"""
Test script for multi-source data ingestion.

This script tests:
1. CSV file loading
2. SQLite database loading (as a test for SQL databases)
3. Database table loading via SQLAlchemy
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import polars as pl
from pathlib import Path


def create_test_database():
    """Create a SQLite test database with sample data."""
    # Use absolute path
    base_dir = Path(__file__).parent.parent.parent
    db_path = base_dir / "data" / "test_conversions.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Remove existing database
    if db_path.exists():
        db_path.unlink()
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create conversions table
    cursor.execute('''
        CREATE TABLE conversions (
            date TEXT,
            campaign TEXT,
            geo TEXT,
            conversions INTEGER,
            revenue REAL
        )
    ''')
    
    # Insert sample data matching clicks.csv structure
    sample_data = [
        # Week 1 (Previous period: Nov 17-23)
        ('2025-11-17', 'Brand_Awareness', 'US', 45, 2250.0),
        ('2025-11-17', 'Brand_Awareness', 'UK', 32, 1600.0),
        ('2025-11-17', 'Performance_Max', 'US', 120, 6000.0),
        ('2025-11-17', 'Performance_Max', 'UK', 85, 4250.0),
        ('2025-11-17', 'Retargeting', 'US', 65, 3250.0),
        ('2025-11-17', 'Retargeting', 'UK', 48, 2400.0),
        ('2025-11-20', 'Brand_Awareness', 'US', 52, 2600.0),
        ('2025-11-20', 'Brand_Awareness', 'UK', 38, 1900.0),
        ('2025-11-20', 'Performance_Max', 'US', 135, 6750.0),
        ('2025-11-20', 'Performance_Max', 'UK', 92, 4600.0),
        ('2025-11-20', 'Retargeting', 'US', 72, 3600.0),
        ('2025-11-20', 'Retargeting', 'UK', 55, 2750.0),
        ('2025-11-23', 'Brand_Awareness', 'US', 48, 2400.0),
        ('2025-11-23', 'Brand_Awareness', 'UK', 35, 1750.0),
        ('2025-11-23', 'Performance_Max', 'US', 128, 6400.0),
        ('2025-11-23', 'Performance_Max', 'UK', 88, 4400.0),
        ('2025-11-23', 'Retargeting', 'US', 68, 3400.0),
        ('2025-11-23', 'Retargeting', 'UK', 52, 2600.0),
        # Week 2 (Current period: Nov 24-30)
        ('2025-11-24', 'Brand_Awareness', 'US', 55, 2750.0),
        ('2025-11-24', 'Brand_Awareness', 'UK', 42, 2100.0),
        ('2025-11-24', 'Performance_Max', 'US', 145, 7250.0),
        ('2025-11-24', 'Performance_Max', 'UK', 98, 4900.0),
        ('2025-11-24', 'Retargeting', 'US', 78, 3900.0),
        ('2025-11-24', 'Retargeting', 'UK', 62, 3100.0),
        ('2025-11-27', 'Brand_Awareness', 'US', 62, 3100.0),
        ('2025-11-27', 'Brand_Awareness', 'UK', 48, 2400.0),
        ('2025-11-27', 'Performance_Max', 'US', 158, 7900.0),
        ('2025-11-27', 'Performance_Max', 'UK', 108, 5400.0),
        ('2025-11-27', 'Retargeting', 'US', 85, 4250.0),
        ('2025-11-27', 'Retargeting', 'UK', 68, 3400.0),
        ('2025-11-30', 'Brand_Awareness', 'US', 58, 2900.0),
        ('2025-11-30', 'Brand_Awareness', 'UK', 45, 2250.0),
        ('2025-11-30', 'Performance_Max', 'US', 152, 7600.0),
        ('2025-11-30', 'Performance_Max', 'UK', 102, 5100.0),
        ('2025-11-30', 'Retargeting', 'US', 82, 4100.0),
        ('2025-11-30', 'Retargeting', 'UK', 65, 3250.0),
    ]
    
    cursor.executemany('''
        INSERT INTO conversions (date, campaign, geo, conversions, revenue)
        VALUES (?, ?, ?, ?, ?)
    ''', sample_data)
    
    conn.commit()
    conn.close()
    
    print(f"Created test database: {db_path}")
    return str(db_path)


def test_csv_source():
    """Test CSV source loading."""
    print("\n" + "="*50)
    print("TEST 1: CSV Source Loading")
    print("="*50)
    
    from engine.ingest import load_csv_source
    from core.config import SourceConfig
    
    base_dir = Path(__file__).parent.parent.parent
    
    config = SourceConfig(
        type="csv",
        path="data/clicks.csv",
        date_col="date",
        dimensions=["campaign", "geo"],
        metrics=["impressions", "clicks", "spend"]
    )
    
    df = load_csv_source("clicks", config, base_path=str(base_dir))
    print(f"✅ Loaded CSV: {len(df)} rows, {len(df.columns)} columns")
    print(f"   Columns: {df.columns}")
    print(df.head(3))
    return True


def test_sql_source():
    """Test SQL query source loading."""
    print("\n" + "="*50)
    print("TEST 2: SQL Query Source Loading")
    print("="*50)
    
    from engine.ingest import load_sql_source
    from core.config import SourceConfig
    
    db_path = create_test_database()
    
    # Use absolute path for SQLite
    abs_db_path = str(Path(db_path).absolute()).replace("\\", "/")
    
    config = SourceConfig(
        type="sql",
        connection_string=f"sqlite:///{abs_db_path}",
        query="SELECT * FROM conversions WHERE campaign = 'Performance_Max'",
        date_col="date",
        dimensions=["campaign", "geo"],
        metrics=["conversions", "revenue"]
    )
    
    df = load_sql_source("conversions", config)
    print(f"✅ Loaded SQL: {len(df)} rows, {len(df.columns)} columns")
    print(f"   Columns: {df.columns}")
    print(df.head(3))
    return True


def test_database_source():
    """Test database table source loading."""
    print("\n" + "="*50)
    print("TEST 3: Database Table Source Loading")
    print("="*50)
    
    from engine.ingest import load_database_source
    from core.config import SourceConfig, DatabaseConnectionConfig
    
    base_dir = Path(__file__).parent.parent.parent
    db_path = str(base_dir / "data" / "test_conversions.db").replace("\\", "/")
    
    config = SourceConfig(
        type="database",
        connection=DatabaseConnectionConfig(
            driver="sqlite",
            database=db_path
        ),
        table="conversions",
        date_col="date",
        dimensions=["campaign", "geo"],
        metrics=["conversions", "revenue"]
    )
    
    df = load_database_source("conversions_db", config)
    print(f"✅ Loaded Database: {len(df)} rows, {len(df.columns)} columns")
    print(f"   Columns: {df.columns}")
    print(df.head(3))
    return True


def test_multi_source_config():
    """Test loading from YAML config with multiple sources."""
    print("\n" + "="*50)
    print("TEST 4: Multi-Source Configuration")
    print("="*50)
    
    from core.config import load_config_from_string
    from engine.ingest import load_all_sources
    
    base_dir = Path(__file__).parent.parent.parent
    db_path = str(base_dir / "data" / "test_conversions.db").replace("\\", "/")
    
    config_yaml = f"""
dataset:
  primary_source: clicks
  sources:
    clicks:
      type: csv
      path: "data/clicks.csv"
      date_col: "date"
      dimensions:
        - campaign
        - geo
      metrics:
        - impressions
        - clicks
        - spend
    
    conversions:
      type: sql
      connection_string: "sqlite:///{db_path}"
      query: "SELECT * FROM conversions"
      date_col: "date"
      dimensions:
        - campaign
        - geo
      metrics:
        - conversions
        - revenue
      join_key:
        - campaign
        - geo
        - date

derived_metrics:
  ctr: "clicks / impressions"
  cpc: "spend / clicks"
  roas: "revenue / spend"
  cpa: "spend / conversions"

report:
  primary_date_col: date
  comparison:
    current_start: "2025-11-24"
    current_end: "2025-11-30"
    previous_start: "2025-11-17"
    previous_end: "2025-11-23"
  primary_dims:
    - campaign
    - geo
  kpi_priority:
    - roas
    - ctr
    - cpc
    - impressions
"""
    
    config = load_config_from_string(config_yaml)
    print(f"✅ Parsed config with {len(config.dataset.sources)} sources")
    
    sources = load_all_sources(config, base_path=str(base_dir))
    
    for name, df in sources.items():
        print(f"   Source '{name}': {len(df)} rows, columns: {df.columns}")
    
    return True


def run_all_tests():
    """Run all ingestion tests."""
    print("\n" + "#"*60)
    print("# MULTI-SOURCE DATA INGESTION TESTS")
    print("#"*60)
    
    results = []
    
    try:
        results.append(("CSV Source", test_csv_source()))
    except Exception as e:
        print(f"❌ CSV Source failed: {e}")
        results.append(("CSV Source", False))
    
    try:
        results.append(("SQL Source", test_sql_source()))
    except Exception as e:
        print(f"❌ SQL Source failed: {e}")
        results.append(("SQL Source", False))
    
    try:
        results.append(("Database Source", test_database_source()))
    except Exception as e:
        print(f"❌ Database Source failed: {e}")
        results.append(("Database Source", False))
    
    try:
        results.append(("Multi-Source Config", test_multi_source_config()))
    except Exception as e:
        print(f"❌ Multi-Source Config failed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Multi-Source Config", False))
    
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False
    
    print("="*60)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️  SOME TESTS FAILED")
    
    return all_passed


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    run_all_tests()
