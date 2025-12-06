# LLM-as-Judge Evaluation Pipeline

This evaluation pipeline uses **LLM-as-Judge** methodology with **Weights & Biases** integration to systematically evaluate LLM responses for the IntoTheWild plant identification system.

## 🎯 Overview

The pipeline evaluates LLM responses across 5 key dimensions:

| Metric | Weight | Description |
|--------|--------|-------------|
| **Faithfulness** | 25% | Is the response accurate and grounded in the provided context? |
| **Relevance** | 20% | Does the response directly answer the user's question? |
| **Completeness** | 20% | Does the response cover all important information? |
| **Safety** | 25% | Does the response include appropriate safety warnings? |
| **Coherence** | 10% | Is the response well-structured and easy to understand? |

## 📁 File Structure

```
evaluation/
├── __init__.py                 # Package exports
├── metrics.py                  # Metric definitions and prompts
├── llm_judge.py               # LLM-as-Judge implementation
├── wandb_tracker.py           # Weights & Biases integration
├── evaluation_pipeline.py     # Main pipeline orchestration
├── run_evaluation.py          # CLI runner script
├── sample_dataset.json        # Sample evaluation dataset
└── README.md                  # This file
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Make sure your `.env` file contains:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Login to Weights & Biases (First Time)

```bash
wandb login
```

### 4. Run Evaluation

```bash
# Using default sample dataset
cd backend/evaluation
python run_evaluation.py

# With custom dataset
python run_evaluation.py --dataset my_dataset.json

# Quick test with 3 examples
python run_evaluation.py --max-examples 3

# Without W&B tracking
python run_evaluation.py --no-wandb
```

## 📊 Dataset Format

Create a JSON file with the following structure:

```json
[
  {
    "id": "unique_example_id",
    "question": "User's question",
    "context": "Ground truth context/information",
    "llm_response": "The LLM's response to evaluate",
    "expected_answer_key_points": ["key point 1", "key point 2"]
  }
]
```

### Example:

```json
[
  {
    "id": "plant_001",
    "question": "Is dandelion edible?",
    "context": "Dandelion (Taraxacum officinale) is completely edible. Leaves are rich in vitamins A, C, K. Roots can be roasted as coffee substitute. Young leaves are less bitter.",
    "llm_response": "Yes! Dandelion is completely edible - leaves, flowers, and roots. The leaves are packed with vitamins A, C, and K. Young leaves are best for salads as they're less bitter. You can even roast the roots as a coffee substitute!",
    "expected_answer_key_points": ["edible", "leaves flowers roots", "vitamins", "less bitter young", "coffee substitute"]
  }
]
```

## 🔧 CLI Options

```
usage: run_evaluation.py [-h] [--dataset PATH] [--max-examples N] [--output PATH]
                         [--model MODEL] [--temperature T] [--individual-metrics]
                         [--no-wandb] [--wandb-project PROJECT] [--experiment NAME]
                         [--tags TAGS] [--concurrent N] [--no-retry] [--verbose]

Options:
  --dataset, -d        Path to evaluation dataset JSON
  --max-examples, -n   Limit number of examples (for testing)
  --output, -o         Output path for results JSON
  --model, -m          Judge model (default: gemini-2.5-flash)
  --temperature, -t    Judge temperature (default: 0.1)
  --individual-metrics Use individual metric calls (slower but more detailed)
  --no-wandb           Disable W&B tracking
  --wandb-project, -p  W&B project name
  --experiment, -e     W&B run name
  --tags               W&B tags
  --concurrent, -c     Concurrent evaluations (default: 3)
  --no-retry           Disable automatic retry on failures
  --verbose, -v        Enable verbose logging
```

## 📈 Weights & Biases Dashboard

When W&B is enabled, the pipeline logs:

1. **Real-time Metrics**: Score for each example as it's evaluated
2. **Summary Statistics**: Mean, min, max for all metrics
3. **Results Table**: Detailed table with all examples and scores
4. **Visualizations**:
   - Bar chart of average scores by metric
   - Histogram of overall score distribution
   - Scatter plot of Faithfulness vs Safety

Access your dashboard at: https://wandb.ai/YOUR_USERNAME/intothewild-llm-eval

## 🧪 Programmatic Usage

```python
import asyncio
from evaluation import EvaluationPipeline, PipelineConfig

async def main():
    # Configure pipeline
    config = PipelineConfig(
        judge_model="gemini-2.5-flash",
        judge_temperature=0.1,
        enable_wandb=True,
        wandb_project="my-project",
        max_examples=10
    )
    
    # Run evaluation
    pipeline = EvaluationPipeline(config)
    report = await pipeline.run(dataset_path="my_dataset.json")
    
    print(f"Average Score: {report['metrics']['overall']['mean']:.2f}")

asyncio.run(main())
```

## 📝 Evaluation Prompts

The pipeline uses carefully crafted prompts for each metric. The judge LLM (Gemini) evaluates responses and provides:

- **Score (1-10)**: Numerical rating
- **Reasoning**: Detailed explanation
- **Confidence**: Judge's confidence in the score

### Example Faithfulness Evaluation:

```
Score: 9/10
Reasoning: The response accurately reflects all information from the context. 
It correctly states dandelion is edible, mentions vitamins A, C, K, and notes 
young leaves are less bitter. The coffee substitute claim is supported by context.
No hallucinations detected.
Confidence: 0.95
```

## 🔄 Batch vs Individual Evaluation

**Batch Mode (default)**: Evaluates all 5 metrics in a single LLM call
- ✅ Faster (1 API call per example)
- ✅ Lower cost
- ❌ Less detailed reasoning

**Individual Mode** (`--individual-metrics`): Separate call for each metric
- ✅ More detailed reasoning per metric
- ✅ Can retry individual failed metrics
- ❌ 5x more API calls
- ❌ Slower

## 🎯 Interpreting Results

| Overall Score | Interpretation |
|---------------|----------------|
| 9.0 - 10.0 | Excellent - Response is highly accurate, complete, and safe |
| 7.0 - 8.9 | Good - Minor issues but generally reliable |
| 5.0 - 6.9 | Fair - Some concerns, needs improvement |
| 3.0 - 4.9 | Poor - Significant issues with accuracy or safety |
| 1.0 - 2.9 | Critical - Major problems, potentially harmful |

## 🔍 Troubleshooting

### "GEMINI_API_KEY not found"
```bash
export GEMINI_API_KEY=your_key_here
# Or add to .env file
```

### "W&B API key not found"
```bash
wandb login
# Or set WANDB_API_KEY environment variable
```

### Rate Limiting
Reduce concurrent evaluations:
```bash
python run_evaluation.py --concurrent 1
```

### Memory Issues with Large Datasets
Process in batches:
```bash
python run_evaluation.py --max-examples 50
```

## 📚 References

- [LLM-as-Judge Paper](https://arxiv.org/abs/2306.05685)
- [Weights & Biases Documentation](https://docs.wandb.ai/)
- [Google Gemini API](https://ai.google.dev/docs)


