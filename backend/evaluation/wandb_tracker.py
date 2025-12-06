"""
Weights & Biases Integration for LLM Evaluation Pipeline
Tracks experiments, logs metrics, and creates visualizations
"""

import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime

from dotenv import load_dotenv

from .metrics import EvaluationResult, MetricType

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Try to import wandb
try:
    import wandb
    from wandb import Table
    WANDB_AVAILABLE = True
except ImportError:
    WANDB_AVAILABLE = False
    logger.warning("wandb not installed. Run: pip install wandb")


class WandBTracker:
    """
    Weights & Biases tracker for LLM evaluation experiments.
    Handles logging, visualization, and experiment tracking.
    """
    
    def __init__(
        self,
        project_name: str = "intothewild-llm-eval",
        experiment_name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        notes: Optional[str] = None
    ):
        """
        Initialize W&B tracker.
        
        Args:
            project_name: W&B project name
            experiment_name: Run name (auto-generated if not provided)
            config: Experiment configuration to log
            tags: Tags for the run
            notes: Notes for the run
        """
        self.project_name = project_name
        self.experiment_name = experiment_name or f"eval-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.config = config or {}
        self.tags = tags or ["llm-evaluation", "rag"]
        self.notes = notes
        self.run = None
        self.results_table = None
        
    def is_available(self) -> bool:
        """Check if W&B is available"""
        return WANDB_AVAILABLE
    
    def init(self) -> bool:
        """
        Initialize W&B run.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if not WANDB_AVAILABLE:
            logger.warning("W&B not available. Metrics will not be tracked.")
            return False
        
        try:
            # Check if already logged in
            if not wandb.api.api_key:
                logger.warning(
                    "W&B API key not found. Please run 'wandb login' or set WANDB_API_KEY environment variable."
                )
                return False
            
            self.run = wandb.init(
                project=self.project_name,
                name=self.experiment_name,
                config=self.config,
                tags=self.tags,
                notes=self.notes,
                reinit=True
            )
            
            # Initialize results table
            self.results_table = wandb.Table(columns=[
                "example_id",
                "question",
                "llm_response",
                "faithfulness_score",
                "relevance_score",
                "completeness_score",
                "safety_score",
                "coherence_score",
                "overall_score",
                "evaluation_time_s"
            ])
            
            logger.info(f"W&B run initialized: {self.run.url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize W&B: {e}")
            return False
    
    def log_config(self, config: Dict[str, Any]):
        """Log configuration parameters"""
        if self.run:
            wandb.config.update(config)
    
    def log_single_result(self, result: EvaluationResult):
        """
        Log a single evaluation result.
        
        Args:
            result: EvaluationResult to log
        """
        if not self.run:
            return
        
        # Extract metric scores
        metrics = {
            f"{metric}/score": result.metric_results.get(metric, type('', (), {'score': 0})()).score
            if hasattr(result.metric_results.get(metric), 'score')
            else result.metric_results.get(metric, type('', (), {'score': 0})).score
            for metric in ["faithfulness", "relevance", "completeness", "safety", "coherence"]
        }
        
        # Fix: properly extract scores
        metrics = {}
        for metric_name in ["faithfulness", "relevance", "completeness", "safety", "coherence"]:
            metric_result = result.metric_results.get(metric_name)
            if metric_result:
                metrics[f"{metric_name}/score"] = metric_result.score
            else:
                metrics[f"{metric_name}/score"] = 0.0
        
        metrics["overall_score"] = result.overall_score
        metrics["evaluation_time_seconds"] = result.evaluation_time_seconds
        
        # Log metrics
        wandb.log(metrics)
        
        # Add to results table
        if self.results_table is not None:
            self.results_table.add_data(
                result.example_id,
                result.question[:100] + "..." if len(result.question) > 100 else result.question,
                result.llm_response[:200] + "..." if len(result.llm_response) > 200 else result.llm_response,
                metrics.get("faithfulness/score", 0),
                metrics.get("relevance/score", 0),
                metrics.get("completeness/score", 0),
                metrics.get("safety/score", 0),
                metrics.get("coherence/score", 0),
                result.overall_score,
                result.evaluation_time_seconds
            )
    
    def log_batch_results(self, results: List[EvaluationResult]):
        """
        Log a batch of evaluation results.
        
        Args:
            results: List of EvaluationResult objects
        """
        for result in results:
            self.log_single_result(result)
    
    def log_summary_metrics(self, results: List[EvaluationResult]):
        """
        Log summary metrics for all results.
        
        Args:
            results: List of all EvaluationResult objects
        """
        if not self.run or not results:
            return
        
        # Calculate averages for each metric
        metric_names = ["faithfulness", "relevance", "completeness", "safety", "coherence"]
        
        summary = {}
        for metric_name in metric_names:
            scores = [
                r.metric_results.get(metric_name).score
                for r in results
                if r.metric_results.get(metric_name) and not r.error
            ]
            if scores:
                summary[f"avg_{metric_name}"] = sum(scores) / len(scores)
                summary[f"min_{metric_name}"] = min(scores)
                summary[f"max_{metric_name}"] = max(scores)
        
        # Overall metrics
        overall_scores = [r.overall_score for r in results if not r.error]
        if overall_scores:
            summary["avg_overall_score"] = sum(overall_scores) / len(overall_scores)
            summary["min_overall_score"] = min(overall_scores)
            summary["max_overall_score"] = max(overall_scores)
        
        # Evaluation stats
        summary["total_examples"] = len(results)
        summary["successful_evaluations"] = len([r for r in results if not r.error])
        summary["failed_evaluations"] = len([r for r in results if r.error])
        
        total_time = sum(r.evaluation_time_seconds for r in results)
        summary["total_evaluation_time_seconds"] = total_time
        summary["avg_evaluation_time_seconds"] = total_time / len(results) if results else 0
        
        # Log summary
        wandb.summary.update(summary)
        
        logger.info(f"Summary metrics logged: avg_overall_score={summary.get('avg_overall_score', 0):.2f}")
    
    def log_detailed_results_table(self, results: List[EvaluationResult]):
        """
        Log detailed results as a W&B Table with full information.
        
        Args:
            results: List of EvaluationResult objects
        """
        if not self.run:
            return
        
        # Create detailed table
        detailed_table = wandb.Table(columns=[
            "example_id",
            "question",
            "context",
            "llm_response",
            "faithfulness_score",
            "faithfulness_reasoning",
            "relevance_score",
            "relevance_reasoning",
            "completeness_score",
            "completeness_reasoning",
            "safety_score",
            "safety_reasoning",
            "coherence_score",
            "coherence_reasoning",
            "overall_score",
            "error"
        ])
        
        for result in results:
            faith = result.metric_results.get("faithfulness")
            rel = result.metric_results.get("relevance")
            comp = result.metric_results.get("completeness")
            safe = result.metric_results.get("safety")
            coh = result.metric_results.get("coherence")
            
            detailed_table.add_data(
                result.example_id,
                result.question,
                result.context[:500] + "..." if len(result.context) > 500 else result.context,
                result.llm_response,
                faith.score if faith else 0,
                faith.reasoning if faith else "",
                rel.score if rel else 0,
                rel.reasoning if rel else "",
                comp.score if comp else 0,
                comp.reasoning if comp else "",
                safe.score if safe else 0,
                safe.reasoning if safe else "",
                coh.score if coh else 0,
                coh.reasoning if coh else "",
                result.overall_score,
                result.error or ""
            )
        
        wandb.log({"detailed_results": detailed_table})
    
    def create_visualizations(self, results: List[EvaluationResult]):
        """
        Create and log visualizations for the evaluation results.
        
        Args:
            results: List of EvaluationResult objects
        """
        if not self.run or not results:
            return
        
        successful_results = [r for r in results if not r.error]
        
        if not successful_results:
            logger.warning("No successful results to visualize")
            return
        
        # 1. Metric scores distribution (bar chart data)
        metric_names = ["faithfulness", "relevance", "completeness", "safety", "coherence"]
        avg_scores = []
        
        for metric in metric_names:
            scores = [
                r.metric_results.get(metric).score
                for r in successful_results
                if r.metric_results.get(metric)
            ]
            avg_scores.append(sum(scores) / len(scores) if scores else 0)
        
        # Create bar chart
        bar_data = [[metric, score] for metric, score in zip(metric_names, avg_scores)]
        bar_table = wandb.Table(data=bar_data, columns=["Metric", "Average Score"])
        wandb.log({
            "metric_averages": wandb.plot.bar(
                bar_table,
                "Metric",
                "Average Score",
                title="Average Scores by Metric"
            )
        })
        
        # 2. Score distribution histogram data
        overall_scores = [r.overall_score for r in successful_results]
        hist_table = wandb.Table(data=[[s] for s in overall_scores], columns=["Overall Score"])
        wandb.log({
            "score_distribution": wandb.plot.histogram(
                hist_table,
                "Overall Score",
                title="Distribution of Overall Scores"
            )
        })
        
        # 3. Scatter plot: Faithfulness vs Safety (often correlated in this domain)
        scatter_data = []
        for r in successful_results:
            faith = r.metric_results.get("faithfulness")
            safety = r.metric_results.get("safety")
            if faith and safety:
                scatter_data.append([faith.score, safety.score, r.example_id])
        
        if scatter_data:
            scatter_table = wandb.Table(
                data=scatter_data,
                columns=["Faithfulness", "Safety", "Example ID"]
            )
            wandb.log({
                "faithfulness_vs_safety": wandb.plot.scatter(
                    scatter_table,
                    "Faithfulness",
                    "Safety",
                    title="Faithfulness vs Safety Scores"
                )
            })
        
        logger.info("Visualizations created and logged to W&B")
    
    def finish(self):
        """
        Finish the W&B run and upload final artifacts.
        """
        if not self.run:
            return
        
        try:
            # Log final results table
            if self.results_table is not None:
                wandb.log({"evaluation_results": self.results_table})
            
            # Finish the run
            wandb.finish()
            logger.info("W&B run finished successfully")
            
        except Exception as e:
            logger.error(f"Error finishing W&B run: {e}")
    
    def get_run_url(self) -> Optional[str]:
        """Get the URL of the current W&B run"""
        return self.run.url if self.run else None


