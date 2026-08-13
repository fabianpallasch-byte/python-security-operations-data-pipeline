from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"

files = {
    "incidents": "incidents_raw.csv",
    "findings": "findings_raw.csv",
    "awareness": "awareness_training_raw.csv",
    "patch": "patch_compliance_raw.csv",
    "departments": "department_master.csv",
}

dataframes = {}

for name, filename in files.items():
    file_path = RAW_DIR / filename
    df = pd.read_csv(file_path, sep=";")
    dataframes[name] = df

    print(f"\n--- {name.upper()} ---")
    print("Shape:", df.shape)
    print("\nColumns:")
    print(df.columns.tolist())
    print("\nMissing values:")
    print(df.isna().sum())
    print("\nDuplicate rows:", df.duplicated().sum())
    print("\nSample rows:")
    print(df.head(5))

from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

files = {
    "incidents": "incidents_raw.csv",
    "findings": "findings_raw.csv",
    "awareness": "awareness_training_raw.csv",
    "patch": "patch_compliance_raw.csv",
    "departments": "department_master.csv",
}

department_mapping = {
    "IT": "Information Technology",
    "Information Technology": "Information Technology",
    "Operations": "Operations",
    "Ops": "Operations",
    "Sales": "Sales",
    "Finance": "Finance",
    "HR": "HR",
    "Legal": "Legal",
    "Marketing": "Marketing",
    "Customer Support": "Customer Support"
}

dataframes = {}

for name, filename in files.items():
    file_path = RAW_DIR / filename
    df = pd.read_csv(file_path, sep=";")

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    if "department" in df.columns:
        df["department"] = df["department"].astype(str).str.strip().replace(department_mapping)

    if name == "departments":
        df["department_name"] = df["department_name"].astype(str).str.strip().replace(department_mapping)

    date_columns = [col for col in df.columns if "date" in col]
    for col in date_columns:
        df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)

    numeric_columns = [
        "response_hours", "emails_sent", "clicks", "failures",
        "completion_rate", "assets_total", "assets_compliant", "compliance_rate"
    ]
    for col in numeric_columns:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", ".", regex=False)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

    duplicates_before = df.duplicated().sum()
    df = df.drop_duplicates()

    print(f"\n--- {name.upper()} CLEANING SUMMARY ---")
    print("Shape after cleaning:", df.shape)
    print("Duplicates removed:", duplicates_before)
    print("Missing values after type conversion:")
    print(df.isna().sum())

    output_path = PROCESSED_DIR / f"{name}_clean.csv"
    df.to_csv(output_path, index=False)

    dataframes[name] = df

REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

quality_rows = []
detail_frames = []

def add_issue(dataset, rule_name, mask, df, detail_cols, description):
    mask = mask.fillna(False)
    affected = int(mask.sum())

    quality_rows.append({
        "dataset": dataset,
        "rule_name": rule_name,
        "affected_rows": affected,
        "description": description
    })

    if affected > 0:
        detail_cols = [col for col in detail_cols if col in df.columns]
        issue_df = df.loc[mask, detail_cols].copy()
        issue_df.insert(0, "dataset", dataset)
        issue_df.insert(1, "rule_name", rule_name)
        detail_frames.append(issue_df)

inc = dataframes["incidents"].copy()
inc_status = inc["status"].astype(str).str.strip().str.lower()

add_issue(
    "incidents",
    "resolved_date_before_created_date",
    inc["resolved_date"].notna() & inc["created_date"].notna() & (inc["resolved_date"] < inc["created_date"]),
    inc,
    ["incident_id", "department", "status", "created_date", "resolved_date", "response_hours"],
    "resolved_date is earlier than created_date"
)

add_issue(
    "incidents",
    "resolved_status_missing_resolved_date",
    inc_status.eq("resolved") & inc["resolved_date"].isna(),
    inc,
    ["incident_id", "department", "status", "created_date", "resolved_date"],
    "status is resolved but resolved_date is missing"
)

add_issue(
    "incidents",
    "open_status_with_resolved_date",
    inc_status.isin(["open", "in progress"]) & inc["resolved_date"].notna(),
    inc,
    ["incident_id", "department", "status", "created_date", "resolved_date"],
    "status is open/in progress but resolved_date is filled"
)

add_issue(
    "incidents",
    "negative_response_hours",
    inc["response_hours"].notna() & (inc["response_hours"] < 0),
    inc,
    ["incident_id", "department", "response_hours"],
    "response_hours is negative"
)

find = dataframes["findings"].copy()
find_status = find["status"].astype(str).str.strip().str.lower()

add_issue(
    "findings",
    "close_date_before_open_date",
    find["close_date"].notna() & find["open_date"].notna() & (find["close_date"] < find["open_date"]),
    find,
    ["finding_id", "department", "status", "open_date", "close_date", "owner_team"],
    "close_date is earlier than open_date"
)

add_issue(
    "findings",
    "closed_status_missing_close_date",
    find_status.eq("closed") & find["close_date"].isna(),
    find,
    ["finding_id", "department", "status", "open_date", "close_date"],
    "status is closed but close_date is missing"
)

add_issue(
    "findings",
    "open_status_with_close_date",
    find_status.eq("open") & find["close_date"].notna(),
    find,
    ["finding_id", "department", "status", "open_date", "close_date"],
    "status is open but close_date is filled"
)

add_issue(
    "findings",
    "missing_owner_team",
    find["owner_team"].isna(),
    find,
    ["finding_id", "department", "severity", "owner_team"],
    "owner_team is missing"
)

aware = dataframes["awareness"].copy()

add_issue(
    "awareness",
    "clicks_greater_than_emails_sent",
    aware["clicks"] > aware["emails_sent"],
    aware,
    ["department", "campaign_date", "emails_sent", "clicks"],
    "clicks is greater than emails_sent"
)

add_issue(
    "awareness",
    "failures_greater_than_emails_sent",
    aware["failures"] > aware["emails_sent"],
    aware,
    ["department", "campaign_date", "emails_sent", "failures"],
    "failures is greater than emails_sent"
)

add_issue(
    "awareness",
    "completion_rate_out_of_range",
    aware["completion_rate"].notna() & ((aware["completion_rate"] < 0) | (aware["completion_rate"] > 1)),
    aware,
    ["department", "campaign_date", "completion_rate"],
    "completion_rate is outside 0 to 1"
)

patch = dataframes["patch"].copy()

add_issue(
    "patch",
    "assets_compliant_greater_than_assets_total",
    patch["assets_compliant"] > patch["assets_total"],
    patch,
    ["department", "scan_date", "assets_total", "assets_compliant"],
    "assets_compliant is greater than assets_total"
)

add_issue(
    "patch",
    "compliance_rate_out_of_range",
    patch["compliance_rate"].notna() & ((patch["compliance_rate"] < 0) | (patch["compliance_rate"] > 1)),
    patch,
    ["department", "scan_date", "compliance_rate"],
    "compliance_rate is outside 0 to 1"
)

add_issue(
    "patch",
    "missing_compliance_rate",
    patch["compliance_rate"].isna(),
    patch,
    ["department", "scan_date", "compliance_rate"],
    "compliance_rate is missing"
)

valid_departments = set(
    dataframes["departments"]["department_name"]
    .dropna()
    .astype(str)
    .str.strip()
)

for dataset_name, id_cols in {
    "incidents": ["incident_id", "department", "created_date"],
    "findings": ["finding_id", "department", "open_date"],
    "awareness": ["department", "campaign_date"],
    "patch": ["department", "scan_date"]
}.items():
    df = dataframes[dataset_name].copy()

    add_issue(
        dataset_name,
        "department_not_in_master",
        ~df["department"].isin(valid_departments),
        df,
        id_cols,
        "department is not found in department master"
    )

quality_report = pd.DataFrame(quality_rows).sort_values(
    by=["dataset", "affected_rows", "rule_name"],
    ascending=[True, False, True]
)

quality_report.to_csv(REPORTS_DIR / "data_quality_report.csv", index=False)

if detail_frames:
    detail_report = pd.concat(detail_frames, ignore_index=True)
else:
    detail_report = pd.DataFrame(columns=["dataset", "rule_name"])

detail_report.to_csv(REPORTS_DIR / "data_quality_issue_details.csv", index=False)

print("\n--- DATA QUALITY REPORT ---")
print(quality_report.to_string(index=False))
print("\nReports saved to:")
print(REPORTS_DIR / "data_quality_report.csv")
print(REPORTS_DIR / "data_quality_issue_details.csv")

from pandas.api.types import is_datetime64_any_dtype as is_datetime

def add_quarter_columns(df, date_col, prefix=""):
    if date_col in df.columns and is_datetime(df[date_col]):
        quarter = df[date_col].dt.to_period("Q").astype(str)
        if prefix:
            df[f"{prefix}_quarter"] = quarter
        else:
            df["quarter"] = quarter
    return df

inc = dataframes["incidents"].copy()
inc = add_quarter_columns(inc, "created_date")
inc["resolution_days"] = (inc["resolved_date"] - inc["created_date"]).dt.days
inc["is_critical"] = inc["severity"].astype(str).str.strip().str.lower().eq("critical")
inc["is_open"] = inc["status"].astype(str).str.strip().str.lower().isin(["open", "in progress"])
inc["sla_breach_flag"] = inc["response_hours"].notna() & (inc["response_hours"] > 24)

find = dataframes["findings"].copy()
find = add_quarter_columns(find, "open_date")
find["finding_age_days"] = (find["close_date"].fillna(pd.Timestamp.today().normalize()) - find["open_date"]).dt.days
find["is_critical"] = find["severity"].astype(str).str.strip().str.lower().eq("critical")
find["is_open"] = find["status"].astype(str).str.strip().str.lower().eq("open")
find["risk_flag"] = find["severity"].astype(str).str.strip().str.lower().isin(["high", "critical"])

aware = dataframes["awareness"].copy()
aware = add_quarter_columns(aware, "campaign_date")
aware["fail_rate"] = aware["failures"] / aware["emails_sent"]
aware["click_rate"] = aware["clicks"] / aware["emails_sent"]
aware["high_fail_rate_flag"] = aware["fail_rate"].notna() & (aware["fail_rate"] > 0.15)

patch = dataframes["patch"].copy()
patch = add_quarter_columns(patch, "scan_date")
patch["calculated_compliance_rate"] = patch["assets_compliant"] / patch["assets_total"]
patch["compliance_gap"] = 1 - patch["calculated_compliance_rate"]
patch["low_compliance_flag"] = patch["calculated_compliance_rate"].notna() & (patch["calculated_compliance_rate"] < 0.90)

departments = dataframes["departments"].copy()
departments_unique = (
    departments
    .sort_values("department_key")
    .drop_duplicates(subset=["department_name"], keep="first")
)

inc_enriched = inc.merge(
    departments_unique,
    left_on="department",
    right_on="department_name",
    how="left",
    validate="many_to_one"
)

find_enriched = find.merge(
    departments_unique,
    left_on="department",
    right_on="department_name",
    how="left",
    validate="many_to_one"
)

aware_enriched = aware.merge(
    departments_unique,
    left_on="department",
    right_on="department_name",
    how="left",
    validate="many_to_one"
)

patch_enriched = patch.merge(
    departments_unique,
    left_on="department",
    right_on="department_name",
    how="left",
    validate="many_to_one"
)

inc_enriched.to_csv(PROCESSED_DIR / "incidents_enriched.csv", index=False)
find_enriched.to_csv(PROCESSED_DIR / "findings_enriched.csv", index=False)
aware_enriched.to_csv(PROCESSED_DIR / "awareness_enriched.csv", index=False)
patch_enriched.to_csv(PROCESSED_DIR / "patch_enriched.csv", index=False)

print("\n--- FEATURE ENGINEERING SUMMARY ---")
print("incidents_enriched:", inc_enriched.shape)
print("findings_enriched:", find_enriched.shape)
print("awareness_enriched:", aware_enriched.shape)
print("patch_enriched:", patch_enriched.shape)
print("\nNew enriched files saved to:")
print(PROCESSED_DIR / "incidents_enriched.csv")
print(PROCESSED_DIR / "findings_enriched.csv")
print(PROCESSED_DIR / "awareness_enriched.csv")
print(PROCESSED_DIR / "patch_enriched.csv")

import sqlite3

DATABASE_DIR = BASE_DIR / "database"
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

db_path = DATABASE_DIR / "security_operations.db"
conn = sqlite3.connect(db_path)

inc_enriched.to_sql("incidents_clean", conn, if_exists="replace", index=False)
find_enriched.to_sql("findings_clean", conn, if_exists="replace", index=False)
aware_enriched.to_sql("awareness_clean", conn, if_exists="replace", index=False)
patch_enriched.to_sql("patch_clean", conn, if_exists="replace", index=False)
departments_unique.to_sql("department_dim", conn, if_exists="replace", index=False)
quality_report.to_sql("data_quality_summary", conn, if_exists="replace", index=False)
detail_report.to_sql("data_quality_details", conn, if_exists="replace", index=False)

kpi_open_incidents = pd.read_sql("""
SELECT
    department,
    business_unit,
    quarter,
    COUNT(*) AS open_incidents
FROM incidents_clean
WHERE is_open = 1
GROUP BY department, business_unit, quarter
""", conn)

kpi_findings = pd.read_sql("""
SELECT
    department,
    business_unit,
    quarter,
    SUM(CASE WHEN is_critical = 1 AND is_open = 1 THEN 1 ELSE 0 END) AS open_critical_findings,
    SUM(CASE WHEN risk_flag = 1 THEN 1 ELSE 0 END) AS high_risk_findings
FROM findings_clean
GROUP BY department, business_unit, quarter
""", conn)

kpi_awareness = pd.read_sql("""
SELECT
    department,
    business_unit,
    quarter,
    ROUND(AVG(fail_rate), 4) AS avg_fail_rate,
    ROUND(AVG(click_rate), 4) AS avg_click_rate,
    ROUND(AVG(completion_rate), 4) AS avg_completion_rate
FROM awareness_clean
GROUP BY department, business_unit, quarter
""", conn)

kpi_patch = pd.read_sql("""
SELECT
    department,
    business_unit,
    quarter,
    ROUND(AVG(calculated_compliance_rate), 4) AS avg_compliance_rate,
    ROUND(AVG(compliance_gap), 4) AS avg_compliance_gap
FROM patch_clean
GROUP BY department, business_unit, quarter
""", conn)

kpi_resolution = pd.read_sql("""
SELECT
    department,
    business_unit,
    quarter,
    ROUND(AVG(resolution_days), 2) AS avg_resolution_days
FROM incidents_clean
WHERE resolution_days IS NOT NULL
GROUP BY department, business_unit, quarter
""", conn)

kpi_summary = (
    kpi_open_incidents
    .merge(kpi_findings, on=["department", "business_unit", "quarter"], how="outer")
    .merge(kpi_awareness, on=["department", "business_unit", "quarter"], how="outer")
    .merge(kpi_patch, on=["department", "business_unit", "quarter"], how="outer")
    .merge(kpi_resolution, on=["department", "business_unit", "quarter"], how="outer")
    .sort_values(["business_unit", "department", "quarter"])
)

kpi_summary.to_sql("kpi_summary", conn, if_exists="replace", index=False)
kpi_summary.to_csv(REPORTS_DIR / "clean_kpi_dataset.csv", index=False)

print("\n--- SQLITE LOAD SUMMARY ---")
print("Database saved to:", db_path)
print("kpi_summary shape:", kpi_summary.shape)
print("KPI dataset saved to:", REPORTS_DIR / "clean_kpi_dataset.csv")

conn.close()