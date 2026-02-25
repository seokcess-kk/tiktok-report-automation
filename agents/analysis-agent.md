# Analysis Agent

> Role: Creative aggregation + TIER classification + Branch relative evaluation

## Prerequisites
- Phase 0 (normalize) completed: `output/normalized.parquet` exists
- Phase 1 (parse) completed: `output/parsed.parquet` exists

## Input Files
- `output/parsed.parquet` - Parsed ad data with metadata
- `input/target_cpa.csv` (optional) - Target CPA by branch

## Execution
```bash
python skills/creative-analyzer/scripts/score_creatives.py output/parsed.parquet output input/target_cpa.csv
```

## Output Files
- `output/creative_tier.parquet` - Creative TIER classification
- `output/creative_tier.csv` - CSV format
- `output/age_analysis.parquet` - Age group analysis
- `output/age_analysis.csv` - CSV format

## Completion Flag
- `output/analysis_done.flag` - Created on successful completion

## Failure Handling
- Log errors to `logs/analysis_error.log`
- Do not create completion flag on failure

## Core Rules (ABSOLUTE)

### TIER Classification Rules
1. **Aggregate by Creative First** - Group by (소재구분, 소재유형, 소재명)
   - NEVER evaluate TIER at row level (daily x age)
   - ALWAYS aggregate to creative level, then assign TIER

2. **Volume Gates**
   - 집행일수 < 7 days → `UNCLASSIFIED`
   - 클릭 < 100 AND 비용 < 100,000원 → `LOW_VOLUME`
   - Only creatives passing both gates can be TIER1~4

3. **TIER Assignment Order** (if/elif sequential)
   ```
   TIER1: CPA ≤ target_cpa AND CVR ≥ 5%
   TIER2: CTR ≥ avg_ctr × 1.2 AND NOT cpa_ok
   TIER3: Landing_rate ≥ avg_landing × 1.1 AND NOT cvr_ok
   TIER4: All metrics below average
   ```

4. **Target CPA Fallback**
   - If `target_cpa.csv` not found → Use median CPA of evaluable creatives

### Calculation Rules
- Use ONLY `_calc` columns (CTR_calc, CVR_calc, CPA_calc, LPV_rate_calc)
- NEVER use raw CTR/CVR/CPA columns from TikTok export
- CPA = 총비용 / 총전환 (creative-level aggregation)
- CVR = 총전환 / 총클릭 (creative-level aggregation)

### Branch Relative Evaluation
- Compare same creative's CPA across different branches
- Flag as TOP (≤70% of branch avg) or WORST (≥150% of branch avg)
- Do NOT adjust values - annotation only

## Validation Checks
- [ ] No creatives with 집행일수 < 7 in TIER1~4
- [ ] No creatives with 클릭 < 100 AND 비용 < 100,000 in TIER1~4
- [ ] CPA = 총비용 / 총전환 verified
- [ ] CVR = 총전환 / 총클릭 verified (NOT row-level)
