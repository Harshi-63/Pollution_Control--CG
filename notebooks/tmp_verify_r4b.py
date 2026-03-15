"""Verify the Rule 4b backfill logic works correctly on the actual data."""
import pandas as pd, numpy as np

# Load cleaned data (this is what the notebook produces)
df = pd.read_csv('../cleaned/full/raw_cems_data_cleaned.csv')
print(f"Loaded {len(df)} rows from cleaned data")

# Check current NaN Lat_Lon
nan_before = df['Lat_Lon'].isna().sum()
gap_filled = df['Status'].eq('GAP_FILLED').sum()
print(f"\nBEFORE backfill:")
print(f"  NaN Lat_Lon: {nan_before}")
print(f"  GAP_FILLED rows: {gap_filled}")
print(f"  NaN Lat_Lon that are NOT gap-filled: {nan_before - gap_filled}")

# Build coord mode lookup
coord_mode = (
    df[df['Lat_Lon'].notna()]
    .groupby('Plant_ID')['Lat_Lon']
    .agg(lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else np.nan)
)
print(f"\nCoordinate mode per Plant_ID:")
print(coord_mode.to_string())

# Simulate the backfill
backfill_count = 0
for idx in df[df['Lat_Lon'].isna()].index:
    pid = df.at[idx, 'Plant_ID']
    if pd.isna(pid):
        continue
    fill_val = coord_mode.get(pid)
    if pd.notna(fill_val):
        df.at[idx, 'Lat_Lon'] = fill_val
        backfill_count += 1

nan_after = df['Lat_Lon'].isna().sum()
print(f"\nAFTER backfill:")
print(f"  Backfilled: {backfill_count} values")
print(f"  NaN remaining: {nan_after}")
print(f"  (remaining are GAP_FILLED rows with no Plant_ID)")

# Verify: remaining NaNs should all be GAP_FILLED
remaining_nan = df[df['Lat_Lon'].isna()]
non_gapfilled_nan = remaining_nan[remaining_nan['Status'] != 'GAP_FILLED']
if len(non_gapfilled_nan) == 0:
    print(f"\n  PASS: All remaining NaN Lat_Lon are GAP_FILLED rows")
else:
    print(f"\n  FAIL: {len(non_gapfilled_nan)} non-GAP_FILLED rows still have NaN Lat_Lon")
    print(non_gapfilled_nan.head())
