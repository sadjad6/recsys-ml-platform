"""
RecSys ML Platform — Data Quality Plugin.

Contains reusable validation functions to check data quality
before processing or model training.
"""

from pyspark.sql import DataFrame
from pyspark.sql.functions import col, isnull

def check_nulls(df: DataFrame, critical_columns: list[str]) -> bool:
    """Check if critical columns contain any nulls. Returns False if nulls exist."""
    for column in critical_columns:
        if df.filter(col(column).isNull() | isnull(col(column))).count() > 0:
            print(f"Data Quality Error: Nulls found in column '{column}'")
            return False
    return True

def check_row_count(df: DataFrame, min_count: int) -> bool:
    """Check if the DataFrame has at least min_count rows."""
    count = df.count()
    if count < min_count:
        print(f"Data Quality Error: Row count {count} is below threshold {min_count}")
        return False
    return True

def check_no_duplicates(df: DataFrame, unique_columns: list[str]) -> bool:
    """Check if specific columns form a unique key."""
    total_count = df.count()
    distinct_count = df.select(*unique_columns).distinct().count()
    if total_count != distinct_count:
        print(f"Data Quality Error: Duplicates found in {unique_columns}")
        return False
    return True

def run_all_checks(df: DataFrame, critical_cols: list[str], min_rows: int, unique_cols: list[str] = None) -> bool:
    """Run a suite of data quality checks."""
    if not check_nulls(df, critical_cols):
        return False
    if not check_row_count(df, min_rows):
        return False
    if unique_cols and not check_no_duplicates(df, unique_cols):
        return False
    return True
