"""
Main Evaluation Pipeline
Orchestrates the LLM-as-Judge evaluation process with W&B tracking
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from dotenv import load_dotenv

from .llm_judge import LLMJudge
from .wandb_tracker import WandBTracker
from .metrics import EvaluationResult

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class DatasetExample:
    """Single example from the evaluation dataset"""
    id: str
    question: str
    context: str
    llm_response: str
    expected_answer_key_points: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineConfig:
    """Configuration for the evaluation pipeline"""
    # Judge settings
    judge_model: str = "gemini-2.5-flash"
    judge_temperature: float = 0.1
    use_batch_evaluation: bool = True
    
    # Dataset settings
    dataset_path: Optional[str] = None
    max_examples: Optional[int] = None  # Limit for testing
    
    # W&B settings
    wandb_project: str = "intothewild-llm-eval"
    wandb_experiment_name: Optional[str] = None
    wandb_tags: List[str] = field(default_factory=lambda: ["llm-evaluation", "rag"])
    enable_wandb: bool = True
    
    # Execution settings
    concurrent_evaluations: int = 3  # Number of concurrent evaluations
    retry_failed: bool = True
    max_retries: int = 2
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for logging"""
        return {
            "judge_model": self.judge_model,
            "judge_temperature": self.judge_temperature,
            "use_batch_evaluation": self.use_batch_evaluation,
            "max_examples": self.max_examples,
            "concurrent_evaluations": self.concurrent_evaluations,
            "retry_failed": self.retry_failed,
            "max_retries": self.max_retries,
        }


class EvaluationPipeline:
    """
    Main pipeline for evaluating LLM responses using LLM-as-Judge.
    Integrates with Weights & Biases for experiment tracking.
    """
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        """
        Initialize the evaluation pipeline.
        
        Args:
            config: Pipeline configuration
        """
        self.config = config or PipelineConfig()
        self.judge = None
        self.tracker = None
        self.dataset: List[DatasetExample] = []
        self.results: List[EvaluationResult] = []
        
    def load_dataset(self, path: Optional[str] = None) -> List[DatasetExample]:
        """
        Load evaluation dataset from JSON file.
        
        Args:
            path: Path to dataset JSON file
            
        Returns:
            List of DatasetExample objects
        """
        dataset_path = path or self.config.dataset_path
        
        if not dataset_path:
            # Use default sample dataset
            default_path = Path(__file__).parent / "sample_dataset.json"
            dataset_path = str(default_path)
        
        logger.info(f"Loading dataset from: {dataset_path}")
        
        try:
            with open(dataset_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            examples = []
            for item in data:
                example = DatasetExample(
                    id=item.get("id", f"example_{len(examples)}"),
                    question=item["question"],
                    context=item["context"],
                    llm_response=item["llm_response"],
                    expected_answer_key_points=item.get("expected_answer_key_points", []),
                    metadata=item.get("metadata", {})
                )
                examples.append(example)
            
            # Apply max_examples limit if set
            if self.config.max_examples:
                examples = examples[:self.config.max_examples]
            
            self.dataset = examples
            logger.info(f"Loaded {len(examples)} examples from dataset")
            return examples
            
        except Exception as e:
            logger.error(f"Failed to load dataset: {e}")
            raise
    
    def initialize(self) -> bool:
        """
        Initialize the pipeline components (judge and tracker).
        
        Returns:
            True if initialization successful
        """
        # Initialize LLM Judge
        self.judge = LLMJudge(
            model_name=self.config.judge_model,
            temperature=self.config.judge_temperature,
            use_batch_evaluation=self.config.use_batch_evaluation
        )
        
        if not self.judge.is_available():
            logger.error("LLM Judge is not available. Check GEMINI_API_KEY.")
            return False
        
        logger.info(f"LLM Judge initialized with model: {self.config.judge_model}")
        
        # Initialize W&B tracker if enabled
        if self.config.enable_wandb:
            self.tracker = WandBTracker(
                project_name=self.config.wandb_project,
                experiment_name=self.config.wandb_experiment_name,
                config=self.config.to_dict(),
                tags=self.config.wandb_tags
            )
            
            if self.tracker.init():
                logger.info(f"W&B tracker initialized: {self.tracker.get_run_url()}")
            else:
                logger.warning("W&B tracker initialization failed. Continuing without tracking.")
                self.tracker = None
        
        return True
    
    async def evaluate_example(
        self,
        example: DatasetExample,
        retry_count: int = 0
    ) -> EvaluationResult:
        """
        Evaluate a single example.
        
        Args:
            example: DatasetExample to evaluate
            retry_count: Current retry attempt
            
        Returns:
            EvaluationResult
        """
        try:
            result = await self.judge.evaluate(
                example_id=example.id,
                question=example.question,
                context=example.context,
                llm_response=example.llm_response,
                key_points=example.expected_answer_key_points
            )
            
            # Retry on error if configured
            if result.error and self.config.retry_failed and retry_count < self.config.max_retries:
                logger.warning(f"Retrying {example.id} (attempt {retry_count + 1})")
                await asyncio.sleep(1)  # Brief delay before retry
                return await self.evaluate_example(example, retry_count + 1)
            
            return result
            
        except Exception as e:
            logger.error(f"Error evaluating {example.id}: {e}")
            return EvaluationResult(
                example_id=example.id,
                question=example.question,
                context=example.context,
                llm_response=example.llm_response,
                error=str(e)
            )
    
    async def run_evaluations(self) -> List[EvaluationResult]:
        """
        Run evaluations on all dataset examples.
        
        Returns:
            List of EvaluationResult objects
        """
        if not self.dataset:
            logger.error("No dataset loaded. Call load_dataset() first.")
            return []
        
        if not self.judge or not self.judge.is_available():
            logger.error("Judge not initialized. Call initialize() first.")
            return []
        
        logger.info(f"Starting evaluation of {len(self.dataset)} examples...")
        start_time = time.time()
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.config.concurrent_evaluations)
        
        async def evaluate_with_semaphore(example: DatasetExample) -> EvaluationResult:
            async with semaphore:
                result = await self.evaluate_example(example)
                
                # Log to W&B immediately
                if self.tracker:
                    self.tracker.log_single_result(result)
                
                # Progress logging
                completed = len([r for r in self.results if r]) + 1
                logger.info(
                    f"[{completed}/{len(self.dataset)}] {example.id}: "
                    f"overall_score={result.overall_score:.2f}"
                )
                
                return result
        
        # Run evaluations concurrently
        tasks = [evaluate_with_semaphore(example) for example in self.dataset]
        self.results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        logger.info(f"Evaluation completed in {total_time:.2f} seconds")
        
        return self.results
    
    def generate_report(self) -> Dict[str, Any]:
        """
        Generate a summary report of the evaluation results.
        
        Returns:
            Dictionary containing summary statistics
        """
        if not self.results:
            return {"error": "No results to report"}
        
        successful = [r for r in self.results if not r.error]
        failed = [r for r in self.results if r.error]
        
        report = {
            "summary": {
                "total_examples": len(self.results),
                "successful": len(successful),
                "failed": len(failed),
                "success_rate": len(successful) / len(self.results) if self.results else 0
            },
            "metrics": {},
            "examples": {
                "best": None,
                "worst": None
            }
        }
        
        if successful:
            # Calculate metric statistics
            metric_names = ["faithfulness", "relevance", "completeness", "safety", "coherence"]
            
            for metric in metric_names:
                scores = [
                    r.metric_results.get(metric).score
                    for r in successful
                    if r.metric_results.get(metric)
                ]
                if scores:
                    report["metrics"][metric] = {
                        "mean": sum(scores) / len(scores),
                        "min": min(scores),
                        "max": max(scores)
                    }
            
            # Overall score statistics
            overall_scores = [r.overall_score for r in successful]
            report["metrics"]["overall"] = {
                "mean": sum(overall_scores) / len(overall_scores),
                "min": min(overall_scores),
                "max": max(overall_scores)
            }
            
            # Best and worst examples
            sorted_results = sorted(successful, key=lambda r: r.overall_score, reverse=True)
            report["examples"]["best"] = {
                "id": sorted_results[0].example_id,
                "score": sorted_results[0].overall_score,
                "question": sorted_results[0].question[:100]
            }
            report["examples"]["worst"] = {
                "id": sorted_results[-1].example_id,
                "score": sorted_results[-1].overall_score,
                "question": sorted_results[-1].question[:100]
            }
        
        # Failed examples
        if failed:
            report["failed_examples"] = [
                {"id": r.example_id, "error": r.error}
                for r in failed
            ]
        
        return report
    
    def save_results(self, output_path: str = "evaluation_results.json"):
        """
        Save evaluation results to a JSON file.
        
        Args:
            output_path: Path to save results
        """
        results_data = {
            "config": self.config.to_dict(),
            "summary": self.generate_report(),
            "results": [r.to_dict() for r in self.results]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2)
        
        logger.info(f"Results saved to: {output_path}")
    
    def finalize(self):
        """
        Finalize the pipeline, log final results to W&B, and cleanup.
        """
        if self.tracker and self.results:
            # Log summary metrics
            self.tracker.log_summary_metrics(self.results)
            
            # Log detailed results table
            self.tracker.log_detailed_results_table(self.results)
            
            # Create visualizations
            self.tracker.create_visualizations(self.results)
            
            # Finish W&B run
            self.tracker.finish()
        
        logger.info("Pipeline finalized")
    
    async def run(
        self,
        dataset_path: Optional[str] = None,
        output_path: str = "evaluation_results.json"
    ) -> Dict[str, Any]:
        """
        Run the complete evaluation pipeline.
        
        Args:
            dataset_path: Path to dataset (uses default if not provided)
            output_path: Path to save results
            
        Returns:
            Summary report dictionary
        """
        try:
            # Load dataset
            self.load_dataset(dataset_path)
            
            # Initialize components
            if not self.initialize():
                return {"error": "Pipeline initialization failed"}
            
            # Run evaluations
            await self.run_evaluations()
            
            # Generate and save report
            report = self.generate_report()
            self.save_results(output_path)
            
            # Finalize (W&B logging, cleanup)
            self.finalize()
            
            return report
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            if self.tracker:
                self.tracker.finish()
            raise


async def run_evaluation_pipeline(
    dataset_path: Optional[str] = None,
    config: Optional[PipelineConfig] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function to run the evaluation pipeline.
    
    Args:
        dataset_path: Path to evaluation dataset
        config: Pipeline configuration
        **kwargs: Additional config overrides
        
    Returns:
        Evaluation report
    """
    # Create config with any overrides
    if config is None:
        config = PipelineConfig(**kwargs)
    else:
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
    
    # Run pipeline
    pipeline = EvaluationPipeline(config)
    return await pipeline.run(dataset_path)


