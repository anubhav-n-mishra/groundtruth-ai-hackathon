"""
Insights generation module for the Automated Insight Engine.

This module computes deltas, percentage changes, and impact scores
between current and previous periods, then ranks insights by impact.
"""

import polars as pl
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import InsightConfig
from core.logger import get_insights_logger

logger = get_insights_logger()


@dataclass
class InsightRecord:
    """
    A single insight record representing a significant change.
    
    Attributes:
        dimensions: Dictionary of dimension name to value
        metric: The metric being measured
        current_value: Value in current period
        previous_value: Value in previous period
        delta: Absolute change (current - previous)
        delta_pct: Percentage change
        impact_score: Calculated impact score for ranking
        direction: 'up' or 'down'
    """
    dimensions: Dict[str, Any]
    metric: str
    current_value: float
    previous_value: float
    delta: float
    delta_pct: float
    impact_score: float
    direction: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


def compute_delta(current: float, previous: float) -> float:
    """
    Compute absolute delta between current and previous values.
    
    Args:
        current: Current period value
        previous: Previous period value
        
    Returns:
        Absolute difference (current - previous)
    """
    return current - previous


def compute_delta_pct(current: float, previous: float) -> float:
    """
    Compute percentage change between periods.
    
    Args:
        current: Current period value
        previous: Previous period value
        
    Returns:
        Percentage change, or 0 if previous is 0
    """
    if previous == 0:
        if current == 0:
            return 0.0
        return 100.0 if current > 0 else -100.0
    
    return ((current - previous) / abs(previous)) * 100


def compute_impact_score(
    delta: float,
    delta_pct: float,
    metric_priority: int,
    total_metrics: int
) -> float:
    """
    Compute impact score for ranking insights.
    
    The impact score combines:
    - Absolute magnitude of change
    - Percentage change (normalized)
    - Metric priority weight
    
    Args:
        delta: Absolute change
        delta_pct: Percentage change
        metric_priority: Priority index (0 = highest priority)
        total_metrics: Total number of metrics for normalization
        
    Returns:
        Impact score (higher = more significant)
    """
    # Normalize percentage change to 0-1 scale (cap at 200%)
    pct_factor = min(abs(delta_pct), 200) / 200
    
    # Priority weight: higher priority metrics get higher weight
    priority_weight = (total_metrics - metric_priority) / total_metrics
    
    # Combine factors
    # abs(delta) captures magnitude, pct_factor captures relative change
    raw_score = abs(delta) * (1 + pct_factor) * (1 + priority_weight)
    
    return round(raw_score, 4)


def join_periods(
    current_df: pl.DataFrame,
    previous_df: pl.DataFrame,
    dimensions: List[str]
) -> pl.DataFrame:
    """
    Join current and previous period DataFrames for comparison.
    
    Args:
        current_df: Aggregated current period data
        previous_df: Aggregated previous period data
        dimensions: Dimension columns for joining
        
    Returns:
        Joined DataFrame with _current and _previous suffixes
    """
    if not dimensions:
        # No dimensions - single row comparison
        logger.debug("No dimensions, creating single-row comparison")
        
        # Get metric columns
        current_metrics = [c for c in current_df.columns]
        previous_metrics = [c for c in previous_df.columns]
        
        # Rename columns with suffixes
        current_renamed = current_df.rename({c: f"{c}_current" for c in current_metrics})
        previous_renamed = previous_df.rename({c: f"{c}_previous" for c in previous_metrics})
        
        # Cross join (single row each)
        return current_renamed.join(previous_renamed, how="cross")
    
    # Rename non-dimension columns with suffixes
    current_metrics = [c for c in current_df.columns if c not in dimensions]
    previous_metrics = [c for c in previous_df.columns if c not in dimensions]
    
    current_renamed = current_df.rename({c: f"{c}_current" for c in current_metrics})
    previous_renamed = previous_df.rename({c: f"{c}_previous" for c in previous_metrics})
    
    # Outer join to capture all dimension combinations
    joined = current_renamed.join(
        previous_renamed,
        on=dimensions,
        how="outer"
    )
    
    # Fill nulls with 0 for missing period data
    for col in joined.columns:
        if col.endswith("_current") or col.endswith("_previous"):
            joined = joined.with_columns(pl.col(col).fill_null(0))
    
    logger.debug(f"Joined periods: {len(joined)} dimension combinations")
    return joined


def extract_insights(
    joined_df: pl.DataFrame,
    dimensions: List[str],
    kpi_priority: List[str]
) -> List[InsightRecord]:
    """
    Extract insight records from joined period data.
    
    Args:
        joined_df: Joined current/previous DataFrame
        dimensions: Dimension column names
        kpi_priority: KPIs in priority order
        
    Returns:
        List of InsightRecord objects
    """
    insights: List[InsightRecord] = []
    total_metrics = len(kpi_priority)
    
    # Convert to list of dicts for iteration
    rows = joined_df.to_dicts()
    
    for row in rows:
        # Extract dimension values
        dim_values = {d: row.get(d) for d in dimensions}
        
        # Process each KPI
        for priority_idx, metric in enumerate(kpi_priority):
            current_col = f"{metric}_current"
            previous_col = f"{metric}_previous"
            
            if current_col not in row or previous_col not in row:
                continue
            
            current_val = float(row[current_col] or 0)
            previous_val = float(row[previous_col] or 0)
            
            delta = compute_delta(current_val, previous_val)
            delta_pct = compute_delta_pct(current_val, previous_val)
            impact = compute_impact_score(delta, delta_pct, priority_idx, total_metrics)
            
            direction = "up" if delta > 0 else "down" if delta < 0 else "flat"
            
            insight = InsightRecord(
                dimensions=dim_values,
                metric=metric,
                current_value=round(current_val, 4),
                previous_value=round(previous_val, 4),
                delta=round(delta, 4),
                delta_pct=round(delta_pct, 2),
                impact_score=impact,
                direction=direction
            )
            
            insights.append(insight)
    
    logger.info(f"Extracted {len(insights)} raw insights")
    return insights


def rank_insights(
    insights: List[InsightRecord],
    top_n: Optional[int] = None,
    min_impact: float = 0.0
) -> List[InsightRecord]:
    """
    Rank insights by impact score and optionally filter.
    
    Args:
        insights: List of insight records
        top_n: Optional limit on number of insights to return
        min_impact: Minimum impact score threshold
        
    Returns:
        Sorted and filtered list of insights
    """
    # Filter by minimum impact
    filtered = [i for i in insights if i.impact_score >= min_impact]
    
    # Sort by impact score descending
    ranked = sorted(filtered, key=lambda x: x.impact_score, reverse=True)
    
    # Limit if specified
    if top_n:
        ranked = ranked[:top_n]
    
    logger.info(f"Ranked insights: {len(ranked)} after filtering (min_impact={min_impact})")
    return ranked


def generate_insight_summary(insights: List[InsightRecord]) -> Dict[str, Any]:
    """
    Generate a summary of the insights.
    
    Args:
        insights: List of ranked insights
        
    Returns:
        Summary dictionary with overall statistics
    """
    if not insights:
        return {
            "total_insights": 0,
            "top_mover": None,
            "biggest_gain": None,
            "biggest_drop": None
        }
    
    gains = [i for i in insights if i.direction == "up"]
    drops = [i for i in insights if i.direction == "down"]
    
    summary = {
        "total_insights": len(insights),
        "total_gains": len(gains),
        "total_drops": len(drops),
        "top_mover": insights[0].to_dict() if insights else None,
        "biggest_gain": max(gains, key=lambda x: x.delta_pct).to_dict() if gains else None,
        "biggest_drop": min(drops, key=lambda x: x.delta_pct).to_dict() if drops else None,
    }
    
    return summary


def generate_insights(
    current_df: pl.DataFrame,
    previous_df: pl.DataFrame,
    config: InsightConfig,
    top_n: int = 20
) -> Dict[str, Any]:
    """
    Main entry point for insight generation.
    
    This function:
    1. Joins current and previous period data
    2. Extracts insight records for each dimension/metric combination
    3. Ranks insights by impact score
    4. Generates summary statistics
    
    Args:
        current_df: Aggregated current period DataFrame
        previous_df: Aggregated previous period DataFrame
        config: Insight configuration
        top_n: Number of top insights to return
        
    Returns:
        Dictionary containing:
        - insights: List of insight dictionaries
        - summary: Summary statistics
    """
    logger.info("Starting insight generation")
    
    dimensions = config.report.primary_dims
    kpi_priority = config.report.kpi_priority
    
    # Join periods
    joined = join_periods(current_df, previous_df, dimensions)
    
    # Extract insights
    insights = extract_insights(joined, dimensions, kpi_priority)
    
    # Rank insights
    ranked = rank_insights(insights, top_n=top_n)
    
    # Generate summary
    summary = generate_insight_summary(ranked)
    
    result = {
        "insights": [i.to_dict() for i in ranked],
        "summary": summary,
        "config": {
            "dimensions": dimensions,
            "kpis": kpi_priority,
            "current_period": f"{config.report.comparison.current_start} to {config.report.comparison.current_end}",
            "previous_period": f"{config.report.comparison.previous_start} to {config.report.comparison.previous_end}"
        }
    }
    
    logger.info(f"Insight generation complete. Top insight: {ranked[0].metric if ranked else 'N/A'}")
    return result
