"""
Data ingestion module for the Automated Insight Engine.

This module handles loading data from multiple sources:
- CSV files (using Polars)
- SQL queries (using connectorx or SQLAlchemy)
- Database tables (using SQLAlchemy connections)

Multiple sources are joined using DuckDB with Polars fallback.
"""

import polars as pl
import duckdb
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import InsightConfig, SourceConfig
from core.logger import get_ingest_logger

logger = get_ingest_logger()


def load_csv_source(
    source_name: str,
    source_config: SourceConfig,
    base_path: str = ""
) -> pl.DataFrame:
    """
    Load a CSV source into a Polars DataFrame.
    
    Args:
        source_name: Name identifier for the source
        source_config: Configuration for the source
        base_path: Base path to prepend to relative paths
        
    Returns:
        pl.DataFrame: Loaded data
        
    Raises:
        FileNotFoundError: If the CSV file doesn't exist
    """
    file_path = source_config.path
    if base_path and not Path(file_path).is_absolute():
        file_path = str(Path(base_path) / file_path)
    
    logger.info(f"Loading CSV source '{source_name}' from: {file_path}")
    
    if not Path(file_path).exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")
    
    try:
        # Read first line to detect delimiter
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline()
        
        # Auto-detect delimiter
        delimiter = ','
        semicolon_count = first_line.count(';')
        comma_count = first_line.count(',')
        tab_count = first_line.count('\t')
        
        if semicolon_count > comma_count and semicolon_count > tab_count:
            delimiter = ';'
        elif tab_count > comma_count and tab_count > semicolon_count:
            delimiter = '\t'
        
        logger.info(f"Detected delimiter: '{delimiter}' (semicolons: {semicolon_count}, commas: {comma_count}, tabs: {tab_count})")
        
        df = pl.read_csv(file_path, separator=delimiter)
        logger.info(f"Loaded {len(df)} rows from CSV '{source_name}' with columns: {df.columns}")
        return df
    except Exception as e:
        logger.error(f"Failed to load CSV source '{source_name}': {e}")
        raise


def load_sql_source(
    source_name: str,
    source_config: SourceConfig
) -> pl.DataFrame:
    """
    Load data from a SQL query into a Polars DataFrame.
    
    Uses connectorx for fast loading, with SQLAlchemy fallback.
    
    Args:
        source_name: Name identifier for the source
        source_config: Configuration with connection_string and query
        
    Returns:
        pl.DataFrame: Query results as DataFrame
    """
    connection_string = source_config.connection_string
    query = source_config.query
    
    logger.info(f"Loading SQL source '{source_name}'")
    logger.debug(f"Query: {query[:100]}..." if len(query) > 100 else f"Query: {query}")
    
    try:
        # Try connectorx first (fastest)
        import connectorx as cx
        df = pl.from_pandas(cx.read_sql(connection_string, query))
        logger.info(f"Loaded {len(df)} rows from SQL '{source_name}' via connectorx")
        return df
    except ImportError:
        logger.warning("connectorx not available, trying SQLAlchemy")
    except Exception as e:
        logger.warning(f"connectorx failed: {e}, trying SQLAlchemy")
    
    # Fallback to SQLAlchemy
    try:
        from sqlalchemy import create_engine, text
        import pandas as pd
        
        engine = create_engine(connection_string)
        with engine.connect() as conn:
            pdf = pd.read_sql(text(query), conn)
        
        df = pl.from_pandas(pdf)
        logger.info(f"Loaded {len(df)} rows from SQL '{source_name}' via SQLAlchemy")
        return df
    except Exception as e:
        logger.error(f"Failed to load SQL source '{source_name}': {e}")
        raise


def load_database_source(
    source_name: str,
    source_config: SourceConfig
) -> pl.DataFrame:
    """
    Load data from a database table into a Polars DataFrame.
    
    Builds a SELECT query from the table name and uses SQLAlchemy.
    
    Args:
        source_name: Name identifier for the source
        source_config: Configuration with connection and table
        
    Returns:
        pl.DataFrame: Table data as DataFrame
    """
    connection = source_config.connection
    table_name = source_config.table
    
    logger.info(f"Loading database source '{source_name}' from table '{table_name}'")
    
    try:
        # Build connection string from config
        connection_string = connection.get_connection_string()
        
        # Build SELECT query - select all columns or specific ones
        columns = []
        if source_config.dimensions:
            columns.extend(source_config.dimensions)
        if source_config.metrics:
            columns.extend(source_config.metrics)
        if source_config.date_col and source_config.date_col not in columns:
            columns.append(source_config.date_col)
        if source_config.join_key:
            for key in source_config.join_key:
                if key not in columns:
                    columns.append(key)
        
        if columns:
            columns_str = ", ".join([f'"{c}"' for c in columns])
            query = f'SELECT {columns_str} FROM "{table_name}"'
        else:
            query = f'SELECT * FROM "{table_name}"'
        
        logger.debug(f"Generated query: {query}")
        
        # Try connectorx first
        try:
            import connectorx as cx
            df = pl.from_pandas(cx.read_sql(connection_string, query))
            logger.info(f"Loaded {len(df)} rows from database '{source_name}' via connectorx")
            return df
        except Exception as e:
            logger.warning(f"connectorx failed: {e}, trying SQLAlchemy")
        
        # Fallback to SQLAlchemy
        from sqlalchemy import create_engine, text
        import pandas as pd
        
        engine = create_engine(connection_string)
        with engine.connect() as conn:
            pdf = pd.read_sql(text(query), conn)
        
        df = pl.from_pandas(pdf)
        logger.info(f"Loaded {len(df)} rows from database '{source_name}' via SQLAlchemy")
        return df
        
    except Exception as e:
        logger.error(f"Failed to load database source '{source_name}': {e}")
        raise


def load_source(
    source_name: str,
    source_config: SourceConfig,
    base_path: str = ""
) -> pl.DataFrame:
    """
    Load a single data source based on its type.
    
    Args:
        source_name: Name identifier for the source
        source_config: Configuration for the source
        base_path: Base path for relative file paths (CSV only)
        
    Returns:
        pl.DataFrame: Loaded data
    """
    source_type = getattr(source_config, 'type', 'csv')
    
    if source_type == "csv":
        return load_csv_source(source_name, source_config, base_path)
    elif source_type == "sql":
        return load_sql_source(source_name, source_config)
    elif source_type == "database":
        return load_database_source(source_name, source_config)
    else:
        raise ValueError(f"Unknown source type: {source_type}")


def load_all_sources(
    config: InsightConfig,
    base_path: str = ""
) -> Dict[str, pl.DataFrame]:
    """
    Load all data sources defined in the configuration.
    
    Args:
        config: Complete insight configuration
        base_path: Base path for relative file paths
        
    Returns:
        Dict[str, pl.DataFrame]: Map of source name to DataFrame
    """
    sources: Dict[str, pl.DataFrame] = {}
    
    for source_name, source_config in config.dataset.sources.items():
        sources[source_name] = load_source(source_name, source_config, base_path)
    
    logger.info(f"Loaded {len(sources)} data source(s)")
    return sources


def join_sources_duckdb(
    sources: Dict[str, pl.DataFrame],
    config: InsightConfig
) -> pl.DataFrame:
    """
    Join multiple data sources using DuckDB SQL.
    
    This function registers all sources as DuckDB tables and performs
    a SQL join based on common dimensions.
    
    Args:
        sources: Map of source name to DataFrame
        config: Insight configuration
        
    Returns:
        pl.DataFrame: Joined DataFrame
        
    Raises:
        Exception: If DuckDB join fails (will fallback to Polars)
    """
    if len(sources) == 1:
        # Single source, no join needed
        source_name = list(sources.keys())[0]
        logger.info(f"Single source '{source_name}', no join needed")
        return sources[source_name]
    
    logger.info("Joining sources using DuckDB")
    
    try:
        con = duckdb.connect(":memory:")
        
        # Register all DataFrames as DuckDB tables
        for name, df in sources.items():
            # Convert Polars to Arrow for DuckDB
            arrow_table = df.to_arrow()
            con.register(name, arrow_table)
            logger.debug(f"Registered table '{name}' with {len(df)} rows")
        
        # Get primary source info
        primary_name = config.dataset.primary_source
        primary_config = config.dataset.sources[primary_name]
        
        # Determine join keys from dimensions
        join_keys = config.report.primary_dims.copy()
        if primary_config.date_col not in join_keys:
            join_keys.append(primary_config.date_col)
        
        # Build JOIN SQL
        table_names = list(sources.keys())
        primary_table = primary_name
        
        # Start with SELECT from primary table
        select_cols = []
        
        # Add all columns from primary table
        primary_cols = sources[primary_table].columns
        for col in primary_cols:
            select_cols.append(f'"{primary_table}"."{col}" AS "{col}"')
        
        # Add non-overlapping columns from other tables
        for table_name in table_names:
            if table_name == primary_table:
                continue
            for col in sources[table_name].columns:
                if col not in primary_cols and col not in join_keys:
                    select_cols.append(f'"{table_name}"."{col}" AS "{col}"')
        
        sql = f'SELECT {", ".join(select_cols)} FROM "{primary_table}"'
        
        # Add LEFT JOINs for other tables
        for table_name in table_names:
            if table_name == primary_table:
                continue
            
            # Build ON clause using join keys
            on_conditions = []
            for key in join_keys:
                if key in sources[table_name].columns:
                    on_conditions.append(f'"{primary_table}"."{key}" = "{table_name}"."{key}"')
            
            if on_conditions:
                sql += f' LEFT JOIN "{table_name}" ON {" AND ".join(on_conditions)}'
        
        logger.debug(f"Join SQL: {sql}")
        
        # Execute and convert back to Polars
        result = con.execute(sql).pl()
        logger.info(f"DuckDB join successful, result has {len(result)} rows")
        
        con.close()
        return result
        
    except Exception as e:
        logger.warning(f"DuckDB join failed: {e}, falling back to Polars")
        raise


def join_sources_polars(
    sources: Dict[str, pl.DataFrame],
    config: InsightConfig
) -> pl.DataFrame:
    """
    Join multiple data sources using Polars (fallback method).
    
    Args:
        sources: Map of source name to DataFrame
        config: Insight configuration
        
    Returns:
        pl.DataFrame: Joined DataFrame
    """
    if len(sources) == 1:
        source_name = list(sources.keys())[0]
        return sources[source_name]
    
    logger.info("Joining sources using Polars")
    
    # Get primary source
    primary_name = config.dataset.primary_source
    result = sources[primary_name]
    
    # Determine join keys
    join_keys = config.report.primary_dims.copy()
    primary_config = config.dataset.sources[primary_name]
    if primary_config.date_col not in join_keys:
        join_keys.append(primary_config.date_col)
    
    # Join with other sources
    for source_name, df in sources.items():
        if source_name == primary_name:
            continue
        
        # Find common join keys
        common_keys = [k for k in join_keys if k in df.columns and k in result.columns]
        
        if common_keys:
            # Identify columns to keep from right table (avoid duplicates)
            right_cols = [c for c in df.columns if c not in result.columns or c in common_keys]
            df_subset = df.select(right_cols)
            
            result = result.join(df_subset, on=common_keys, how="left")
            logger.debug(f"Joined '{source_name}' on keys: {common_keys}")
    
    logger.info(f"Polars join complete, result has {len(result)} rows")
    return result


def join_sources(
    sources: Dict[str, pl.DataFrame],
    config: InsightConfig
) -> pl.DataFrame:
    """
    Join multiple data sources with DuckDB primary and Polars fallback.
    
    This is the main entry point for joining sources. It first attempts
    to use DuckDB for better SQL support, then falls back to Polars
    if DuckDB fails.
    
    Args:
        sources: Map of source name to DataFrame
        config: Insight configuration
        
    Returns:
        pl.DataFrame: Joined DataFrame
    """
    try:
        return join_sources_duckdb(sources, config)
    except Exception as e:
        logger.info(f"Falling back to Polars join due to: {e}")
        return join_sources_polars(sources, config)


def ingest_data(
    config: InsightConfig,
    base_path: str = ""
) -> pl.DataFrame:
    """
    Main entry point for data ingestion.
    
    This function loads all configured sources and joins them into
    a single DataFrame ready for analysis.
    
    Args:
        config: Complete insight configuration
        base_path: Base path for relative file paths
        
    Returns:
        pl.DataFrame: Joined and ready DataFrame
    """
    logger.info("Starting data ingestion")
    
    # Load all sources
    sources = load_all_sources(config, base_path)
    
    # Join sources
    df = join_sources(sources, config)
    
    # Validate date column exists (critical)
    primary_config = config.dataset.sources[config.dataset.primary_source]
    if primary_config.date_col not in df.columns:
        logger.warning(f"Date column '{primary_config.date_col}' not found. Available: {df.columns}")
        # Try to find a date-like column
        date_candidates = [c for c in df.columns if 'date' in c.lower() or 'dt_' in c.lower()]
        if date_candidates:
            logger.info(f"Using fallback date column: {date_candidates[0]}")
        else:
            raise ValueError(f"Date column '{primary_config.date_col}' not found in data")
    
    # Log available columns for debugging
    logger.info(f"Available columns: {df.columns}")
    logger.info(f"Data ingestion complete. Final shape: {df.shape}")
    return df
