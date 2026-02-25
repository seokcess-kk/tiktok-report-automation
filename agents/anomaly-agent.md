# Anomaly Agent

> Role: Detect data anomalies and quality issues

## Prerequisites
- Phase 0 completed: `output/normalized.parquet` exists
- Phase 1 completed: `output/parsed.parquet` exists

## Input Files
- `output/normalized.parquet` - Normalized data with attribution_caution flag
- `output/parsed.parquet` - Parsed data with metadata
- `output/creative_tier.parquet` - Creative TIER data

## Execution
```bash
python skills/creative-analyzer/scripts/detect_anomalies.py output/parsed.parquet output/creative_tier.parquet output
```

## Output Files
- `output/anomalies.csv` - All detected anomalies

## Completion Flag
- `output/anomaly_done.flag` - Created on successful completion

## Failure Handling
- Log errors to `logs/anomaly_error.log`
- Do not create completion flag on failure

## Detection Types

### 1. Attribution Caution
- Condition: click = 0 AND conversion > 0
- Interpretation: View-through or delayed conversion
- Flag: `attribution_caution = True`
- Action: Mark as hypothesis, not confirmed insight

### 2. Cost Spike
- Condition: Daily cost > 3x previous day
- Detection: Day-over-day comparison
- Action: Flag for budget pacing review

### 3. Zero CTR with High Impressions
- Condition: CTR = 0 AND impressions > 1000
- Interpretation: Possible ad serving issue
- Action: Flag for creative/targeting review

### 4. CVR Outliers
- Condition: CVR > 20% (unusually high)
- Z-score based detection
- Action: Verify data accuracy

### 5. CPA Outliers
- Condition: CPA > 3x median CPA
- Z-score based detection
- Action: Flag for budget reallocation

### 6. Branch Variance
- Condition: Same creative, CPA ratio > 3x between branches
- Action: Analyze branch-specific factors

### 7. Daily Trend Anomaly
- Condition: Significant deviation from 7-day moving average
- Action: Flag for review

## Core Rules
- Anomaly detection does NOT stop the pipeline
- Anomalies are flagged with annotations only
- Excel report shows anomaly indicators in relevant rows
- No automatic data correction or filtering

## Output CSV Columns
```
감지유형, 소재명, 지점, 날짜, 설명, 권장조치,
관련값1, 관련값2, ...
```

## Validation Checks
- [ ] All attribution_caution rows logged
- [ ] Anomaly counts match expected patterns
- [ ] No pipeline interruption from anomalies
