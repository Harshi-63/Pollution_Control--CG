import pytest
import pandas as pd

def test_r1_no_midnight_rollover(cleaned_df, audit_df):
    """R1: Verify no 24:xx timestamps remain and gap-filled rows match TS nulls."""
    ts_nulls = cleaned_df['TS'].isna().sum()
    gap_filled = (cleaned_df['Status'] == 'GAP_FILLED').sum()
    assert ts_nulls == gap_filled, f"TS nulls={ts_nulls}, gap_filled={gap_filled} (should match)"
    
    r1_logs = len(audit_df[audit_df['Rule'] == 'R1'])
    assert r1_logs > 0, f"R1 missing from audit log. found {r1_logs}"
    print(f"\n✅ R1       | No midnight rollover (24:xx) — all timestamps parsed — TS nulls={ts_nulls}, gap_filled={gap_filled} (should match)")
    print(f"✅ R1       | Audit log has midnight rollover entries — {r1_logs} changes logged")

def test_r2_no_unicode_units(cleaned_df, audit_df):
    """R2: Verify no unicode µg/m³ remaining."""
    unicode_units = cleaned_df['Unit'].isin(['\u00b5g/m\u00b3']).sum()
    assert unicode_units == 0, f"Found {unicode_units} unicode units"
    r2_logs = len(audit_df[audit_df['Rule'] == 'R2'])
    assert r2_logs > 0, "R2 missing from audit log"
    print(f"\n✅ R2       | No unicode µg/m³ remaining — Found: {unicode_units}")
    print(f"✅ R2       | Audit log has unit standardization entries — {r2_logs} changes logged")

def test_r3_status_formatting(cleaned_df):
    """R3: Verify Status values are trimmed and uppercased."""
    has_whitespace = cleaned_df['Status'].str.contains(r'^\s|\s$', regex=True, na=False).sum()
    assert has_whitespace == 0, f"Found {has_whitespace} Status rows with whitespace"
    
    has_lowercase = cleaned_df['Status'].apply(lambda s: s != s.upper() if isinstance(s, str) else False).sum()
    assert has_lowercase == 0, f"Found {has_lowercase} Status rows with lowercase letters"
    print(f"\n✅ R3       | No leading/trailing whitespace in Status — Found: {has_whitespace}")
    print(f"✅ R3       | All Status values are uppercase — Found: {has_lowercase}")

def test_r4_coordinates_valid(cleaned_df):
    """R4: Verify no semicolons in Lat_Lon and all within India bounds."""
    LAT_MIN, LAT_MAX = 6.0, 37.0
    LON_MIN, LON_MAX = 68.0, 97.5

    invalid_coords = 0
    semicolons = 0
    for val in cleaned_df['Lat_Lon'].dropna():
        s = str(val)
        if ';' in s:
            semicolons += 1
        try:
            parts = s.split(',')
            lat, lon = float(parts[0]), float(parts[1])
            if lat < LAT_MIN or lat > LAT_MAX or lon < LON_MIN or lon > LON_MAX:
                invalid_coords += 1
        except:
            invalid_coords += 1

    assert semicolons == 0, f"Found {semicolons} semicolons in Lat_Lon"
    assert invalid_coords == 0, f"Found {invalid_coords} coordinates outside bounds"
    print(f"\n✅ R4       | No semicolons in Lat_Lon — Found: {semicolons}")
    print(f"✅ R4       | All coordinates within India bounds — Invalid: {invalid_coords}")

def test_r5_no_negative_pollutants(cleaned_df):
    """R5: No negative pollutant values (PM2.5, SO2, NOx)."""
    print()
    for col in ['PM2.5', 'SO2', 'NOx']:
        neg_count = (cleaned_df[col] < 0).sum()
        assert neg_count == 0, f"Found {neg_count} negative values in {col}"
        print(f"✅ R5       | No negatives in {col} — Found: {neg_count}")

def test_r6_no_duplicates(cleaned_df):
    """R6: No duplicates on Plant_ID + Stack_ID + TS (excluding gap-fills)."""
    non_gap = cleaned_df[cleaned_df['Status'] != 'GAP_FILLED']
    dups = non_gap.duplicated(subset=['Plant_ID', 'Stack_ID', 'TS'], keep=False).sum()
    assert dups == 0, f"Found {dups} duplicate rows"
    print(f"\n✅ R6       | No duplicate rows (Plant+Stack+TS) — Duplicates: {dups}")

def test_r7_calibration_audit(audit_df):
    """R7: Verify calibration adjustments exist in the audit log."""
    r7_logs = len(audit_df[audit_df['Rule'] == 'R7'])
    assert r7_logs > 0, f"R7 missing from audit log. found {r7_logs}"
    print(f"\n✅ R7       | Calibration adjustments were made — {r7_logs} adjustments logged")

def test_r8_no_spikes(cleaned_df):
    """R8: No physical spikes > 5000 remain."""
    print()
    for col in ['PM2.5', 'SO2', 'NOx']:
        over_5000 = (cleaned_df[col] > 5000).sum()
        assert over_5000 == 0, f"Found {over_5000} spikes > 5000 in {col}"
        print(f"✅ R8       | No spikes > 5000 in {col} — Found: {over_5000}, max={cleaned_df[col].max():.1f}")

def test_r9_record_id_continuous(cleaned_df):
    """R9: Record_IDs are continuous (E00001 to E0XXXX) with no gaps."""
    record_nums = cleaned_df['Record_ID'].str.replace('E', '').astype(int)
    expected_range = set(range(record_nums.min(), record_nums.max() + 1))
    actual_range = set(record_nums)
    gaps = expected_range - actual_range
    assert len(gaps) == 0, f"Missing {len(gaps)} IDs"
    print(f"\n✅ R9       | Record_IDs are continuous (no gaps) — Missing IDs: {len(gaps)}")

def test_r9_gap_filled_values(cleaned_df):
    """R9: GAP_FILLED rows have exactly NaN pollutant values initially."""
    gap_rows = cleaned_df[cleaned_df['Status'] == 'GAP_FILLED']
    gap_all_nan = gap_rows[['PM2.5', 'SO2', 'NOx']].isna().all().all()
    assert gap_all_nan, f"Not all {len(gap_rows)} gap-filled rows have NaN pollutants"
    print(f"\n✅ R9       | GAP_FILLED rows have NaN pollutant values — {len(gap_rows)} gap-filled rows")
