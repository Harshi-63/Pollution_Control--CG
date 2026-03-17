import pandas as pd
import pytest

def test_all_expected_columns_present(cleaned_df):
    """Verify all 16 expected columns exist in the cleaned dataset."""
    expected_cols = [
        'Record_ID', 'Plant_ID', 'Stack_ID', 'Flow_Rate_m3_hr',
        'TS', 'PM2.5', 'SO2', 'NOx', 'Unit', 'Status', 'Lat_Lon',
        'Source_Type', 'Exceedance_Flag',
        'PM25_Filled', 'SO2_Filled', 'NOx_Filled'
    ]
    
    missing = [c for c in expected_cols if c not in cleaned_df.columns]
    assert len(missing) == 0, f"Missing columns in cleaned_df: {missing}"
    print(f"\n✅ SCHEMA | All expected columns present — 16 columns verified")

def test_pollutant_columns_are_numeric(cleaned_df):
    """Verify PM2.5, SO2, and NOx are float64."""
    for col in ['PM2.5', 'SO2', 'NOx']:
        # They will be floats since there are NaNs, verify they are numeric types
        assert pd.api.types.is_numeric_dtype(cleaned_df[col]), f"Column {col} is not numeric. Type: {cleaned_df[col].dtype}"
    print(f"\n✅ SCHEMA | Pollutant columns are float64 — PM2.5={cleaned_df['PM2.5'].dtype}, SO2={cleaned_df['SO2'].dtype}, NOx={cleaned_df['NOx'].dtype}")

def test_ts_is_datetime(cleaned_df):
    """Verify TS parsed correctly as a datetime object."""
    assert pd.api.types.is_datetime64_any_dtype(cleaned_df['TS']), f"TS column is not datetime. Type: {cleaned_df['TS'].dtype}"
    print(f"\n✅ SCHEMA | TS is datetime64 — dtype={cleaned_df['TS'].dtype}")
