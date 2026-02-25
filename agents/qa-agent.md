# QA Agent

> Role: Verify data integrity and analysis quality before report generation

## Prerequisites
- Phase 2 and Phase 3 completed
- All analysis outputs exist in `output/`

## Input Files
- `output/normalized.parquet` - Raw normalized data
- `output/parsed.parquet` - Parsed data
- `output/creative_tier.parquet` - Creative TIER data
- `output/hook_type_comparison.parquet` - Hook comparison
- `output/age_analysis.parquet` - Age analysis
- `output/anomalies.csv` - Anomaly detection results

## Execution
```bash
python skills/qa/scripts/validate_analysis.py output output/YYYYMMDD
```

## Output Files
- `output/YYYYMMDD/qa_report.json` - QA verification results

## Completion Flag
- `output/qa_done.flag` - Created only when all_pass = true

## Failure Handling
- Log errors to `logs/qa_error.log`
- Generate qa_report.json even on failure (with all_pass = false)
- Phase 5 (report generation) BLOCKED if all_pass = false

## QA Report JSON Structure
```json
{
  "timestamp": "YYYY-MM-DD HH:MM",
  "all_pass": true/false,
  "checks": {
    "data_integrity": {
      "daily_conv_match": bool,
      "branch_conv_match": bool,
      "creative_conv_match": bool,
      "raw_total_conv": number,
      "analysis_total_conv": number,
      "raw_total_cost": number,
      "analysis_total_cost": number,
      "cost_match": bool,
      "conv_match": bool
    },
    "tier_quality": {
      "no_under7days_in_tier": bool,
      "no_low_volume_in_tier": bool,
      "tier3_not_zero_check": bool,
      "tier_counts": {
        "TIER1": number,
        "TIER2": number,
        "TIER3": number,
        "TIER4": number,
        "LOW_VOLUME": number,
        "UNCLASSIFIED": number
      }
    },
    "calculation": {
      "cpa_verified": bool,
      "cvr_verified": bool,
      "ctr_verified": bool,
      "sample_verification": {
        "creative_name": string,
        "expected_cpa": number,
        "actual_cpa": number,
        "match": bool
      }
    },
    "hook": {
      "has_strict_or_type_comparison": bool,
      "strict_pairs_count": number,
      "type_comparison_count": number,
      "unmatched_list_exists": bool,
      "unmatched_count": number
    },
    "off_creative": {
      "parsed_correctly": bool,
      "separated_from_tier": bool,
      "off_creative_count": number,
      "sheet_exists": bool
    },
    "output": {
      "excel_7_sheets": bool,
      "pdf_exists": bool,
      "sheets_found": [list of sheet names]
    },
    "charts": {
      "bubble_data_points_match_tier": bool,
      "heatmap_not_empty": bool
    }
  },
  "failures": ["List of failed check descriptions"],
  "warnings": ["List of warnings (non-blocking)"]
}
```

## Verification Checks

### Data Integrity
1. **Cost Match**: raw total cost = analysis total cost (tolerance: +-1원)
2. **Conversion Match**: raw total conversions = analysis total conversions
3. **Parse Fail Exclusion**: FAIL creatives not in TIER analysis

### TIER Quality
1. **No Under-7-days**: No creatives with 집행일수 < 7 in TIER1~4
2. **No Low-Volume**: No creatives with 클릭<100 AND 비용<100,000 in TIER1~4
3. **TIER3 Check**: If TIER3 count is 0, verify elif order in classify_tier()

### Calculation Verification
1. **CPA**: CPA = 총비용 / 총전환 (spot check 3 random creatives)
2. **CVR**: CVR = 총전환 / 총클릭 (creative-level, NOT row-level)
3. **CTR**: CTR = 총클릭 / 총노출

### Hook Comparison
1. Has either strict_pairs OR type_comparison (at least one)
2. Unmatched list generated for reworked creatives

### OFF Creative
1. `is_off` flag parsed correctly from ad names ending with `_off`
2. OFF creatives excluded from TIER analysis (df_on)
3. OFF creatives sheet exists in Excel

### Output
1. Excel file has exactly 7 sheets
2. PDF file exists
3. analysis_validation.json exists

### Charts (if applicable)
1. Bubble chart data points = TIER1~4 count (no LOW_VOLUME/UNCLASSIFIED)
2. Heatmap has data (not empty)

## Blocking Rules
- **all_pass = false** → Phase 5 (report generation) is BLOCKED
- Console output: Display failures prominently
- Create `qa_report.json` regardless of pass/fail status

## Console Output on Failure
```
============================================================
QA VERIFICATION FAILED
============================================================
Failed Checks:
  - [description of each failure]

Phase 5 (Report Generation) BLOCKED until issues resolved.
============================================================
```
