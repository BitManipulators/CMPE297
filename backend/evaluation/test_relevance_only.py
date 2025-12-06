#!/usr/bin/env python3
"""
Simple test script for Relevance metric only.
Used to debug the LLM Judge response.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from evaluation.llm_judge import LLMJudge
from evaluation.metrics import EvaluationMetrics

async def test_relevance():
    """Test just the relevance evaluation"""
    
    print("\n" + "="*60)
    print("Testing Relevance Metric Only")
    print("="*60)
    
    # Check API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set!")
        return
    print(f"API Key found: {api_key[:10]}...")
    
    # Initialize judge
    print("\nInitializing LLM Judge...")
    judge = LLMJudge(
        model_name="gemini-2.5-flash",
        temperature=0.1,
        use_batch_evaluation=False
    )
    
    if not judge.is_available():
        print("ERROR: Judge not available!")
        return
    
    print("Judge initialized successfully!")
    
    # Test data
    question = "Is dandelion edible?"
    context = "Dandelion (Taraxacum officinale) is completely edible. All parts - leaves, flowers, and roots - can be consumed. Leaves are rich in vitamins A, C, and K."
    llm_response = "Yes, dandelion is edible! You can eat the leaves, flowers, and roots. The leaves are nutritious and contain vitamins."
    
    print(f"\n--- Test Input ---")
    print(f"Question: {question}")
    print(f"Context: {context[:100]}...")
    print(f"LLM Response: {llm_response}")
    
    # Get the prompt that will be sent
    print(f"\n--- Evaluation Prompt ---")
    prompt = EvaluationMetrics.get_relevance_prompt(question, context, llm_response)
    print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
    
    # Run evaluation
    print(f"\n--- Calling Judge ---")
    try:
        result = await judge.evaluate_relevance(question, context, llm_response)
        
        print(f"\n--- Result ---")
        print(f"Metric: {result.metric_name}")
        print(f"Score: {result.score}")
        print(f"Reasoning: {result.reasoning}")
        print(f"Confidence: {result.confidence}")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_relevance())


