import pytest
import pandas as pd
import re

def test_r10_maintenance_windows(cleaned_df, maint_df):
    """R10: All rows during maintenance have Status=MAINT."""
    maint_violations = 0
    for _, m in maint_df.iterrows():
        during_maint = cleaned_df[
            (cleaned_df['Plant_ID'] == m['Plant_ID']) &
            (cleaned_df['Stack_ID'] == m['Stack_ID']) &
            (cleaned_df['TS'] >= m['Maint_Start']) &
            (cleaned_df['TS'] <= m['Maint_End'])
        ]
        # these rows should all have Status=MAINT
        not_maint = during_maint[during_maint['Status'] != 'MAINT']
        maint_violations += len(not_maint)
    assert maint_violations == 0, f"Found {maint_violations} violations during scheduled maintenance"
    print(f"\n✅ R10      | All rows during maintenance have Status=MAINT — Violations: {maint_violations}")

def test_r11_no_bdl_strings(cleaned_df):
    """R11: No BDL strings remaining."""
    print()
    for col in ['PM2.5', 'SO2', 'NOx']:
        str_vals = cleaned_df[col].astype(str).str.strip().str.upper()
        bdl_remaining = str_vals.isin(['BDL']).sum() + str_vals.str.startswith('<').sum()
        assert bdl_remaining == 0, f"Found {bdl_remaining} BDL strings in {col}"
        print(f"✅ R11      | No BDL strings in {col} — Found: {bdl_remaining}")

def test_r12_canonical_status(cleaned_df):
    """R12: Only canonical status values exist."""
    canonical = {'OK', 'FAULT', 'MAINT', 'GAP_FILLED', 'UNKNOWN'}
    actual_statuses = set(cleaned_df['Status'].unique())
    non_canonical = actual_statuses - canonical
    assert len(non_canonical) == 0, f"Found non-canonical status values: {non_canonical}"
    print(f"\n✅ R12      | Only canonical status values exist — Values: {actual_statuses}")

def test_r13_plant_stack_combos(cleaned_df, sensors_df):
    """R13: All Plant+Stack combos in output exist in sensor_master."""
    valid_combos = set(zip(sensors_df['Plant_ID'], sensors_df['Stack_ID']))
    data_combos = set(zip(cleaned_df['Plant_ID'].dropna(), cleaned_df['Stack_ID'].dropna()))
    invalid_combos = data_combos - valid_combos
    assert len(invalid_combos) == 0, f"Found invalid Plant/Stack Combos: {invalid_combos}"
    print(f"\n✅ R13      | All Plant+Stack combos exist in sensor_master — All valid")

def test_r14_unit_is_ugm3(cleaned_df):
    """R14: All units are exactly ug/m3."""
    mg_remaining = (cleaned_df['Unit'] == 'mg/Nm3').sum()
    assert mg_remaining == 0, f"Found {mg_remaining} instances of mg/Nm3 remaining"
    all_ugm3 = (cleaned_df['Unit'] == 'ug/m3').all()
    assert all_ugm3, "Not all units are ug/m3"
    print(f"\n✅ R14      | No mg/Nm3 unit remaining — Found: {mg_remaining}")
    print(f"✅ R14      | All units are ug/m3 — Values: {cleaned_df['Unit'].value_counts().to_dict()}")

def test_r15_source_type(cleaned_df):
    """R15: Source_Type column exists and is valid."""
    assert 'Source_Type' in cleaned_df.columns, "Source_Type column is missing"
    valid_types = {'Stack', 'Ambient', 'Unknown'}
    actual_types = set(cleaned_df['Source_Type'].unique())
    assert actual_types.issubset(valid_types), f"Found invalid source types: {actual_types - valid_types}"
    print(f"\n✅ R15      | Source_Type column exists — Values: {cleaned_df['Source_Type'].value_counts().to_dict()}")
    print(f"✅ R15      | Source_Type has valid values only — Values: {actual_types}")

def test_r16_manual_qc_status(manual_df):
    """R16: QC_Status correctly flags >1% differences in manual entries."""
    assert 'QC_Status' in manual_df.columns, "QC_Status missing from manual entries"
    qc_correct = True
    for _, row in manual_df.iterrows():
        expected = 'QC_FAIL' if row['Diff_Pct'] > 1.0 else 'QC_PASS'
        if row['QC_Status'] != expected:
            qc_correct = False
            break
    assert qc_correct, "QC_Status logic (Diff_Pct > 1 == QC_FAIL) failed"
    print(f"\n✅ R16      | QC_Status column exists in manual entries — Values: {manual_df['QC_Status'].value_counts().to_dict()}")
    print(f"✅ R16      | QC_Status correctly flags >1% differences — Logic verified")

def test_r17_utc_conversions(cleaned_df, audit_df):
    """R17: Check timeline bounds showing UTC offset was applied."""
    r17_logs = len(audit_df[audit_df['Rule'] == 'R17'])
    assert r17_logs > 0, "R17 missing from audit log"
    valid_ts = cleaned_df['TS'].dropna()
    assert valid_ts.min().year >= 2025, f"Date ranges should correspond to the 2025 dataset, got {valid_ts.min().year}"
    print(f"\n✅ R17      | UTC-to-IST conversions were made — {r17_logs} conversions logged")
    print(f"✅ R17      | Date range is in 2025 (post-conversion) — {valid_ts.min()} to {valid_ts.max()}")

def test_r18_no_pii_in_notes(manual_df):
    """R18: No unredacted phone numbers/emails remain in Inspection_Notes."""
    phone_pattern = r'\b\d{10}\b'
    email_pattern = r'\S+@\S+\.\S+'
    pii_found = 0
    for note in manual_df['Inspection_Notes'].dropna():
        note_str = str(note)
        clean_note = note_str.replace('[REDACTED_PHONE]', '').replace('[REDACTED_EMAIL]', '')
        if re.search(phone_pattern, clean_note) or re.search(email_pattern, clean_note):
            pii_found += 1
    assert pii_found == 0, f"Found {pii_found} unredacted PII strings"
    redacted = manual_df['Inspection_Notes'].str.contains('REDACTED', na=False).sum()
    assert redacted > 0, "No redacted notes found, assuming PII replacement failed entirely"
    print(f"\n✅ R18      | No unredacted PII in Inspection_Notes — Unredacted PII: {pii_found}")
    print(f"✅ R18      | Redacted notes exist (proving PII was found & fixed) — {redacted} notes contain [REDACTED]")

def test_r19_exceedance_flag(cleaned_df, thresh_df):
    """R19: Exceedance flags exist and accurately simulate thresholds."""
    assert 'Exceedance_Flag' in cleaned_df.columns, "Exceedance_Flag column missing"
    limit_lookup = {}
    for _, t in thresh_df.iterrows():
        limit_lookup[(t['Pollutant'], t['Source_Type'])] = t['Legal_Limit_ugm3']
        
    sample = cleaned_df[cleaned_df['Source_Type'] != 'Unknown'].sample(min(100, len(cleaned_df)), random_state=42)
    mismatches = 0
    for _, row in sample.iterrows():
        should_flag = False
        for col in ['PM2.5', 'SO2', 'NOx']:
            val = row[col]
            if pd.notna(val):
                limit = limit_lookup.get((col, row['Source_Type']))
                if limit and val > limit:
                    should_flag = True
        expected = 'EXCEEDANCE' if should_flag else 'OK'
        if row['Exceedance_Flag'] != expected:
            mismatches += 1
            
    assert mismatches == 0, f"Checked {len(sample)} rows, mismatches: {mismatches}"
    print(f"\n✅ R19      | Exceedance_Flag column exists — Values: {cleaned_df['Exceedance_Flag'].value_counts().to_dict()}")
    print(f"✅ R19      | Exceedance flags are correct (spot-check) — Checked {len(sample)} rows, mismatches: {mismatches}")

def test_r9b_gap_fill_validity(cleaned_df, audit_df):
    """R9b: Gap-fill boolean flag columns exist and numeric constraints."""
    flag_cols = ['PM25_Filled', 'SO2_Filled', 'NOx_Filled']
    for c in flag_cols:
        assert c in cleaned_df.columns, f"{c} flag column is missing"
    print(f"\n✅ R9b      | Gap-fill flag columns exist — Columns: {flag_cols}")
        
    for col, flag in [('PM2.5','PM25_Filled'), ('SO2','SO2_Filled'), ('NOx','NOx_Filled')]:
        filled_vals = cleaned_df[cleaned_df[flag] == True][col]
        bad_fills = (filled_vals < 0).sum() if len(filled_vals) > 0 else 0
        assert bad_fills == 0, f"Found {bad_fills} negative fills for {col}"
        print(f"✅ R9b      | {col} filled values are valid (n={len(filled_vals)}) — Negative fills: {bad_fills}")
        
    r9b_logs = len(audit_df[audit_df['Rule'] == 'R9b'])
    assert r9b_logs > 0, "R9b missing from audit log"
    print(f"✅ R9b      | Audit log has R9b gap-fill entries — {r9b_logs} entries")
