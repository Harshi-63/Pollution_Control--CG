# Pipeline Visualization Guide

This document describes all **9 inline visualizations** across the CEMS cleaning and transformation pipeline.

---

## Cleaning Notebook Graphs (5)

These graphs are embedded inline in `02_cleaning.ipynb` and `02_simple_cleaning.ipynb`. They render automatically when you "Run All".

### C1: Gap-Fill Analysis
**Position:** After R9b (metric gap-fill interpolation)  
**File:** `cleaned/{MODE}/graphs/gap_fill_analysis.png`

| Panel | Content |
|-------|---------|
| Left  | Grouped bar: Original Valid / R9b Interpolated / Still NaN per pollutant |
| Right | Donut chart: Total data completeness across all pollutants |

**Why it matters:** Shows exactly how many NaN values R9b successfully filled via linear interpolation vs how many remain unfillable (long gaps, fault periods).

---

### C2: Sensor Data Completeness
**Position:** After R9b  
**File:** `cleaned/{MODE}/graphs/sensor_completeness.png`

Stacked horizontal bar per plant showing status breakdown: **OK** (green), **FAULT** (red), **MAINT** (amber), **UNKNOWN** (grey).

**Why it matters:** Instantly identifies which sensors/plants have the most reliability issues — critical for prioritizing maintenance and understanding data gaps.

---

### C3: Pollutant Distributions
**Position:** Before save (final cleaned data)  
**File:** `cleaned/{MODE}/graphs/pollutant_distributions.png`

Three violin plots (PM2.5, SO2, NOx) showing the full distribution of cleaned values. Includes:
- CPCB regulatory limit line (dashed red)
- Stats box (n, mean, median, max)

**Why it matters:** Confirms the cleaned data has reasonable distributions — no extreme outliers, negative values, or suspicious patterns remaining.

---

### C4: Cleaning Rule Impact
**Position:** After save  
**File:** `cleaned/{MODE}/graphs/rule_impact.png`

Horizontal bar chart showing how many records each cleaning rule modified, sourced from the `cleaning_log.csv` audit trail. Uses viridis color gradient.

**Why it matters:** Justifies the cleaning pipeline — shows which rules had the most impact and where the most data quality issues existed.

---

### C5: Before vs After Missing Data
**Position:** After save  
**File:** `cleaned/{MODE}/graphs/before_after_nan.png`

Grouped bar comparing NaN + invalid values in raw data vs remaining NaN after cleaning, for each pollutant column.

**Why it matters:** The clearest proof that the cleaning pipeline improved data quality — shows the reduction in missing/invalid data.

---

## Transformation Graphs (4)

These graphs are embedded inline in `04_transformation.py` / `04_transformation.ipynb`. They generate during transformation execution.

### T-viz1: Exceedance Heatmap
**Position:** After T1 (Exceedance Flagging)  
**File:** `transformed/{MODE}/graphs/exceedance_heatmap.png`

Heatmap grid with Plants (rows) × Pollutants (columns). Cell values are exceedance counts, colored with YlOrRd colormap. Darker red = more exceedances.

**Why it matters:** Reveals patterns at a glance — does one plant fail on everything? Is PM2.5 universally worse than NOx? Are ambient stations different from stack sources?

---

### T-viz2: AQI Analysis
**Position:** After T2 (AQI Computation)  
**File:** `transformed/{MODE}/graphs/aqi_analysis.png`

| Panel | Content |
|-------|---------|
| Left  | Donut chart: AQI category distribution (Good/Satisfactory/Moderate/Poor/Very Poor/Severe) |
| Right | Box plot: AQI ranges by industry sector (City/Cement/Steel/Power) |

**Why it matters:** Instant overall air quality assessment. The donut shows the big picture (what % is "Good" vs "Severe"), and the sector comparison reveals whether certain industries pollute more.

---

### T-viz3: Compliance & Pollutant Trends
**Position:** After T6 (Compliance Rate)  
**File:** `transformed/{MODE}/graphs/compliance_trends.png`

| Panel | Content |
|-------|---------|
| Left  | Horizontal bars: Per-plant compliance rate for PM2.5/SO2/NOx with 90% target line |
| Right | Line chart: PM2.5 24h rolling average for top 3 worst plants with CPCB limit overlay |

**Why it matters:** The compliance bars identify which plants need enforcement action. The time series reveals temporal patterns — sustained violations vs occasional spikes.

---

### T-viz4: Gap-Fill Impact (Conditional)
**Position:** After T14 (Gap-Fill Comparison)  
**File:** `transformed/{MODE}/graphs/gap_fill_impact.png`

| Panel | Content |
|-------|---------|
| Left  | Grouped bar: Raw mean vs Filled mean per pollutant |
| Right | Bar chart: Number of values interpolated per pollutant with fill rate % |

**Why it matters:** Quantifies the impact of R9b interpolation on downstream analysis — shows whether gap-filling changed the statistical picture or left it essentially unchanged.

> **Note:** This graph only generates when the cleaned data contains R9b fill flag columns. If cleaning hasn't been re-run with R9b, it gracefully skips.

---

## Design System

All 9 graphs use a consistent **dark GitHub-inspired theme**:

| Element | Color |
|---------|-------|
| Background | `#0d1117` |
| Panel | `#161b22` |
| Borders | `#30363d` |
| Text | `#c9d1d9` |
| Blue accent | `#58A6FF` |
| Green accent | `#3FB950` |
| Red accent | `#F85149` |
| Amber accent | `#D29922` |

All graphs are saved at **150 DPI** for presentation quality.

## Output Locations

```
cleaned/{MODE}/graphs/
    gap_fill_analysis.png
    sensor_completeness.png
    pollutant_distributions.png
    rule_impact.png
    before_after_nan.png

transformed/{MODE}/graphs/
    exceedance_heatmap.png
    aqi_analysis.png
    compliance_trends.png
    gap_fill_impact.png          # conditional
```
