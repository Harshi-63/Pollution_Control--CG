import pytest
import pandas as pd
import os

# Adjust path assuming tests are run from notebooks directory
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'cleaned', 'full')

@pytest.fixture(scope="session")
def cleaned_df():
    """Returns the cleaned raw CEMS data."""
    df = pd.read_csv(f'{DATA_DIR}/raw_cems_data_cleaned.csv')
    df['TS'] = pd.to_datetime(df['TS'], errors='coerce')
    return df

@pytest.fixture(scope="session")
def manual_df():
    """Returns the cleaned manual entries."""
    return pd.read_csv(f'{DATA_DIR}/manual_entries_cleaned.csv')

@pytest.fixture(scope="session")
def sensors_df():
    """Returns the sensor master data."""
    return pd.read_csv(f'{DATA_DIR}/sensor_master.csv')

@pytest.fixture(scope="session")
def maint_df():
    """Returns the maintenance logs."""
    maint = pd.read_csv(f'{DATA_DIR}/maintenance_logs.csv')
    maint['Maint_Start'] = pd.to_datetime(maint['Maint_Start'])
    maint['Maint_End'] = pd.to_datetime(maint['Maint_End'])
    return maint

@pytest.fixture(scope="session")
def thresh_df():
    """Returns the regulatory thresholds."""
    return pd.read_csv(f'{DATA_DIR}/regulatory_thresholds.csv')

@pytest.fixture(scope="session")
def audit_df():
    """Returns the cleaning audit log."""
    return pd.read_csv(f'{DATA_DIR}/cleaning_log.csv')

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Custom hook to print a big summary block at the end of the test run, like the notebook did."""
    try:
        df = pd.read_csv(f'{DATA_DIR}/raw_cems_data_cleaned.csv')
        df['TS'] = pd.to_datetime(df['TS'], errors='coerce')
        audit = pd.read_csv(f'{DATA_DIR}/cleaning_log.csv')
        
        terminalreporter.write_line("\n" + "="*60)
        terminalreporter.write_line("  DATA QUALITY SUMMARY")
        terminalreporter.write_line("="*60)
        terminalreporter.write_line(f"  Total rows:         {len(df):,}")
        terminalreporter.write_line(f"  Total columns:      {len(df.columns)}")
        terminalreporter.write_line(f"  Audit log entries:  {len(audit):,}")
        terminalreporter.write_line(f"  Date range:         {df['TS'].min()} to {df['TS'].max()}")
        terminalreporter.write_line(f"  Unit values:        {df['Unit'].unique().tolist()}")
        terminalreporter.write_line(f"  Status values:      {sorted(df['Status'].unique().tolist())}")
        terminalreporter.write_line("\nPollutant ranges (after cleaning):")
        for col in ['PM2.5', 'SO2', 'NOx']:
            vals = df[col].dropna()
            terminalreporter.write_line(f"  {col:6s}: min={vals.min():.1f}, max={vals.max():.1f}, mean={vals.mean():.1f}, nulls={df[col].isna().sum()}")
        terminalreporter.write_line("="*60 + "\n")
    except Exception as e:
        pass
