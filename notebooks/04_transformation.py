"""
04_transformation.py - Run all 20 transformation rules.
This script will be auto-converted to a notebook.
"""
import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

# ═════════════════════════════════════════════════════════════
# SETUP
# ═════════════════════════════════════════════════════════════
MODE = 'dev'
CLEANED_PATH = f'../cleaned/{MODE}/raw_cems_data_cleaned.csv'
SENSOR_PATH  = f'../datasets/{MODE}/sensor_master.csv'
THRESH_PATH  = f'../datasets/{MODE}/regulatory_thresholds.csv'
METEO_PATH   = f'../datasets/{MODE}/transformation/meteorology_data.csv'
AQI_PATH     = f'../datasets/{MODE}/transformation/aqi_standards_cpcb.csv'
EF_PATH      = f'../datasets/{MODE}/transformation/emission_factors.csv'
CONTROL_PATH = f'../datasets/{MODE}/transformation/industry_control_measures.csv'
PENALTY_PATH = f'../datasets/{MODE}/transformation/compliance_penalty_rules.csv'
OUT_DIR      = f'../transformed/{MODE}'
os.makedirs(OUT_DIR, exist_ok=True)

df    = pd.read_csv(CLEANED_PATH)
sm    = pd.read_csv(SENSOR_PATH)
rt    = pd.read_csv(THRESH_PATH)
meteo = pd.read_csv(METEO_PATH)
aqi   = pd.read_csv(AQI_PATH)
ef    = pd.read_csv(EF_PATH)
ctrl  = pd.read_csv(CONTROL_PATH)
pen   = pd.read_csv(PENALTY_PATH)

print(f"Cleaned CEMS  : {df.shape}")
print(f"Sensor Master : {sm.shape}")
print(f"Thresholds    : {rt.shape}")
print(f"Meteorology   : {meteo.shape}")
print(f"AQI Standards : {aqi.shape}")
print(f"Emission Fact : {ef.shape}")
print(f"Controls      : {ctrl.shape}")
print(f"Penalties     : {pen.shape}")
print("All datasets loaded!")

# ═════════════════════════════════════════════════════════════
# DATA PREP
# ═════════════════════════════════════════════════════════════
df['TS'] = pd.to_datetime(df['TS'], errors='coerce')
for col in ['PM2.5', 'SO2', 'NOx']:
    df[col] = pd.to_numeric(df[col], errors='coerce')
df = df.merge(sm[['Plant_ID','Stack_ID','Sector']], on=['Plant_ID','Stack_ID'], how='left')
df = df.sort_values(['Plant_ID','Stack_ID','TS']).reset_index(drop=True)
print(f"Prepped: {df.shape}, Sector added")

# ═════════════════════════════════════════════════════════════
# T0: LAT/LON SPLIT
# ═════════════════════════════════════════════════════════════
print("\n── T0: Lat/Lon Split ──")
lat_lon_split = df['Lat_Lon'].str.split(',', expand=True)
df['Latitude']  = pd.to_numeric(lat_lon_split[0], errors='coerce')
df['Longitude'] = pd.to_numeric(lat_lon_split[1], errors='coerce')
df.drop(columns=['Lat_Lon'], inplace=True)
print(f"  Latitude range: {df['Latitude'].min():.4f} to {df['Latitude'].max():.4f}")
print(f"  Longitude range: {df['Longitude'].min():.4f} to {df['Longitude'].max():.4f}")

# ═════════════════════════════════════════════════════════════
# T1: EXCEEDANCE FLAGS
# ═════════════════════════════════════════════════════════════
print("\n── T1: Exceedance Flags ──")
thresh_dict = {}
for _, row in rt.iterrows():
    thresh_dict[(row['Pollutant'], row['Source_Type'])] = row['Legal_Limit_ugm3']

for pollutant in ['PM2.5', 'SO2', 'NOx']:
    col_name = f'Exceed_{pollutant.replace(".", "")}'
    df[col_name] = False
    for src in ['Stack', 'Ambient']:
        key = (pollutant, src)
        if key in thresh_dict:
            mask = df['Source_Type'] == src
            df.loc[mask, col_name] = df.loc[mask, pollutant] > thresh_dict[key]
    print(f"  {col_name}: {df[col_name].sum()} exceedances")

df['Any_Exceedance'] = df[['Exceed_PM25','Exceed_SO2','Exceed_NOx']].any(axis=1)
print(f"  Total exceedances: {df['Any_Exceedance'].sum()} ({df['Any_Exceedance'].mean()*100:.1f}%)")

# ═════════════════════════════════════════════════════════════
# T2: AQI COMPUTATION
# ═════════════════════════════════════════════════════════════
print("\n── T2: AQI Computation ──")
def calc_aqi_subindex(conc, pollutant, aqi_table):
    if pd.isna(conc) or conc < 0:
        return np.nan
    bp = aqi_table[aqi_table['Pollutant'] == pollutant].sort_values('Conc_Low')
    for _, row in bp.iterrows():
        if row['Conc_Low'] <= conc <= row['Conc_High']:
            return round(((row['AQI_High'] - row['AQI_Low']) / (row['Conc_High'] - row['Conc_Low'])) * (conc - row['Conc_Low']) + row['AQI_Low'], 1)
    if conc > bp['Conc_High'].max():
        return 500.0
    return np.nan

for pollutant in ['PM2.5', 'SO2', 'NOx']:
    col_name = f'AQI_{pollutant.replace(".", "")}'
    df[col_name] = df[pollutant].apply(lambda x: calc_aqi_subindex(x, pollutant, aqi))
    print(f"  {col_name}: mean={df[col_name].mean():.1f}")

df['AQI_Overall'] = df[['AQI_PM25','AQI_SO2','AQI_NOx']].max(axis=1)

def aqi_category(val):
    if pd.isna(val): return 'Unknown'
    if val <= 50:  return 'Good'
    if val <= 100: return 'Satisfactory'
    if val <= 200: return 'Moderate'
    if val <= 300: return 'Poor'
    if val <= 400: return 'Very Poor'
    return 'Severe'

df['AQI_Category'] = df['AQI_Overall'].apply(aqi_category)
print(f"  Category distribution: {dict(df['AQI_Category'].value_counts())}")

# ═════════════════════════════════════════════════════════════
# T3: EMISSION LOAD
# ═════════════════════════════════════════════════════════════
print("\n── T3: Emission Load (kg/day) ──")
stack_mask = df['Source_Type'] == 'Stack'
for pollutant in ['PM2.5', 'SO2', 'NOx']:
    col = f'Load_{pollutant.replace(".","")}_kg_day'
    df[col] = np.nan
    df.loc[stack_mask, col] = df.loc[stack_mask, pollutant] * df.loc[stack_mask, 'Flow_Rate_m3_hr'] * 24 / 1e9
    print(f"  {col}: mean={df.loc[stack_mask, col].mean():.4f}")

# ═════════════════════════════════════════════════════════════
# T4: ROLLING 24H AVERAGES
# ═════════════════════════════════════════════════════════════
print("\n── T4: Rolling 24h Averages ──")
for pollutant in ['PM2.5', 'SO2', 'NOx']:
    safe = pollutant.replace('.','')
    df[f'{safe}_24h_avg'] = df.groupby(['Plant_ID','Stack_ID'])[pollutant].transform(
        lambda x: x.rolling(window=96, min_periods=24).mean())
    df[f'{safe}_24h_p95'] = df.groupby(['Plant_ID','Stack_ID'])[pollutant].transform(
        lambda x: x.rolling(window=96, min_periods=24).quantile(0.95))
    print(f"  {safe}_24h_avg: mean={df[f'{safe}_24h_avg'].mean():.2f}")

# ═════════════════════════════════════════════════════════════
# T5 (placeholder): WIND CONTRIBUTION
# ═════════════════════════════════════════════════════════════
def bearing_between(lat1, lon1, lat2, lon2):
    d_lon = np.radians(lon2 - lon1)
    lat1r, lat2r = np.radians(lat1), np.radians(lat2)
    x = np.sin(d_lon) * np.cos(lat2r)
    y = np.cos(lat1r)*np.sin(lat2r) - np.sin(lat1r)*np.cos(lat2r)*np.cos(d_lon)
    return (np.degrees(np.arctan2(x, y)) + 360) % 360

df['Wind_Contribution_Score'] = 0.0

# ═════════════════════════════════════════════════════════════
# T6: COMPLIANCE RATE (Overall + Monthly)
# ═════════════════════════════════════════════════════════════
print("\n── T6: Compliance Rate ──")
stack_df = df[df['Source_Type'] == 'Stack'].copy()

# Overall compliance per plant
compliance = stack_df.groupby('Plant_ID').agg(
    Total_Readings=('Any_Exceedance', 'count'),
    Exceedances=('Any_Exceedance', 'sum')).reset_index()
compliance['Compliance_Rate_Pct'] = ((compliance['Total_Readings'] - compliance['Exceedances']) / compliance['Total_Readings'] * 100).round(2)
print("Overall:")
print(compliance.to_string(index=False))
compliance.to_csv(f'{OUT_DIR}/compliance_report.csv', index=False)

# Monthly compliance per plant
stack_df['Month'] = stack_df['TS'].dt.to_period('M').astype(str)
monthly = stack_df.groupby(['Plant_ID','Month']).agg(
    Total_Readings=('Any_Exceedance', 'count'),
    Exceedances=('Any_Exceedance', 'sum')).reset_index()
monthly['Compliance_Rate_Pct'] = ((monthly['Total_Readings'] - monthly['Exceedances']) / monthly['Total_Readings'] * 100).round(2)
print("\nMonthly:")
print(monthly.to_string(index=False))
monthly.to_csv(f'{OUT_DIR}/compliance_report_monthly.csv', index=False)

# ═════════════════════════════════════════════════════════════
# T7: EPISODE DETECTION
# ═════════════════════════════════════════════════════════════
print("\n── T7: Episode Detection ──")
episodes_list = []
for src_type in ['Stack', 'Ambient']:
    for pollutant in ['PM2.5', 'SO2', 'NOx']:
        key = (pollutant, src_type)
        if key not in thresh_dict: continue
        limit = thresh_dict[key]
        subset = df[df['Source_Type'] == src_type].copy()
        subset['above'] = subset[pollutant] > limit * 2
        for (pid, sid), grp in subset.groupby(['Plant_ID','Stack_ID']):
            grp = grp.sort_values('TS')
            grp['run_id'] = (grp['above'] != grp['above'].shift()).cumsum()
            for _, run in grp[grp['above']].groupby('run_id'):
                if len(run) >= 4:
                    episodes_list.append({
                        'Plant_ID': pid, 'Stack_ID': sid, 'Pollutant': pollutant,
                        'Episode_Start': run['TS'].min(), 'Episode_End': run['TS'].max(),
                        'Duration_Hours': len(run) * 0.25, 'Peak_Value': run[pollutant].max()})

episodes_df = pd.DataFrame(episodes_list)
print(f"  Found {len(episodes_df)} episodes")
episodes_df.to_csv(f'{OUT_DIR}/episodes.csv', index=False)

# ═════════════════════════════════════════════════════════════
# T8: SPATIAL GRID (IDW)
# ═════════════════════════════════════════════════════════════
print("\n── T8: Spatial Grid ──")
daily_avg = df.groupby(['Plant_ID','Latitude','Longitude']).agg(PM25_avg=('PM2.5','mean')).reset_index().dropna()
lat_r = [daily_avg['Latitude'].min()-0.05, daily_avg['Latitude'].max()+0.05]
lon_r = [daily_avg['Longitude'].min()-0.05, daily_avg['Longitude'].max()+0.05]
grid_rows = []
for lat in np.linspace(lat_r[0], lat_r[1], 10):
    for lon in np.linspace(lon_r[0], lon_r[1], 10):
        dists = np.sqrt((daily_avg['Latitude']-lat)**2 + (daily_avg['Longitude']-lon)**2).clip(lower=0.001)
        grid_rows.append({'Grid_Lat': round(lat,4), 'Grid_Lon': round(lon,4),
                          'PM25_IDW': round(np.average(daily_avg['PM25_avg'], weights=1/dists**2), 2)})
grid_df = pd.DataFrame(grid_rows)
grid_df.to_csv(f'{OUT_DIR}/spatial_grid.csv', index=False)
print(f"  Grid: {len(grid_df)} points")

# ═════════════════════════════════════════════════════════════
# T9: HEALTH RISK SCORE
# ═════════════════════════════════════════════════════════════
print("\n── T9: Health Risk Score ──")
df['Health_Risk_Score'] = df['AQI_PM25'] * 0.25
df['Date'] = df['TS'].dt.date
print(f"  Mean per-reading score: {df['Health_Risk_Score'].mean():.2f}")

# ═════════════════════════════════════════════════════════════
# T10: DIURNAL PROFILES
# ═════════════════════════════════════════════════════════════
print("\n── T10: Diurnal Profiles ──")
df['Hour'] = df['TS'].dt.hour
df['DayOfWeek'] = df['TS'].dt.day_name()
hourly_profile = df.groupby('Hour')[['PM2.5','SO2','NOx']].mean().round(2)
hourly_profile.to_csv(f'{OUT_DIR}/hourly_profile.csv')
print(hourly_profile.to_string())

# ═════════════════════════════════════════════════════════════
# T11: METEOROLOGY JOIN
# ═════════════════════════════════════════════════════════════
print("\n── T11: Meteorology Join ──")
plant_to_loc = {}
for pid in df['Plant_ID'].unique():
    pdata = df[(df['Plant_ID']==pid) & df['Latitude'].notna()]
    if len(pdata) == 0: continue
    lat = pdata['Latitude'].iloc[0]
    if lat > 25:    plant_to_loc[pid] = 'LOC-DEL-01'
    elif lat > 15:  plant_to_loc[pid] = 'LOC-MUM-01'
    else:           plant_to_loc[pid] = 'LOC-BLR-01'

df['TS_hour'] = df['TS'].dt.floor('h')
meteo['TS'] = pd.to_datetime(meteo['TS'])
df['Location_ID'] = df['Plant_ID'].map(plant_to_loc)
# Deduplicate meteo to prevent row multiplication during merge
meteo_dedup = meteo.drop_duplicates(subset=['Location_ID','TS'], keep='first')
pre_len = len(df)
df = df.merge(meteo_dedup[['Location_ID','TS','Wind_Speed_kmh','Wind_Dir_deg','Temp_C','Humidity_RH']],
              left_on=['Location_ID','TS_hour'], right_on=['Location_ID','TS'],
              how='left', suffixes=('', '_meteo'))
if 'TS_meteo' in df.columns: df.drop(columns=['TS_meteo'], inplace=True)
df.drop(columns=['TS_hour'], inplace=True)
post_len = len(df)
print(f"  Rows before merge: {pre_len}, after: {post_len} (should be equal)")
if post_len != pre_len:
    print(f"  WARNING: Merge created {post_len-pre_len} extra rows — deduplicating")
    df = df.drop_duplicates(subset=[c for c in df.columns if c not in ['Wind_Speed_kmh','Wind_Dir_deg','Temp_C','Humidity_RH']], keep='first')
    df = df.reset_index(drop=True)
    print(f"  After dedup: {len(df)} rows")
print(f"  Wind filled: {df['Wind_Speed_kmh'].notna().sum()} of {len(df)}")

# ═════════════════════════════════════════════════════════════
# T5 FINALIZED: WIND CONTRIBUTION
# ═════════════════════════════════════════════════════════════
print("\n── T5 Finalized: Wind Contribution ──")
ambient_mask = df['Source_Type'] == 'Ambient'
stack_locs = df[df['Source_Type']=='Stack'].groupby('Plant_ID')[['Latitude','Longitude']].first()

# Vectorized approach: for each stack, compute contribution to all ambient rows at once
ambient_idx = df[ambient_mask].index
scores = pd.Series(0.0, index=ambient_idx)

for spid, sloc in stack_locs.iterrows():
    amb = df.loc[ambient_idx]
    valid = amb['Wind_Dir_deg'].notna() & amb['Latitude'].notna()
    if valid.sum() == 0: continue
    v_idx = amb[valid].index
    bearings = amb.loc[v_idx].apply(
        lambda r: bearing_between(sloc['Latitude'], sloc['Longitude'], r['Latitude'], r['Longitude']), axis=1)
    diffs = (amb.loc[v_idx, 'Wind_Dir_deg'] - bearings).abs()
    diffs = diffs.where(diffs <= 180, 360 - diffs)
    contrib = (1.0 - diffs / 90.0).clip(lower=0)
    scores.loc[v_idx] = scores.loc[v_idx].combine(contrib, max)

df.loc[ambient_idx, 'Wind_Contribution_Score'] = scores.round(3).values
print(f"  Ambient scores: mean={df.loc[ambient_mask, 'Wind_Contribution_Score'].mean():.3f}")

# ═════════════════════════════════════════════════════════════
# T12: EMISSION FACTOR COMPARISON
# ═════════════════════════════════════════════════════════════
print("\n── T12: Emission Factor Comparison ──")
ef_results = []
for sector in df[df['Source_Type']=='Stack']['Sector'].dropna().unique():
    for pollutant in ['PM2.5', 'SO2', 'NOx']:
        load_col = f'Load_{pollutant.replace(".","")}_kg_day'
        ef_row = ef[(ef['Sector']==sector) & (ef['Pollutant']==pollutant)]
        if len(ef_row)==0: continue
        avg_load = df[(df['Sector']==sector)][load_col].mean()
        ef_results.append({'Sector':sector, 'Pollutant':pollutant,
                           'EF_kg_per_ton': ef_row.iloc[0]['Emission_Factor_kg_per_ton'],
                           'Avg_Measured_Load': round(avg_load,4) if not pd.isna(avg_load) else 0})
pd.DataFrame(ef_results).to_csv(f'{OUT_DIR}/emission_factor_comparison.csv', index=False)
print(f"  Saved emission factor comparison")

# ═════════════════════════════════════════════════════════════
# T13: DRIFT ALARMS (CUSUM)
# ═════════════════════════════════════════════════════════════
print("\n── T13: Drift Alarms ──")
drift_alarms = []
for (pid, sid), grp in df.groupby(['Plant_ID','Stack_ID']):
    if len(grp) < 48: continue
    for pollutant in ['PM2.5', 'SO2', 'NOx']:
        s = grp[pollutant].dropna()
        if len(s) < 48: continue
        rm = s.rolling(48, min_periods=24).mean()
        dev = s - rm
        cp = dev.clip(lower=0).cumsum()
        cn = (-dev).clip(lower=0).cumsum()
        th = s.std() * 2
        if th == 0: continue
        alarm_mask = (cp > th) | (cn > th)
        alarms = grp.loc[s.index[alarm_mask.values[:len(s)]], 'TS'] if alarm_mask.any() else pd.Series(dtype='datetime64[ns]')
        if len(alarms) > 0:
            drift_alarms.append({'Plant_ID':pid, 'Stack_ID':sid, 'Pollutant':pollutant,
                                 'Alarm_Count':len(alarms), 'Drift_Score':round(max(cp.max(),cn.max())/th,2)})
drift_df = pd.DataFrame(drift_alarms) if drift_alarms else pd.DataFrame(columns=['Plant_ID','Stack_ID','Pollutant','Alarm_Count','Drift_Score'])
drift_df.to_csv(f'{OUT_DIR}/drift_alarms.csv', index=False)
print(f"  Found {len(drift_df)} drift alarm groups")

# ═════════════════════════════════════════════════════════════
# T14: GAP ANALYSIS
# ═════════════════════════════════════════════════════════════
print("\n── T14: Gap Analysis ──")

# Count gap-filled rows (these have NaN Plant_ID from cleaning Rule R9)
total_gap_filled = (df['Status'] == 'GAP_FILLED').sum()
total_rows = len(df)
# Rows with actual sensor data (non-NaN Plant_ID)
real_rows = df['Plant_ID'].notna().sum()

print(f"  Total rows in dataset    : {total_rows}")
print(f"  Rows with real sensor ID : {real_rows}")
print(f"  Gap-filled (orphaned)    : {total_gap_filled}")

# Per-sensor breakdown (only real sensor rows)
real_df = df[df['Plant_ID'].notna()]
gap_analysis = real_df.groupby(['Plant_ID','Stack_ID']).agg(
    Original_Readings=('Status','count'),
    OK_Readings=('Status', lambda x: (x=='OK').sum()),
    Faults=('Status', lambda x: (x=='FAULT').sum()),
    Maint=('Status', lambda x: (x=='MAINT').sum()),
    Unknown=('Status', lambda x: (x=='UNKNOWN').sum()),
).reset_index()

# Calculate the time window and expected readings per sensor
ts_min, ts_max = real_df['TS'].min(), real_df['TS'].max()
time_span_hours = (ts_max - ts_min).total_seconds() / 3600
expected_per_sensor = int(time_span_hours / 0.25)  # one reading every 15 min
gap_analysis['Expected_Readings'] = expected_per_sensor
gap_analysis['Missing_Readings'] = expected_per_sensor - gap_analysis['Original_Readings']
gap_analysis['Data_Availability_Pct'] = (gap_analysis['Original_Readings'] / expected_per_sensor * 100).round(2)

print(f"\n  Time window: {ts_min} → {ts_max} ({time_span_hours:.0f} hours)")
print(f"  Expected readings per sensor: {expected_per_sensor}")
print(f"\n  Per-sensor breakdown:")
print(gap_analysis.to_string(index=False))

# Add a summary row for the orphaned gap-filled entries
summary_row = pd.DataFrame([{
    'Plant_ID': 'ORPHANED_GAPS', 'Stack_ID': '-',
    'Original_Readings': 0, 'OK_Readings': 0, 'Faults': 0,
    'Maint': 0, 'Unknown': 0,
    'Expected_Readings': total_gap_filled, 'Missing_Readings': total_gap_filled,
    'Data_Availability_Pct': 0.0
}])
gap_analysis_full = pd.concat([gap_analysis, summary_row], ignore_index=True)
gap_analysis_full.to_csv(f'{OUT_DIR}/gap_analysis.csv', index=False)
print(f"\n  Saved (including orphaned gap summary row)")

# ═════════════════════════════════════════════════════════════
# T15: REGULATORY REPORTS
# ═════════════════════════════════════════════════════════════
print("\n── T15: Regulatory Reports ──")
for src in ['Stack', 'Ambient']:
    sub = df[df['Source_Type']==src]
    if len(sub)==0: continue
    rpt = sub.groupby(['Plant_ID','Date']).agg(
        PM25_Avg=('PM2.5','mean'), SO2_Avg=('SO2','mean'), NOx_Avg=('NOx','mean'),
        Readings=('Record_ID','count'), Exceedances=('Any_Exceedance','sum'),
        AQI_Avg=('AQI_Overall','mean')).round(2).reset_index()
    rpt.to_csv(f'{OUT_DIR}/regulatory_report_{src.lower()}.csv', index=False)
    print(f"  {src}: {len(rpt)} rows")

# ═════════════════════════════════════════════════════════════
# T16: ML FEATURES
# ═════════════════════════════════════════════════════════════
print("\n── T16: ML Features ──")
feat = df[['Plant_ID','Stack_ID','TS','Source_Type','Sector','PM2.5','SO2','NOx','AQI_Overall','Hour','DayOfWeek']].copy()
for lag, lbl in [(1,'15m'),(4,'1h'),(24,'6h'),(96,'24h')]:
    feat[f'PM25_lag_{lbl}'] = feat.groupby(['Plant_ID','Stack_ID'])['PM2.5'].shift(lag)
feat['PM25_roll_mean_6h'] = feat.groupby(['Plant_ID','Stack_ID'])['PM2.5'].transform(lambda x: x.rolling(24,min_periods=6).mean())
feat['PM25_roll_std_6h'] = feat.groupby(['Plant_ID','Stack_ID'])['PM2.5'].transform(lambda x: x.rolling(24,min_periods=6).std())
feat['IsWeekend'] = feat['TS'].dt.dayofweek >= 5
feat['HourSin'] = np.sin(2*np.pi*feat['Hour']/24)
feat['HourCos'] = np.cos(2*np.pi*feat['Hour']/24)
if 'Wind_Speed_kmh' in df.columns:
    feat['Wind_Speed'] = df['Wind_Speed_kmh'].values
    feat['Temp_C'] = df['Temp_C'].values
feat.to_csv(f'{OUT_DIR}/model_features.csv', index=False)
print(f"  Features: {feat.shape}")

# ═════════════════════════════════════════════════════════════
# T17: HOTSPOT RANKING
# ═════════════════════════════════════════════════════════════
print("\n── T17: Hotspot Ranking ──")
daily_exc = df.groupby(['Plant_ID','Date']).agg(
    Exceeded=('Any_Exceedance','any'), PM25=('PM2.5','mean'),
    Lat=('Latitude','first'), Lon=('Longitude','first'), Src=('Source_Type','first')).reset_index()
hotspot = daily_exc.groupby('Plant_ID').agg(
    Days=('Date','nunique'), Exc_Days=('Exceeded','sum'), Avg_PM25=('PM25','mean'),
    Lat=('Lat','first'), Lon=('Lon','first'), Source=('Src','first')).reset_index()
hotspot['Persist_Pct'] = (hotspot['Exc_Days']/hotspot['Days']*100).round(1)
hotspot['Score'] = (hotspot['Persist_Pct']*hotspot['Avg_PM25']/100).round(2)
hotspot = hotspot.sort_values('Score', ascending=False)
hotspot['Rank'] = range(1, len(hotspot)+1)
print(hotspot.to_string(index=False))
hotspot.to_csv(f'{OUT_DIR}/hotspot_ranking.csv', index=False)

# ═════════════════════════════════════════════════════════════
# T18: CONTROL MEASURE IMPACT
# ═════════════════════════════════════════════════════════════
print("\n── T18: Control Measure Impact ──")
ctrl['Install_Date'] = pd.to_datetime(ctrl['Install_Date'])
impact_list = []
for _, m in ctrl.iterrows():
    pdata = df[(df['Plant_ID']==m['Plant_ID']) & (df['Stack_ID']==m['Stack_ID'])]
    if len(pdata)==0: continue
    pre = pdata[pdata['TS'] < m['Install_Date']]
    post = pdata[pdata['TS'] >= m['Install_Date']]
    for p in ['PM2.5','SO2','NOx']:
        pre_avg = pre[p].mean() if len(pre)>0 else np.nan
        post_avg = post[p].mean() if len(post)>0 else np.nan
        red = ((pre_avg-post_avg)/pre_avg*100) if (not pd.isna(pre_avg) and pre_avg>0) else np.nan
        impact_list.append({'Plant_ID':m['Plant_ID'],'Stack_ID':m['Stack_ID'],
                            'Measure':m['Measure_Type'],'Pollutant':p,
                            'Pre_Avg':round(pre_avg,2) if not pd.isna(pre_avg) else None,
                            'Post_Avg':round(post_avg,2) if not pd.isna(post_avg) else None,
                            'Reduction_Pct':round(red,1) if not pd.isna(red) else None})
impact_df = pd.DataFrame(impact_list)
print(impact_df.to_string(index=False))
impact_df.to_csv(f'{OUT_DIR}/control_impact.csv', index=False)

# ═════════════════════════════════════════════════════════════
# T19: PENALTY ESTIMATION
# ═════════════════════════════════════════════════════════════
print("\n── T19: Penalty Estimation ──")
penalty_list = []
for pid in df[df['Source_Type']=='Stack']['Plant_ID'].unique():
    plant = df[(df['Plant_ID']==pid) & (df['Source_Type']=='Stack')]
    for pollutant in ['PM2.5','SO2','NOx']:
        exc_col = f'Exceed_{pollutant.replace(".","")}'
        exceeded = plant[plant[exc_col]==True]
        if len(exceeded)==0: continue
        hrs = len(exceeded)*0.25
        key = (pollutant, 'Stack')
        if key not in thresh_dict: continue
        pct_over = (exceeded[pollutant].mean()-thresh_dict[key])/thresh_dict[key]*100
        pen_rules = pen[pen['Pollutant']==pollutant].sort_values('Threshold_Pct_Over', ascending=False)
        sev, rate = 'Minor', 0
        for _, r in pen_rules.iterrows():
            if pct_over >= r['Threshold_Pct_Over']:
                sev, rate = r['Severity'], r['Fine_INR_per_Hour']; break
        penalty_list.append({'Plant_ID':pid,'Pollutant':pollutant,'Hours':hrs,
                             'Pct_Over':round(pct_over,1),'Severity':sev,'Fine_INR':round(hrs*rate)})
penalty_df = pd.DataFrame(penalty_list)
if len(penalty_df)>0:
    penalty_df = penalty_df.sort_values('Fine_INR', ascending=False)
    print(penalty_df.to_string(index=False))
    print(f"  Total fines: INR {penalty_df['Fine_INR'].sum():,.0f}")
penalty_df.to_csv(f'{OUT_DIR}/penalty_estimate.csv', index=False)

# ═════════════════════════════════════════════════════════════
# T20: OPEN DATA EXTRACT
# ═════════════════════════════════════════════════════════════
print("\n── T20: Open Data Extract ──")
od = df.copy()
drop = [c for c in ['Audit_Hash','Record_ID','Location_ID'] if c in od.columns]
od.drop(columns=drop, inplace=True)
od['Latitude'] = od['Latitude'].round(2)
od['Longitude'] = od['Longitude'].round(2)
keep = [c for c in ['Plant_ID','Stack_ID','TS','Source_Type','Sector','PM2.5','SO2','NOx',
                     'Unit','Status','Latitude','Longitude','AQI_Overall','AQI_Category',
                     'Any_Exceedance','Hour','DayOfWeek'] if c in od.columns]
od = od[keep]
od.to_csv(f'{OUT_DIR}/open_data_extract.csv', index=False)
print(f"  Shape: {od.shape}")

# ═════════════════════════════════════════════════════════════
# SAVE MAIN ENRICHED DATASET
# ═════════════════════════════════════════════════════════════
df.to_csv(f'{OUT_DIR}/transformed_cems.csv', index=False)
print(f"\n{'='*60}")
print("TRANSFORMATION COMPLETE")
print(f"{'='*60}")
print(f"Main dataset: {df.shape} -> {OUT_DIR}/transformed_cems.csv")
print(f"Columns ({len(df.columns)}):")
for c in df.columns:
    print(f"  - {c}")
for f in sorted(os.listdir(OUT_DIR)):
    fp = os.path.join(OUT_DIR, f)
    print(f"  {f:45s} ({os.path.getsize(fp)/1024:.1f} KB)")
print("\nAll 20 transformation rules applied!")
