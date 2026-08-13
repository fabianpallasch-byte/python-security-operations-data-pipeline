-- ============================================================
-- Security & Operations KPI Queries
-- Database: database/security_operations.db
-- Purpose: Management-oriented analysis of prepared security
--          and operations data after Python ETL processing.
-- ============================================================


-- 1. KPI overview by department and quarter
-- Combines incident, finding, awareness, patch compliance
-- and resolution-time indicators in one management view.

SELECT
    department,
    business_unit,
    quarter,
    open_incidents,
    open_critical_findings,
    high_risk_findings,
    avg_fail_rate,
    avg_click_rate,
    avg_completion_rate,
    avg_compliance_rate,
    avg_compliance_gap,
    avg_resolution_days
FROM kpi_summary
ORDER BY business_unit, department, quarter;

-- 2. Open critical and high-risk findings
-- Highlights departments and quarters with elevated unresolved
-- security risk exposure.

SELECT
    department,
    business_unit,
    quarter,
    open_critical_findings,
    high_risk_findings
FROM kpi_summary
WHERE open_critical_findings > 0
   OR high_risk_findings > 0
ORDER BY
    open_critical_findings DESC,
    high_risk_findings DESC,
    department,
    quarter;


-- 3. Incident SLA breaches and resolution performance
-- Measures incident volume, SLA breaches and average resolution
-- duration by department and quarter.

SELECT
    department,
    business_unit,
    quarter,
    COUNT(*) AS total_incidents,
    SUM(CASE WHEN sla_breach_flag = 1 THEN 1 ELSE 0 END) AS sla_breaches,
    ROUND(
        100.0 * SUM(CASE WHEN sla_breach_flag = 1 THEN 1 ELSE 0 END)
        / COUNT(*),
        1
    ) AS sla_breach_rate_pct,
    ROUND(AVG(resolution_days), 2) AS avg_resolution_days
FROM incidents_clean
GROUP BY
    department,
    business_unit,
    quarter
ORDER BY
    sla_breach_rate_pct DESC,
    avg_resolution_days DESC,
    total_incidents DESC;


-- 4. Awareness training risk by department
-- Identifies departments with elevated failure and click rates
-- in security-awareness campaigns.

SELECT
    department,
    business_unit,
    quarter,
    SUM(emails_sent) AS emails_sent,
    SUM(clicks) AS clicks,
    SUM(failures) AS failures,
    ROUND(100.0 * SUM(failures) / SUM(emails_sent), 1) AS fail_rate_pct,
    ROUND(100.0 * SUM(clicks) / SUM(emails_sent), 1) AS click_rate_pct,
    ROUND(100.0 * AVG(completion_rate), 1) AS avg_completion_rate_pct
FROM awareness_clean
GROUP BY
    department,
    business_unit,
    quarter
ORDER BY
    fail_rate_pct DESC,
    click_rate_pct DESC,
    department,
    quarter;


-- 5. Patch compliance risk by department
-- Identifies departments with low patch compliance and the
-- largest number of non-compliant assets.

SELECT
    department,
    business_unit,
    quarter,
    SUM(assets_total) AS assets_total,
    SUM(assets_compliant) AS assets_compliant,
    SUM(assets_total - assets_compliant) AS non_compliant_assets,
    ROUND(
        100.0 * SUM(assets_compliant) / SUM(assets_total),
        1
    ) AS calculated_compliance_rate_pct
FROM patch_clean
GROUP BY
    department,
    business_unit,
    quarter
ORDER BY
    calculated_compliance_rate_pct ASC,
    non_compliant_assets DESC,
    department,
    quarter;


-- 6. Data quality issue summary
-- Summarises the business-rule validation results generated
-- during the Python ETL process.

SELECT
    dataset,
    rule_name,
    affected_rows,
    description
FROM data_quality_summary
WHERE affected_rows > 0
ORDER BY
    dataset,
    affected_rows DESC,
    rule_name;


-- 7. Combined risk prioritisation
-- Ranks department-quarter combinations using critical findings,
-- SLA breaches, awareness failure rate and patch compliance.

SELECT
    department,
    business_unit,
    quarter,
    open_critical_findings,
    high_risk_findings,
    open_incidents,
    ROUND(avg_fail_rate * 100, 1) AS fail_rate_pct,
    ROUND(avg_compliance_rate * 100, 1) AS compliance_rate_pct,
    ROUND(avg_resolution_days, 2) AS avg_resolution_days,
    (
        COALESCE(open_critical_findings, 0) * 4
        + COALESCE(high_risk_findings, 0) * 2
        + CASE WHEN COALESCE(avg_fail_rate, 0) >= 0.15 THEN 2 ELSE 0 END
        + CASE WHEN COALESCE(avg_compliance_rate, 1) < 0.85 THEN 2 ELSE 0 END
        + CASE WHEN COALESCE(open_incidents, 0) > 0 THEN 1 ELSE 0 END
    ) AS risk_priority_score
FROM kpi_summary
ORDER BY
    risk_priority_score DESC,
    open_critical_findings DESC,
    high_risk_findings DESC,
    department,
    quarter;


-- 8. Business unit management summary
-- Provides a compact summary of security and operations KPIs
-- by business unit across all available quarters.

SELECT
    business_unit,
    SUM(COALESCE(open_incidents, 0)) AS open_incidents,
    SUM(COALESCE(open_critical_findings, 0)) AS open_critical_findings,
    SUM(COALESCE(high_risk_findings, 0)) AS high_risk_findings,
    ROUND(AVG(avg_fail_rate) * 100, 1) AS avg_awareness_fail_rate_pct,
    ROUND(AVG(avg_compliance_rate) * 100, 1) AS avg_patch_compliance_rate_pct,
    ROUND(AVG(avg_resolution_days), 2) AS avg_resolution_days,
    MAX(risk_priority_score) AS highest_risk_priority_score
FROM (
    SELECT
        department,
        business_unit,
        quarter,
        open_incidents,
        open_critical_findings,
        high_risk_findings,
        avg_fail_rate,
        avg_compliance_rate,
        avg_resolution_days,
        (
            COALESCE(open_critical_findings, 0) * 4
            + COALESCE(high_risk_findings, 0) * 2
            + CASE WHEN COALESCE(avg_fail_rate, 0) >= 0.15 THEN 2 ELSE 0 END
            + CASE WHEN COALESCE(avg_compliance_rate, 1) < 0.85 THEN 2 ELSE 0 END
            + CASE WHEN COALESCE(open_incidents, 0) > 0 THEN 1 ELSE 0 END
        ) AS risk_priority_score
    FROM kpi_summary
)
GROUP BY business_unit
ORDER BY
    highest_risk_priority_score DESC,
    open_critical_findings DESC,
    high_risk_findings DESC;