#!/usr/bin/env python3
"""
LLM-as-Judge Evaluation Runner
Run this script to evaluate LLM responses using the evaluation pipeline

Usage:
    python run_evaluation.py                           # Run with defaults
    python run_evaluation.py --dataset custom.json     # Use custom dataset
    python run_evaluation.py --no-wandb                # Disable W&B tracking
    python run_evaluation.py --max-examples 5          # Limit examples (for testing)
"""

import argparse
import asyncio
import logging
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from evaluation.evaluation_pipeline import EvaluationPipeline, PipelineConfig
from evaluation.metrics import EvaluationMetrics

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="LLM-as-Judge Evaluation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with sample dataset
  python run_evaluation.py

  # Run with custom dataset
  python run_evaluation.py --dataset my_dataset.json

  # Quick test with 3 examples
  python run_evaluation.py --max-examples 3

  # Run without W&B tracking
  python run_evaluation.py --no-wandb

  # Full run with custom settings
  python run_evaluation.py --dataset data.json --experiment "v1-test" --concurrent 5
        """
    )
    
    # Dataset options
    parser.add_argument(
        '--dataset', '-d',
        type=str,
        default=None,
        help='Path to evaluation dataset JSON file (default: sample_dataset.json)'
    )
    parser.add_argument(
        '--max-examples', '-n',
        type=int,
        default=None,
        help='Maximum number of examples to evaluate (for testing)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='evaluation_results.json',
        help='Output path for results JSON (default: evaluation_results.json)'
    )
    
    # Judge options
    parser.add_argument(
        '--model', '-m',
        type=str,
        default='gemini-2.5-flash',
        help='Judge model to use (default: gemini-2.5-flash)'
    )
    parser.add_argument(
        '--temperature', '-t',
        type=float,
        default=0.1,
        help='Judge temperature (default: 0.1)'
    )
    parser.add_argument(
        '--individual-metrics',
        action='store_true',
        help='Use individual metric evaluations instead of batch (more detailed but slower)'
    )
    
    # W&B options
    parser.add_argument(
        '--no-wandb',
        action='store_true',
        help='Disable Weights & Biases tracking'
    )
    parser.add_argument(
        '--wandb-project', '-p',
        type=str,
        default='intothewild-llm-eval',
        help='W&B project name (default: intothewild-llm-eval)'
    )
    parser.add_argument(
        '--experiment', '-e',
        type=str,
        default=None,
        help='W&B experiment/run name (auto-generated if not provided)'
    )
    parser.add_argument(
        '--tags',
        type=str,
        nargs='+',
        default=['llm-evaluation', 'rag'],
        help='W&B tags for the run'
    )
    
    # Execution options
    parser.add_argument(
        '--concurrent', '-c',
        type=int,
        default=3,
        help='Number of concurrent evaluations (default: 3)'
    )
    parser.add_argument(
        '--no-retry',
        action='store_true',
        help='Disable automatic retry on failures'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser.parse_args()


def print_banner():
    """Print a nice banner"""
    banner = """
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║   🌿 IntoTheWild - LLM-as-Judge Evaluation Pipeline 🌿          ║
║                                                                  ║
║   Evaluating LLM responses with AI-powered quality assessment   ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_config(config: PipelineConfig, args):
    """Print configuration summary"""
    print("\n📋 Configuration:")
    print(f"   • Judge Model: {config.judge_model}")
    print(f"   • Temperature: {config.judge_temperature}")
    print(f"   • Batch Evaluation: {config.use_batch_evaluation}")
    print(f"   • Max Examples: {config.max_examples or 'All'}")
    print(f"   • Concurrent Evaluations: {config.concurrent_evaluations}")
    print(f"   • W&B Tracking: {'Enabled' if config.enable_wandb else 'Disabled'}")
    if config.enable_wandb:
        print(f"   • W&B Project: {config.wandb_project}")
        print(f"   • W&B Experiment: {config.wandb_experiment_name or 'Auto-generated'}")
    print()


def print_report(report: dict):
    """Print evaluation report in a nice format"""
    print("\n" + "="*60)
    print("📊 EVALUATION REPORT")
    print("="*60)
    
    summary = report.get("summary", {})
    print(f"\n📈 Summary:")
    print(f"   • Total Examples: {summary.get('total_examples', 0)}")
    print(f"   • Successful: {summary.get('successful', 0)}")
    print(f"   • Failed: {summary.get('failed', 0)}")
    print(f"   • Success Rate: {summary.get('success_rate', 0)*100:.1f}%")
    
    metrics = report.get("metrics", {})
    if metrics:
        print(f"\n📏 Metric Scores (0-10 scale):")
        print("   " + "-"*50)
        print(f"   {'Metric':<15} {'Mean':>8} {'Min':>8} {'Max':>8}")
        print("   " + "-"*50)
        
        for metric, stats in metrics.items():
            if isinstance(stats, dict):
                print(f"   {metric:<15} {stats.get('mean', 0):>8.2f} {stats.get('min', 0):>8.2f} {stats.get('max', 0):>8.2f}")
        print("   " + "-"*50)
    
    examples = report.get("examples", {})
    if examples.get("best"):
        print(f"\n🏆 Best Example:")
        print(f"   • ID: {examples['best']['id']}")
        print(f"   • Score: {examples['best']['score']:.2f}")
        print(f"   • Question: {examples['best']['question'][:60]}...")
    
    if examples.get("worst"):
        print(f"\n⚠️  Worst Example:")
        print(f"   • ID: {examples['worst']['id']}")
        print(f"   • Score: {examples['worst']['score']:.2f}")
        print(f"   • Question: {examples['worst']['question'][:60]}...")
    
    failed = report.get("failed_examples", [])
    if failed:
        print(f"\n❌ Failed Examples ({len(failed)}):")
        for ex in failed[:5]:  # Show max 5
            print(f"   • {ex['id']}: {ex['error'][:50]}...")
    
    print("\n" + "="*60)


async def main():
    """Main entry point"""
    args = parse_args()
    
    # Set verbose logging if requested
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    print_banner()
    
    # Check for required environment variables
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ Error: GEMINI_API_KEY environment variable not set!")
        print("   Please set it in your .env file or export it:")
        print("   export GEMINI_API_KEY=your_api_key_here")
        sys.exit(1)
    
    # Create configuration
    config = PipelineConfig(
        judge_model=args.model,
        judge_temperature=args.temperature,
        use_batch_evaluation=not args.individual_metrics,
        dataset_path=args.dataset,
        max_examples=args.max_examples,
        wandb_project=args.wandb_project,
        wandb_experiment_name=args.experiment,
        wandb_tags=args.tags,
        enable_wandb=not args.no_wandb,
        concurrent_evaluations=args.concurrent,
        retry_failed=not args.no_retry,
    )
    
    print_config(config, args)
    
    # Create and run pipeline
    pipeline = EvaluationPipeline(config)
    
    try:
        print("🚀 Starting evaluation pipeline...\n")
        report = await pipeline.run(
            dataset_path=args.dataset,
            output_path=args.output
        )
        
        # Print report
        print_report(report)
        
        # Print output location
        print(f"\n📁 Results saved to: {args.output}")
        
        if pipeline.tracker and pipeline.tracker.get_run_url():
            print(f"📊 W&B Dashboard: {pipeline.tracker.get_run_url()}")
        
        print("\n✅ Evaluation complete!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Evaluation interrupted by user")
        pipeline.finalize()
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.exception("Pipeline error")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())


