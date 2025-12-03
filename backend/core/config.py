"""
Configuration module for the Automated Insight Engine.

This module handles loading and validating YAML configuration files
that define data sources, metrics, and report parameters.
"""

from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, validator
import yaml
import os
import re
from pathlib import Path


class DatabaseConnectionConfig(BaseModel):
    """Configuration for direct database connection."""
    driver: str = Field(..., description="Database driver: postgresql, mysql, sqlite, mssql")
    host: str = Field(default="localhost", description="Database host")
    port: Optional[int] = Field(default=None, description="Database port")
    database: str = Field(..., description="Database name")
    username: Optional[str] = Field(default=None, description="Database username (supports ${ENV_VAR})")
    password: Optional[str] = Field(default=None, description="Database password (supports ${ENV_VAR})")
    
    def get_connection_string(self) -> str:
        """Build connection string from components."""
        # Resolve environment variables
        username = self._resolve_env_var(self.username) if self.username else None
        password = self._resolve_env_var(self.password) if self.password else None
        
        # Determine port defaults
        port = self.port
        if port is None:
            port_defaults = {
                "postgresql": 5432,
                "mysql": 3306,
                "mssql": 1433,
                "sqlite": None
            }
            port = port_defaults.get(self.driver)
        
        # Build connection string based on driver
        if self.driver == "sqlite":
            return f"sqlite:///{self.database}"
        
        auth = ""
        if username:
            auth = username
            if password:
                auth += f":{password}"
            auth += "@"
        
        port_str = f":{port}" if port else ""
        
        driver_map = {
            "postgresql": "postgresql",
            "mysql": "mysql+mysqlconnector",
            "mssql": "mssql+pyodbc"
        }
        
        driver_prefix = driver_map.get(self.driver, self.driver)
        return f"{driver_prefix}://{auth}{self.host}{port_str}/{self.database}"
    
    def _resolve_env_var(self, value: str) -> str:
        """Resolve ${ENV_VAR} patterns to actual values."""
        if not value:
            return value
        pattern = r'\$\{([^}]+)\}'
        def replacer(match):
            env_var = match.group(1)
            return os.getenv(env_var, "")
        return re.sub(pattern, replacer, value)


class SourceConfig(BaseModel):
    """Configuration for a single data source (CSV, SQL, or Database)."""
    # Source type
    type: Literal["csv", "sql", "database"] = Field(default="csv", description="Source type: csv, sql, or database")
    
    # CSV source fields
    path: Optional[str] = Field(default=None, description="Path to the CSV file (for type=csv)")
    
    # SQL source fields
    connection_string: Optional[str] = Field(default=None, description="Database connection string (for type=sql)")
    query: Optional[str] = Field(default=None, description="SQL query to execute (for type=sql)")
    
    # Database source fields
    connection: Optional[DatabaseConnectionConfig] = Field(default=None, description="Database connection config (for type=database)")
    table: Optional[str] = Field(default=None, description="Table name to query (for type=database)")
    
    # Common fields
    date_col: str = Field(..., description="Name of the date column")
    dimensions: List[str] = Field(default_factory=list, description="Dimension columns for grouping")
    metrics: List[str] = Field(default_factory=list, description="Metric columns to aggregate")
    join_key: Optional[List[str]] = Field(default=None, description="Keys to use for joining with other sources")
    
    @validator('path', always=True)
    def validate_csv_source(cls, v, values):
        if values.get('type') == 'csv' and not v:
            raise ValueError("'path' is required for CSV sources")
        return v
    
    @validator('connection_string', always=True)
    def validate_sql_source(cls, v, values):
        if values.get('type') == 'sql' and not v:
            raise ValueError("'connection_string' is required for SQL sources")
        return v
    
    @validator('query', always=True)
    def validate_sql_query(cls, v, values):
        if values.get('type') == 'sql' and not v:
            raise ValueError("'query' is required for SQL sources")
        return v
    
    @validator('connection', always=True)
    def validate_db_connection(cls, v, values):
        if values.get('type') == 'database' and not v:
            raise ValueError("'connection' is required for database sources")
        return v
    
    @validator('table', always=True)
    def validate_db_table(cls, v, values):
        if values.get('type') == 'database' and not v:
            raise ValueError("'table' is required for database sources")
        return v


class DatasetConfig(BaseModel):
    """Configuration for the dataset section."""
    primary_source: str = Field(..., description="Name of the primary data source")
    sources: Dict[str, SourceConfig] = Field(..., description="Map of source name to source config")


class ComparisonConfig(BaseModel):
    """Configuration for date comparison periods."""
    current_start: str = Field(..., description="Start date of current period (YYYY-MM-DD)")
    current_end: str = Field(..., description="End date of current period (YYYY-MM-DD)")
    previous_start: str = Field(..., description="Start date of previous period (YYYY-MM-DD)")
    previous_end: str = Field(..., description="End date of previous period (YYYY-MM-DD)")


class ReportConfig(BaseModel):
    """Configuration for report generation."""
    primary_date_col: str = Field(..., description="Primary date column for filtering")
    comparison: ComparisonConfig = Field(..., description="Date comparison configuration")
    primary_dims: List[str] = Field(default_factory=list, description="Primary dimensions for analysis")
    kpi_priority: List[str] = Field(default_factory=list, description="KPIs in priority order")


class InsightConfig(BaseModel):
    """
    Complete configuration schema for the Insight Engine.
    
    Attributes:
        dataset: Dataset configuration including sources
        derived_metrics: Dictionary of metric name to formula
        report: Report generation configuration
    """
    dataset: DatasetConfig
    derived_metrics: Dict[str, str] = Field(default_factory=dict, description="Derived metric formulas")
    report: ReportConfig


def load_config(config_path: str) -> InsightConfig:
    """
    Load and validate configuration from a YAML file.
    
    Args:
        config_path: Path to the YAML configuration file
        
    Returns:
        InsightConfig: Validated configuration object
        
    Raises:
        FileNotFoundError: If the config file doesn't exist
        ValueError: If the config is invalid
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        raw_config = yaml.safe_load(f)
    
    if raw_config is None:
        raise ValueError("Empty configuration file")
    
    return InsightConfig(**raw_config)


def load_config_from_string(config_content: str) -> InsightConfig:
    """
    Load and validate configuration from a YAML string.
    
    Args:
        config_content: YAML configuration as a string
        
    Returns:
        InsightConfig: Validated configuration object
        
    Raises:
        ValueError: If the config is invalid
    """
    raw_config = yaml.safe_load(config_content)
    
    if raw_config is None:
        raise ValueError("Empty configuration content")
    
    return InsightConfig(**raw_config)


# Application settings (environment-based)
class AppSettings(BaseModel):
    """Application-wide settings."""
    gemini_api_key: str = Field(default="", description="Google Gemini API key")
    openai_api_key: str = Field(default="", description="OpenAI API key")
    llm_provider: str = Field(default="auto", description="LLM provider: gemini, openai, or auto")
    llm_model: str = Field(default="gemini-2.0-flash", description="LLM model to use")
    reports_dir: str = Field(default="static/reports", description="Directory to save reports")
    tmp_dir: str = Field(default="tmp", description="Temporary file directory")
    log_level: str = Field(default="INFO", description="Logging level")
    
    class Config:
        env_prefix = "INSIGHT_ENGINE_"


def get_app_settings() -> AppSettings:
    """
    Get application settings from environment variables.
    
    Returns:
        AppSettings: Application settings object
    """
    import os
    return AppSettings(
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        llm_provider=os.getenv("INSIGHT_ENGINE_LLM_PROVIDER", "auto"),
        llm_model=os.getenv("INSIGHT_ENGINE_LLM_MODEL", "gemini-1.5-flash"),
        reports_dir=os.getenv("INSIGHT_ENGINE_REPORTS_DIR", "static/reports"),
        tmp_dir=os.getenv("INSIGHT_ENGINE_TMP_DIR", "tmp"),
        log_level=os.getenv("INSIGHT_ENGINE_LOG_LEVEL", "INFO"),
    )
