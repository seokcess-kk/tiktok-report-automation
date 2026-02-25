# Insight Agent

> Role: Generate AI-powered insights based on analysis results

## Prerequisites
- Phase 2 all agents completed
- Required files exist:
  - `output/creative_tier.parquet`
  - `output/age_analysis.parquet` (or .csv)
  - `output/hook_type_comparison.parquet` (or .csv)
  - `output/anomalies.csv`

## Input Files
- `output/creative_tier.parquet` - Creative TIER classification
- `output/hook_strict_pairs.parquet` - Hook comparison pairs
- `output/hook_type_comparison.parquet` - Type-level comparison
- `output/age_analysis.parquet` - Age group analysis
- `output/anomalies.csv` - Detected anomalies
- `output/funnel_metrics.parquet` (optional) - Funnel analysis

## Execution
```bash
python skills/insight-writer/scripts/generate_insights.py output output/YYYYMMDD
```

## Output Files
- `output/YYYYMMDD/improvement_suggestions.md` - Markdown insights document

## Completion Flag
- `output/insight_done.flag` - Created on successful completion

## Failure Handling
- Log errors to `logs/insight_error.log`
- Do not create completion flag on failure

## Insight Format
```
수치 근거 → 해석 → 액션 제안

Example:
"'다이어트 빼는 게 아니라 찾는 것' 소재의 CTR 0.97%(전체 평균 0.60% 대비 +62%),
 CVR 7.40%, CPA 15,119원으로 전 지표 최우수입니다.
 현재 서울·일산 2개 지점에만 집행 중이므로 대구·천안 지점 추가 집행을 권장합니다."
```

## Insight Grades

### Confirmed Insight (확정 인사이트)
- Criteria: 클릭 100건+ AND QA checks passed
- Confidence: High
- Can make definitive statements

### Hypothesis Insight (가설 인사이트)
- Criteria: Any of the following:
  - 클릭 < 100건
  - attribution_caution rows included
  - LOW_VOLUME creative
- Confidence: Low
- MUST include qualifier phrases

## Forbidden Expressions (ABSOLUTE)

1. **NO definitive statements for LOW_VOLUME creatives**
   - Forbidden: "최고 효율", "가장 우수", "확실히"
   - Required: "추가 데이터 필요", "가설 수준"

2. **NO CVR claims based on click=0 rows**
   - Forbidden: Using CVR from rows where click=0 and conversion>0
   - Required: Exclude from CVR-based insights or mark as hypothesis

3. **NO definitive age group claims with small samples**
   - Forbidden: "25-34세가 가장 비효율적" (with only 10 conversions)
   - Required: Sample size qualifier

4. **NO time estimates or predictions**
   - Forbidden: "1주일 내 개선", "빠른 시일 내"
   - Required: Focus on actions, not timelines

## Insight Categories

### CREATIVE
- Top Performer identification (TIER1)
- Underperforming creatives (TIER4)
- LOW_VOLUME warnings

### TARGETING
- Age group efficiency analysis
- Budget allocation recommendations

### CREATIVE_OPTIMIZATION
- Hook effectiveness (original vs reworked)
- Landing page alignment issues

### BRANCH
- Branch variance alerts
- Branch-specific recommendations

### DATA_QUALITY
- Attribution caution warnings
- Insufficient data alerts

### FUNNEL (if db_by_branch.csv exists)
- DB conversion rate by branch
- Non-ad controllable factors context

## Action Plan Structure
```
Priority 1: [Highest impact action]
Priority 2: [Second priority action]
Priority 3: [Third priority action]
```

## Validation Checks
- [ ] No forbidden expressions in output
- [ ] All LOW_VOLUME creatives marked as hypothesis
- [ ] Attribution caution data flagged appropriately
- [ ] improvement_suggestions.md generated successfully
