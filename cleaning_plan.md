


Let's officially decide on **10 Sensors** reporting every **15 minutes**. 
*(Math: 10 sensors × 4 times/hour × 24 hours × 30 days = **~28,800 rows per month**).* 

Here is the absolute, detailed, column-by-column breakdown of the **5 Cleaning Datasets**, including the exact percentages of how "messy" the raw data will be to trigger your rules!

---

### 1. `raw_cems_data.csv` (The Core Input Stream)
*   **Total Rows:** ~28,800 rows (Dynamic, grows continuously).
*   **What it is:** The raw, unfiltered 15-minute data stream from all 10 sensors.

**Columns & Expected Values:**
*   `Record_ID`: String (e.g., `E00001` to `E28800`). Unique for every row.
*   `Plant_ID`: String. (e.g., `PL-01`, `LOC-DEL-01`).
*   `Stack_ID`: String. (e.g., `S-01`, `A-01`).
*   `Flow_Rate_m3_hr`: Float. Normally `1000.0` to `5000.0` (Will be `0` or `Null` for Ambient sensors since city air isn't pushed through a chimney).
*   **`TS` (Timestamp) - *The Messy Distribution:***
    *   **90% Perfect:** `14-03-2026 12:15`
    *   **5% Edge Case (Rule 1):** Ends in `24:10` or `24:15` (needs midnight rollover).
    *   **5% Edge Case (Rule 17):** Has timezones attached like `14-03-2026 06:45 UTC` (needs IST conversion).
*   **`PM2.5`, `SO2`, `NOx` - *The Messy Distribution:***
    *   **85% Perfect:** Normal Floats (`15.5` up to `400.0`).
    *   **5% Edge Case (Rule 5):** Impossible Negatives (`-5.0`, `-12.4`).
    *   **5% Edge Case (Rule 11):** Strings representing Below Limit of Detection (`"<2.0"`, `"BDL"`).
    *   **3% Edge Case (Rule 8):** Massive physical spikes (`9999.0`, `8500.0`) that need Hampel filtering.
    *   **2% Edge Case (Rule 9):** Gaps! (The row just doesn't exist, and the pipeline must create it and forward-fill the data).
*   **`Unit` - *The Messy Distribution:***
    *   **80% Perfect:** `ug/m3`
    *   **10% Edge Case (Rule 2):** Unicode errors `µg/m³`.
    *   **10% Edge Case (Rule 14):** `mg/Nm3` (Requires pipeline to multiply the pollution value by 1000).
*   **`Status` - *The Messy Distribution:***
    *   **70% Perfect:** `OK`, `FAULT`, `MAINT`.
    *   **30% Edge Case (Rule 3 & 12):** Untrimmed/weird text like `" ok "`, `"offline"`, `"down"`, `"Error 404"`.
*   **`Lat_Lon` - *The Messy Distribution:***
    *   **98% Perfect:** Valid strings (`13.0827,80.2707`).
    *   **2% Edge Case (Rule 4):** Impossible coordinates (`13.08, -999.0` or `13.08;80.27`).

---

### 2. `sensor_master.csv` (Hardware Specs & Metadata)
*   **Total Rows:** **Exactly 10 Rows.** (Because we have exactly 10 physical sensors).
*   **What it is:** The "Absolute Truth" table. Used to calibrate sensors, identify limits, and tag sources (Rule 7, 11, 13, 15).

**The Exact 10 Rows for your Project:**

| Plant_ID | Stack_ID | Source_Type | Sector | Zero_Drift | Span_Mult | LOD_PM25 | LOD_SO2 | LOD_NOx |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `PL-01` | `S-01` | **Stack** | Cement | 0.5 | 1.02 | 2.0 | 4.0 | 5.0 |
| `PL-01` | `S-02` | **Stack** | Cement | 0.2 | 0.98 | 2.0 | 4.0 | 5.0 |
| `PL-02` | `S-01` | **Stack** | Steel | -0.5 | 1.05 | 2.0 | 5.0 | 5.0 |
| `PL-03` | `S-01` | **Stack** | Power | 0.8 | 1.10 | 5.0 | 5.0 | 5.0 |
| `PL-03` | `S-02` | **Stack** | Power | 0.1 | 1.00 | 5.0 | 5.0 | 5.0 |
| `PL-03` | `S-03` | **Stack** | Power | 0.0 | 1.01 | 5.0 | 5.0 | 5.0 |
| `LOC-DEL-01`| `A-01` | **Ambient** | City | 0.1 | 1.00 | 1.0 | 2.0 | 2.0 |
| `LOC-DEL-02`| `A-02` | **Ambient** | City | 0.0 | 0.99 | 1.0 | 2.0 | 2.0 |
| `LOC-MUM-01`| `A-01` | **Ambient** | City | -0.1 | 1.02 | 1.0 | 2.0 | 2.0 |
| `LOC-BLR-01`| `A-01` | **Ambient** | City | 0.2 | 1.00 | 1.0 | 2.0 | 2.0 |

---

### 3. `maintenance_logs.csv` (Mechanic Logs)
*   **Total Rows:** ~30 Rows per month (Dynamic).
*   **What it is:** Used for **Rule 10**. If an IoT sensor sends data, but this table shows a mechanic was working on it at that exact time, the pipeline deletes the raw data and forces the status to `MAINT`.

**Columns & Expected Values:**
*   `Plant_ID` & `Stack_ID`: Strings mapping back to `sensor_master`.
*   `Maint_Start` & `Maint_End`: Datetime strings (e.g., `14-03-2026 10:00` to `14-03-2026 13:00`).
*   `Technician`: String names (`"Ravi Kumar"`, `"Team B"`).

---

### 4. `manual_entries.csv` (Lab & Inspections)
*   **Total Rows:** ~50 Rows per month (Dynamic).
*   **What it is:** Human-typed data. Highly prone to typos and privacy leaks.

**Columns & Expected Values (The Messy Distribution):**
*   `Log_ID`, `Plant_ID`: Strings.
*   **`Lab_PM25_Entry1` & `Lab_PM25_Entry2` (Rule 16 QC):**
    *   **90% Perfect:** Floats match perfectly or within 1% (e.g., `45.0` and `45.0`).
    *   **10% Edge Case:** Human typing error (e.g., `45.0` vs `450.0`). The pipeline halts this row and flags "QC_FAIL".
*   **`Inspection_Notes` (Rule 18 PII Removal):**
    *   **80% Perfect:** `"Checked laser. System operational."`
    *   **20% Edge Case:** Contains personal data! `"System broken. Call Amit at 9876543210 or amit@email.com."` (Pipeline uses regex to replace these with `[REDACTED]`).

---

### 5. `regulatory_thresholds.csv` (Legal Limits)
*   **Total Rows:** **Exactly 6 Rows.**
*   **What it is:** The government rulebook for **Rule 19**. Limits change based on if you are breathing city air (`Ambient`) or standing inside a chimney (`Stack`).

**The Exact 6 Rows for your Project:**

| Pollutant | Source_Type | Legal_Limit_ugm3 |
| :--- | :--- | :--- |
| `PM2.5` | Ambient | 60.0 |
| `PM2.5` | Stack | 150.0 |
| `SO2` | Ambient | 80.0 |
| `SO2` | Stack | 200.0 |
| `NOx` | Ambient | 80.0 |
| `NOx` | Stack | 400.0 |

*(Notice how Stacks are allowed much higher limits? That's why Rule 15 tagging is so important before Rule 19!)*

---

### How to use this for your HTML Board
This gives you everything you need to build your visual map. 
*   You have the **Volume/Scale** (`28,800 rows` vs `10 rows`).
*   You have the **Exact Column Names**.
*   You have the **"Messy Percentage"** logic to explain exactly *why* Data Engineers are needed in the first place!
