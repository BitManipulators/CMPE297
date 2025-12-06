"""
LLM-as-Judge Service
Uses an LLM (Gemini) to evaluate responses from another LLM
"""

import json
import asyncio
import logging
import os
import re
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from dotenv import load_dotenv

from .metrics import (
    EvaluationMetrics,
    MetricResult,
    EvaluationResult,
    MetricType
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import Gemini
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google-generativeai not installed. Run: pip install google-generativeai")


class LLMJudge:
    """
    LLM-as-Judge implementation using Google Gemini
    Evaluates LLM responses across multiple quality dimensions
    """
    
    def __init__(
        self,
        model_name: str = "gemini-2.5-flash",
        api_key: Optional[str] = None,
        temperature: float = 0.1,  # Low temperature for consistent evaluations
        use_batch_evaluation: bool = True
    ):
        """
        Initialize the LLM Judge.
        
        Args:
            model_name: Gemini model to use for judging
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
            temperature: Temperature for judge responses (lower = more consistent)
            use_batch_evaluation: Whether to evaluate all metrics at once (faster)
        """
        self.model_name = model_name
        self.temperature = temperature
        self.use_batch_evaluation = use_batch_evaluation
        self.model = None
        
        # Configure Gemini
        if GEMINI_AVAILABLE:
            api_key = api_key or os.getenv("GEMINI_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                try:
                    self.model = genai.GenerativeModel(
                        model_name,
                        generation_config={
                            "temperature": temperature,
                            "top_p": 0.95,
                            "max_output_tokens": 4096,
                        }
                    )
                    logger.info(f"LLM Judge initialized with model: {model_name}")
                except Exception as e:
                    logger.error(f"Failed to initialize Gemini model: {e}")
                    self.model = None
            else:
                logger.warning("GEMINI_API_KEY not found. LLM Judge will not work.")
        else:
            logger.warning("Gemini not available. Install with: pip install google-generativeai")
    
    def is_available(self) -> bool:
        """Check if the judge is ready to evaluate"""
        return self.model is not None
    
    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response, handling potential formatting issues.
        """
        if not response_text or not response_text.strip():
            logger.warning("Empty response text received")
            return {}
        
        # Clean up the response text
        cleaned_text = response_text.strip()
        
        # Try direct JSON parsing first
        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown code blocks
        # Pattern 1: ```json ... ```
        json_block_match = re.search(r'```json\s*\n?(.*?)\n?```', cleaned_text, re.DOTALL | re.IGNORECASE)
        if json_block_match:
            try:
                json_str = json_block_match.group(1).strip()
                if json_str:
                    return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        # Pattern 2: ``` ... ``` (generic code block)
        code_block_match = re.search(r'```\s*\n?(.*?)\n?```', cleaned_text, re.DOTALL)
        if code_block_match:
            try:
                json_str = code_block_match.group(1).strip()
                if json_str and json_str.startswith('{'):
                    return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        # Pattern 3: Find JSON object directly (greedy match for complete object)
        # Look for balanced braces
        brace_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned_text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass
        
        # Pattern 4: Try to find the largest valid JSON object
        start_idx = cleaned_text.find('{')
        if start_idx != -1:
            # Try progressively smaller substrings
            for end_idx in range(len(cleaned_text), start_idx, -1):
                if cleaned_text[end_idx-1] == '}':
                    try:
                        potential_json = cleaned_text[start_idx:end_idx]
                        return json.loads(potential_json)
                    except json.JSONDecodeError:
                        continue
        
        # Log warning with more context
        preview = cleaned_text[:300] if len(cleaned_text) > 300 else cleaned_text
        logger.warning(f"Failed to parse JSON from response. Preview: {preview}")
        
        # Return a default structure to avoid complete failure
        return {
            "score": 5,
            "reasoning": f"Failed to parse judge response. Raw response: {cleaned_text[:500]}",
            "confidence": 0.0
        }
    
    def _extract_text_from_response(self, response) -> str:
        """
        Extract text from Gemini response, handling both simple and multi-part responses.
        """
        try:
            # Try the simple .text accessor first
            return response.text
        except ValueError:
            # Handle multi-part responses
            pass
        
        # Try to extract from parts
        try:
            if hasattr(response, 'parts') and response.parts:
                text_parts = []
                for part in response.parts:
                    if hasattr(part, 'text'):
                        text_parts.append(part.text)
                return ''.join(text_parts)
        except Exception as e:
            logger.debug(f"Could not extract from parts: {e}")
        
        # Try to extract from candidates
        try:
            if hasattr(response, 'candidates') and response.candidates:
                for candidate in response.candidates:
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        text_parts = []
                        for part in candidate.content.parts:
                            if hasattr(part, 'text'):
                                text_parts.append(part.text)
                        if text_parts:
                            return ''.join(text_parts)
        except Exception as e:
            logger.debug(f"Could not extract from candidates: {e}")
        
        # Last resort: try string representation
        try:
            return str(response)
        except Exception:
            return ""
    
    async def _call_judge(self, prompt: str) -> str:
        """
        Call the judge LLM with the given prompt.
        """
        if not self.model:
            raise RuntimeError("LLM Judge model not initialized")
        
        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(prompt)
            )
            
            # DEBUG: Print raw response object
            print("\n" + "="*60)
            print("DEBUG: Raw Gemini Response Object")
            print("="*60)
            print(f"Response type: {type(response)}")
            print(f"Response dir: {[attr for attr in dir(response) if not attr.startswith('_')]}")
            
            if hasattr(response, 'candidates'):
                print(f"Candidates count: {len(response.candidates) if response.candidates else 0}")
                if response.candidates:
                    for i, candidate in enumerate(response.candidates):
                        print(f"  Candidate {i}: {candidate}")
                        if hasattr(candidate, 'content'):
                            print(f"    Content: {candidate.content}")
                            if hasattr(candidate.content, 'parts'):
                                for j, part in enumerate(candidate.content.parts):
                                    print(f"      Part {j}: {part}")
            
            # Extract text from response (handles both simple and multi-part)
            text = self._extract_text_from_response(response)
            
            # DEBUG: Print extracted text
            print(f"\nExtracted text length: {len(text) if text else 0}")
            print(f"Extracted text preview: {text[:500] if text else 'EMPTY'}")
            print("="*60 + "\n")
            
            return text if text else ""
            
        except Exception as e:
            logger.error(f"Error calling judge LLM: {e}")
            raise
    
    async def evaluate_faithfulness(
        self,
        question: str,
        context: str,
        response: str
    ) -> MetricResult:
        """Evaluate faithfulness of the response to the context."""
        prompt = EvaluationMetrics.get_faithfulness_prompt(question, context, response)
        
        try:
            result_text = await self._call_judge(prompt)
            result_json = self._parse_json_response(result_text)
            
            return MetricResult(
                metric_name=MetricType.FAITHFULNESS.value,
                score=float(result_json.get("score", 5)),
                reasoning=result_json.get("reasoning", "No reasoning provided"),
                confidence=float(result_json.get("confidence", 0.8))
            )
        except Exception as e:
            logger.error(f"Error evaluating faithfulness: {e}")
            return MetricResult(
                metric_name=MetricType.FAITHFULNESS.value,
                score=0,
                reasoning=f"Evaluation failed: {str(e)}",
                confidence=0
            )
    
    async def evaluate_relevance(
        self,
        question: str,
        context: str,
        response: str
    ) -> MetricResult:
        """Evaluate relevance of the response to the question."""
        prompt = EvaluationMetrics.get_relevance_prompt(question, context, response)
        
        try:
            result_text = await self._call_judge(prompt)
            result_json = self._parse_json_response(result_text)
            
            return MetricResult(
                metric_name=MetricType.RELEVANCE.value,
                score=float(result_json.get("score", 5)),
                reasoning=result_json.get("reasoning", "No reasoning provided"),
                confidence=float(result_json.get("confidence", 0.8))
            )
        except Exception as e:
            logger.error(f"Error evaluating relevance: {e}")
            return MetricResult(
                metric_name=MetricType.RELEVANCE.value,
                score=0,
                reasoning=f"Evaluation failed: {str(e)}",
                confidence=0
            )
    
    async def evaluate_completeness(
        self,
        question: str,
        context: str,
        response: str,
        key_points: List[str] = None
    ) -> MetricResult:
        """Evaluate completeness of the response."""
        prompt = EvaluationMetrics.get_completeness_prompt(question, context, response, key_points)
        
        try:
            result_text = await self._call_judge(prompt)
            result_json = self._parse_json_response(result_text)
            
            return MetricResult(
                metric_name=MetricType.COMPLETENESS.value,
                score=float(result_json.get("score", 5)),
                reasoning=result_json.get("reasoning", "No reasoning provided"),
                confidence=float(result_json.get("confidence", 0.8))
            )
        except Exception as e:
            logger.error(f"Error evaluating completeness: {e}")
            return MetricResult(
                metric_name=MetricType.COMPLETENESS.value,
                score=0,
                reasoning=f"Evaluation failed: {str(e)}",
                confidence=0
            )
    
    async def evaluate_safety(
        self,
        question: str,
        context: str,
        response: str
    ) -> MetricResult:
        """Evaluate safety of the response."""
        prompt = EvaluationMetrics.get_safety_prompt(question, context, response)
        
        try:
            result_text = await self._call_judge(prompt)
            result_json = self._parse_json_response(result_text)
            
            return MetricResult(
                metric_name=MetricType.SAFETY.value,
                score=float(result_json.get("score", 5)),
                reasoning=result_json.get("reasoning", "No reasoning provided"),
                confidence=float(result_json.get("confidence", 0.8))
            )
        except Exception as e:
            logger.error(f"Error evaluating safety: {e}")
            return MetricResult(
                metric_name=MetricType.SAFETY.value,
                score=0,
                reasoning=f"Evaluation failed: {str(e)}",
                confidence=0
            )
    
    async def evaluate_coherence(
        self,
        question: str,
        context: str,
        response: str
    ) -> MetricResult:
        """Evaluate coherence of the response."""
        prompt = EvaluationMetrics.get_coherence_prompt(question, context, response)
        
        try:
            result_text = await self._call_judge(prompt)
            result_json = self._parse_json_response(result_text)
            
            return MetricResult(
                metric_name=MetricType.COHERENCE.value,
                score=float(result_json.get("score", 5)),
                reasoning=result_json.get("reasoning", "No reasoning provided"),
                confidence=float(result_json.get("confidence", 0.8))
            )
        except Exception as e:
            logger.error(f"Error evaluating coherence: {e}")
            return MetricResult(
                metric_name=MetricType.COHERENCE.value,
                score=0,
                reasoning=f"Evaluation failed: {str(e)}",
                confidence=0
            )
    
    async def evaluate_all_metrics_batch(
        self,
        question: str,
        context: str,
        response: str
    ) -> Dict[str, MetricResult]:
        """
        Evaluate all metrics in a single LLM call (more efficient).
        """
        prompt = EvaluationMetrics.get_overall_prompt(question, context, response)
        
        try:
            result_text = await self._call_judge(prompt)
            result_json = self._parse_json_response(result_text)
            
            metrics = {}
            
            for metric_name in ["faithfulness", "relevance", "completeness", "safety", "coherence"]:
                metric_data = result_json.get(metric_name, {})
                metrics[metric_name] = MetricResult(
                    metric_name=metric_name,
                    score=float(metric_data.get("score", 5)),
                    reasoning=metric_data.get("reasoning", "No reasoning provided"),
                    confidence=0.8
                )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error in batch evaluation: {e}")
            # Return empty metrics on error
            return {
                metric: MetricResult(
                    metric_name=metric,
                    score=0,
                    reasoning=f"Evaluation failed: {str(e)}",
                    confidence=0
                )
                for metric in ["faithfulness", "relevance", "completeness", "safety", "coherence"]
            }
    
    async def evaluate_all_metrics_individual(
        self,
        question: str,
        context: str,
        response: str,
        key_points: List[str] = None
    ) -> Dict[str, MetricResult]:
        """
        Evaluate all metrics with individual LLM calls (more detailed but slower).
        """
        # Run all evaluations concurrently
        results = await asyncio.gather(
            self.evaluate_faithfulness(question, context, response),
            self.evaluate_relevance(question, context, response),
            self.evaluate_completeness(question, context, response, key_points),
            self.evaluate_safety(question, context, response),
            self.evaluate_coherence(question, context, response),
            return_exceptions=True
        )
        
        metric_names = ["faithfulness", "relevance", "completeness", "safety", "coherence"]
        metrics = {}
        
        for name, result in zip(metric_names, results):
            if isinstance(result, Exception):
                metrics[name] = MetricResult(
                    metric_name=name,
                    score=0,
                    reasoning=f"Evaluation failed: {str(result)}",
                    confidence=0
                )
            else:
                metrics[name] = result
        
        return metrics
    
    async def evaluate(
        self,
        example_id: str,
        question: str,
        context: str,
        llm_response: str,
        key_points: List[str] = None,
        use_batch: bool = None
    ) -> EvaluationResult:
        """
        Evaluate a single example across all metrics.
        
        Args:
            example_id: Unique identifier for this example
            question: The question that was asked
            context: The ground truth context
            llm_response: The LLM's response to evaluate
            key_points: Expected key points for completeness evaluation
            use_batch: Override default batch evaluation setting
        
        Returns:
            EvaluationResult with all metric scores
        """
        start_time = time.time()
        
        if not self.is_available():
            return EvaluationResult(
                example_id=example_id,
                question=question,
                context=context,
                llm_response=llm_response,
                error="LLM Judge not available"
            )
        
        use_batch = use_batch if use_batch is not None else self.use_batch_evaluation
        
        try:
            if use_batch:
                metrics = await self.evaluate_all_metrics_batch(question, context, llm_response)
            else:
                metrics = await self.evaluate_all_metrics_individual(
                    question, context, llm_response, key_points
                )
            
            # Calculate weighted overall score
            weights = EvaluationMetrics.get_metric_weights()
            overall_score = sum(
                metrics.get(name, MetricResult(name, 0, "", 0)).score * weight
                for name, weight in weights.items()
            )
            
            evaluation_time = time.time() - start_time
            
            return EvaluationResult(
                example_id=example_id,
                question=question,
                context=context,
                llm_response=llm_response,
                metric_results=metrics,
                overall_score=overall_score,
                evaluation_time_seconds=evaluation_time,
                judge_model=self.model_name
            )
            
        except Exception as e:
            logger.error(f"Error evaluating example {example_id}: {e}")
            return EvaluationResult(
                example_id=example_id,
                question=question,
                context=context,
                llm_response=llm_response,
                error=str(e),
                evaluation_time_seconds=time.time() - start_time,
                judge_model=self.model_name
            )

