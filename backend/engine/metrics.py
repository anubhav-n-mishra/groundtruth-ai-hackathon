"""
Metrics calculation module for the Automated Insight Engine.

This module handles derived KPI calculation, period splitting,
and aggregation by dimensions.
"""

import polars as pl
from typing import Dict, List, Tuple
from datetime import datetime
import re
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import InsightConfig
from core.logger import get_metrics_logger

logger = get_metrics_logger()


def parse_formula(formula: str) -> Tuple[str, str, str]:
    """
    Parse a simple arithmetic formula like "clicks / impressions".
    
    Supports: +, -, *, /
    
    Args:
        formula: Formula string with format "operand1 operator operand2"
        
    Returns:
        Tuple of (operand1, operator, operand2)
        
    Raises:
        ValueError: If formula cannot be parsed
    """
    # Match pattern: operand operator operand
    pattern = r'^\s*(\w+)\s*([+\-*/])\s*(\w+)\s*$'
    match = re.match(pattern, formula)
    
    if not match:
        raise ValueError(f"Cannot parse formula: {formula}")
    
    return match.group(1), match.group(2), match.group(3)


def compute_derived_metric(
    df: pl.DataFrame,
    metric_name: str,
    formula: str
) -> pl.DataFrame:
    """
    Compute a derived metric from a formula and add it to the DataFrame.
    
    Args:
        df: Input DataFrame
        metric_name: Name for the new metric column
        formula: Formula string (e.g., "clicks / impressions")
        
    Returns:
        pl.DataFrame: DataFrame with new metric column added
    """
    logger.debug(f"Computing derived metric '{metric_name}' from formula: {formula}")
    
    try:
        operand1, operator, operand2 = parse_formula(formula)
        
        # Verify columns exist
        if operand1 not in df.columns:
            raise ValueError(f"Column '{operand1}' not found for formula '{formula}'")
        if operand2 not in df.columns:
            raise ValueError(f"Column '{operand2}' not found for formula '{formula}'")
        
        # Build expression based on operator
        col1 = pl.col(operand1).cast(pl.Float64)
        col2 = pl.col(operand2).cast(pl.Float64)
        
        if operator == '+':
            expr = (col1 + col2).alias(metric_name)
        elif operator == '-':
            expr = (col1 - col2).alias(metric_name)
        elif operator == '*':
            expr = (col1 * col2).alias(metric_name)
        elif operator == '/':
            # Handle division by zero
            expr = pl.when(col2 != 0).then(col1 / col2).otherwise(0.0).alias(metric_name)
        else:
            raise ValueError(f"Unsupported operator: {operator}")
        
        return df.with_columns(expr)
        
    except Exception as e:
        logger.error(f"Failed to compute metric '{metric_name}': {e}")
        raise


def compute_all_derived_metrics(
    df: pl.DataFrame,
    derived_metrics: Dict[str, str]
) -> pl.DataFrame:
    """
    Compute all derived metrics defined in configuration.
    
    Args:
        df: Input DataFrame
        derived_metrics: Map of metric name to formula
        
    Returns:
        pl.DataFrame: DataFrame with all derived metrics added
    """
    logger.info(f"Computing {len(derived_metrics)} derived metric(s)")
    
    for metric_name, formula in derived_metrics.items():
        df = compute_derived_metric(df, metric_name, formula)
        logger.info(f"Added derived metric: {metric_name}")
    
    return df


def parse_date_column(df: pl.DataFrame, date_col: str) -> pl.DataFrame:
    """
    Ensure date column is properly parsed as Date type.
    
    Args:
        df: Input DataFrame
        date_col: Name of the date column
        
    Returns:
        pl.DataFrame: DataFrame with parsed date column
    """
    if date_col not in df.columns:
        raise ValueError(f"Date column '{date_col}' not found")
    
    # Check if already a date type
    col_dtype = df[date_col].dtype
    
    if col_dtype == pl.Date:
        return df
    
    if col_dtype == pl.Datetime:
        return df.with_columns(pl.col(date_col).dt.date().alias(date_col))
    
    # Try to parse as string
    logger.debug(f"Parsing date column '{date_col}' from string")
    
    # Try common date formats
    formats_to_try = ["%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y"]
    
    for fmt in formats_to_try:
        try:
            return df.with_columns(
                pl.col(date_col).str.to_date(fmt).alias(date_col)
            )
        except:
            continue
    
    # Last resort: let Polars infer
    try:
        return df.with_columns(
            pl.col(date_col).str.to_date().alias(date_col)
        )
    except Exception as e:
        logger.error(f"Failed to parse date column: {e}")
        raise ValueError(f"Cannot parse date column '{date_col}'")


def split_by_period(
    df: pl.DataFrame,
    config: InsightConfig
) -> Tuple[pl.DataFrame, pl.DataFrame]:
    """
    Split DataFrame into CURRENT and PREVIOUS periods based on config.
    
    Args:
        df: Input DataFrame with parsed date column
        config: Insight configuration
        
    Returns:
        Tuple of (current_df, previous_df)
    """
    date_col = config.report.primary_date_col
    comparison = config.report.comparison
    
    # Parse date strings
    current_start = datetime.strptime(comparison.current_start, "%Y-%m-%d").date()
    current_end = datetime.strptime(comparison.current_end, "%Y-%m-%d").date()
    previous_start = datetime.strptime(comparison.previous_start, "%Y-%m-%d").date()
    previous_end = datetime.strptime(comparison.previous_end, "%Y-%m-%d").date()
    
    logger.info(f"Splitting data: Current [{current_start} to {current_end}], Previous [{previous_start} to {previous_end}]")
    
    # Filter for current period
    current_df = df.filter(
        (pl.col(date_col) >= current_start) & 
        (pl.col(date_col) <= current_end)
    )
    
    # Filter for previous period
    previous_df = df.filter(
        (pl.col(date_col) >= previous_start) & 
        (pl.col(date_col) <= previous_end)
    )
    
    logger.info(f"Current period: {len(current_df)} rows, Previous period: {len(previous_df)} rows")
    
    return current_df, previous_df


def aggregate_by_dimensions(
    df: pl.DataFrame,
    dimensions: List[str],
    metrics: List[str]
) -> pl.DataFrame:
    """
    Aggregate data by dimensions, summing numeric metrics.
    
    Args:
        df: Input DataFrame
        dimensions: Columns to group by
        metrics: Metric columns to aggregate (sum)
        
    Returns:
        pl.DataFrame: Aggregated DataFrame
    """
    if not dimensions:
        # No dimensions, aggregate entire dataset
        logger.debug("No dimensions specified, aggregating entire dataset")
        agg_exprs = [pl.col(m).sum().alias(m) for m in metrics if m in df.columns]
        return df.select(agg_exprs)
    
    # Verify dimensions exist
    missing_dims = [d for d in dimensions if d not in df.columns]
    if missing_dims:
        raise ValueError(f"Missing dimension columns: {missing_dims}")
    
    # Build aggregation expressions
    agg_exprs = []
    for metric in metrics:
        if metric in df.columns:
            agg_exprs.append(pl.col(metric).sum().alias(metric))
    
    if not agg_exprs:
        raise ValueError("No valid metrics found to aggregate")
    
    result = df.group_by(dimensions).agg(agg_exprs)
    logger.debug(f"Aggregated to {len(result)} rows by dimensions: {dimensions}")
    
    return result


def get_all_metrics(config: InsightConfig) -> List[str]:
    """
    Get all metric names including base and derived metrics.
    
    Args:
        config: Insight configuration
        
    Returns:
        List of all metric names
    """
    # Get base metrics from primary source
    primary_source = config.dataset.sources[config.dataset.primary_source]
    metrics = list(primary_source.metrics)
    
    # Add derived metrics
    metrics.extend(config.derived_metrics.keys())
    
    # Add from KPI priority if not already included
    for kpi in config.report.kpi_priority:
        if kpi not in metrics:
            metrics.append(kpi)
    
    return metrics


def process_metrics(
    df: pl.DataFrame,
    config: InsightConfig
) -> Tuple[pl.DataFrame, pl.DataFrame]:
    """
    Main entry point for metrics processing.
    
    This function:
    1. Parses date column
    2. Computes derived metrics
    3. Splits by period
    4. Aggregates by dimensions
    
    Args:
        df: Input DataFrame from ingestion
        config: Insight configuration
        
    Returns:
        Tuple of (aggregated_current, aggregated_previous) DataFrames
    """
    logger.info("Starting metrics processing")
    
    # Parse date column
    date_col = config.report.primary_date_col
    df = parse_date_column(df, date_col)
    
    # Compute derived metrics
    if config.derived_metrics:
        df = compute_all_derived_metrics(df, config.derived_metrics)
    
    # Split by period
    current_df, previous_df = split_by_period(df, config)
    
    # Get all metrics to aggregate
    all_metrics = get_all_metrics(config)
    dimensions = config.report.primary_dims
    
    logger.info(f"Aggregating metrics: {all_metrics} by dimensions: {dimensions}")
    
    # Aggregate each period
    current_agg = aggregate_by_dimensions(current_df, dimensions, all_metrics)
    previous_agg = aggregate_by_dimensions(previous_df, dimensions, all_metrics)
    
    logger.info(f"Metrics processing complete. Current: {current_agg.shape}, Previous: {previous_agg.shape}")
    
    return current_agg, previous_agg
