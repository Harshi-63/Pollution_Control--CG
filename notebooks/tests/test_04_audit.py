import pytest
import pandas as pd

def test_audit_log_not_empty(audit_df):
    """Verify the audit log generated events."""
    assert len(audit_df) > 0, f"Audit log is empty, expected entries"
    print(f"\n✅ AUDIT    | Audit log is non-empty — {len(audit_df)} entries")

def test_all_expected_rules_in_audit(audit_df):
    """Verify all 14 cleaning rules modifying columns appear at least once."""
    logged_rules = set(audit_df['Rule'].unique())
    expected_rules = {
        'R1', 'R2', 'R3', 'R4', 'R5', 'R7', 'R8', 'R9',
        'R10', 'R11', 'R12', 'R14', 'R17', 'TS_FORMAT'
    }
    missing_rules = expected_rules - logged_rules
    assert len(missing_rules) == 0, f"Rules missing from audit log: {missing_rules}"
    print(f"\n✅ AUDIT    | All cleaning rules appear in audit log — Rules logged: {sorted(list(logged_rules))}")
    print(f"\nAudit log breakdown by rule:\n{audit_df['Rule'].value_counts().to_string()}")

def test_audit_log_schema(audit_df):
    """Verify the audit log possesses the necessary schema identifiers."""
    audit_cols = {'Record_ID', 'Column', 'Old', 'New', 'Rule'}
    audit_cols_present = audit_cols.issubset(set(audit_df.columns))
    assert audit_cols_present, f"Missing columns in audit log: {audit_cols - set(audit_df.columns)}"
    print(f"\n✅ AUDIT    | Audit log has all required columns — Columns: {list(audit_cols)}")
