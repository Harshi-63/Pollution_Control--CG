# Cleaned Dataset — Column Reference

A guide to every column in the cleaned output files, which rule created or modified it, and what it means.

---

## `raw_cems_data_cleaned.csv`

| # | Column | Type | Rule(s) | Description |
|---|--------|------|---------|-------------|
| 1 | `Record_ID` | string | R9 | Unique row ID (`E00001`–`E06000`). R9 fills gaps with placeholder IDs. |
| 2 | `Plant_ID` | string | R13 | Plant identifier (e.g. `PL-01`, `LOC-DEL-01`). Validated against `sensor_master`. |
| 3 | `Stack_ID` | string | R13 | Sensor/stack identifier (e.g. `S-01`, `A-01`). Validated with Plant_ID. |
| 4 | `Flow_Rate_m3_hr` | float | — | Gas flow rate (m³/hr). `NaN` for ambient sensors (no chimney). Untouched by cleaning. |
| 5 | `TS` | datetime | R1, R17, TS_FMT | Timestamp in `YYYY-MM-DD HH:MM:SS` format. Fixed: slash→dash, ISO→standard, midnight rollover (24:xx→00:xx+1day), UTC→IST (+5:30). |
| 6 | `PM2.5` | float | R5, R7, R8, R11, R14 | PM2.5 concentration (µg/m³). Negatives→NaN (R5), BDL→LOD/2 (R11), mg/Nm3×1000 (R14), calibrated (R7), spikes capped (R8). |
| 7 | `SO2` | float | R5, R7, R8, R11, R14 | SO2 concentration (µg/m³). Same cleaning pipeline as PM2.5. |
| 8 | `NOx` | float | R5, R7, R8, R11, R14 | NOx concentration (µg/m³). Same cleaning pipeline as PM2.5. |
| 9 | `Unit` | string | R2, R14 | Measurement unit. All standardized to `ug/m3`. Unicode µg/m³ fixed (R2), mg/Nm3 converted (R14). |
| 10 | `Status` | string | R3, R10, R12 | Canonical status. Trimmed/uppercased (R3), non-standard mapped (R12), maintenance windows applied (R10). **Values:** `OK`, `FAULT`, `MAINT`, `GAP_FILLED`, `UNKNOWN`. |
| 11 | `Lat_Lon` | string | R4 | Latitude,Longitude as comma-separated string. Semicolons fixed, swapped coords fixed, impossible values nulled (R4). |
| 12 | `Source_Type` | string | R15 | **New column.** Tagged from `sensor_master`. **Values:** `Stack`, `Ambient`, `Unknown` (for gap-filled). |
| 13 | `Exceedance_Flag` | string | R19 | **New column.** `EXCEEDANCE` if any pollutant exceeds the legal limit for its Source_Type. `OK` otherwise. |
| 14 | `Audit_Hash` | string | R20 | **New column.** SHA-256 hash of the entire row — for tamper detection and data integrity verification. |

---

## `manual_entries_cleaned.csv`

| # | Column | Type | Rule(s) | Description |
|---|--------|------|---------|-------------|
| 1 | `Log_ID` | string | — | Unique log entry ID (e.g. `L0001`). |
| 2 | `Plant_ID` | string | — | Plant where the manual entry was recorded. |
| 3 | `Lab_PM25_Entry1` | float | R16 | First technician's PM2.5 reading. Compared with Entry2 for QC. |
| 4 | `Lab_PM25_Entry2` | float | R16 | Second technician's PM2.5 reading. |
| 5 | `Inspection_Notes` | string | R18 | Free-text notes. Emails → `[REDACTED_EMAIL]`, phone numbers → `[REDACTED_PHONE]`. |
| 6 | `Diff_Pct` | float | R16 | **New column.** Percentage difference between Entry1 and Entry2. |
| 7 | `QC_Status` | string | R16 | **New column.** `QC_PASS` if diff ≤1%, `QC_FAIL` if diff >1%. |

---

## `cleaning_log.csv` (Audit Trail)

| Column | Description |
|--------|-------------|
| `Record_ID` | Which row was changed. |
| `Column` | Which column was changed (or `ALL` for gap-filled rows). |
| `Old_Value` | Value before the change. |
| `New_Value` | Value after the change. |
| `Rule` | Which rule triggered this change (e.g. `R2`, `R5`, `R14`). |

> **25,811 entries** — every single change is traceable back to a specific rule and record.

---

## Status Values Explained

| Status | Meaning | How It Got There |
|--------|---------|-----------------|
| `OK` | Normal reading | Original data |
| `FAULT` | Sensor error/offline | R12 mapped `OFFLINE`, `DOWN`, `ERROR`, `ERROR 404` → `FAULT` |
| `MAINT` | Under maintenance | R10 applied maintenance windows from `maintenance_logs.csv` |
| `GAP_FILLED` | Data gap placeholder | R9 inserted placeholder row for missing Record_ID |
| `UNKNOWN` | Status was null/NaN | R12 mapped `NAN` → `UNKNOWN` |
