# Hook Agent

> Role: Original (신규) vs Reworked (재가공) hook effect comparison

## Prerequisites
- Phase 2 analysis-agent completed: `output/creative_tier.parquet` exists

## Input Files
- `output/creative_tier.parquet` - Creative TIER data with 소재구분 column
- `input/creative_lineage.csv` (optional) - Explicit original-rework mapping

## Execution
```bash
python skills/creative-analyzer/scripts/hook_comparison.py output/creative_tier.parquet output input/creative_lineage.csv
```

## Output Files
- `output/hook_strict_pairs.parquet` - Strict matched pairs (소재유형 + 소재명 exact match)
- `output/hook_strict_pairs.csv` - CSV format
- `output/hook_type_comparison.parquet` - Ad type level aggregation comparison
- `output/hook_type_comparison.csv` - CSV format
- `output/hook_unmatched.csv` - Reworked creatives without matching original

## Completion Flag
- `output/hook_done.flag` - Created on successful completion

## Failure Handling
- Log errors to `logs/hook_error.log`
- Do not create completion flag on failure

## Matching Strategy (3-tier)

### A. Lineage Matching (Most Accurate)
- Use `creative_lineage.csv` for explicit mapping
- Columns: creative_group_id, 원본소재명, 재가공소재명, 변경요소

### B. Strict Matching
- Match by: 소재유형 + 소재명 exact match
- Different branches with same creative are considered the same

### C. Ad Type Aggregation (Fallback)
- Compare: "인플방문후기 신규" vs "인플방문후기 재가공" at aggregate level
- Used when Strict matching yields 0 pairs

## Hook Verdict Logic
```python
def hook_verdict(orig_ctr, re_ctr, orig_cvr, re_cvr):
    ctr_up = re_ctr > orig_ctr
    cvr_up = re_cvr > orig_cvr

    if ctr_up and cvr_up:
        return '재가공 유효 — 클릭·전환 모두 개선'
    elif ctr_up and not cvr_up:
        return '부분 효과 — 클릭↑ 전환↓ (랜딩 불일치 가능성)'
    elif not ctr_up and cvr_up:
        return '부분 효과 — 클릭↓ 전환↑ (정밀 타겟팅 가능성)'
    else:
        return '재가공 효과 없음 — 원본 훅 복귀 검토'
```

## Core Rules
- Strict matching 0 pairs is NOT an error → Auto-fallback to type aggregation
- `creative_lineage.csv` not found → Skip lineage matching, use auto-matching only
- Always output `hook_unmatched.csv` for reworked creatives without matches

## Validation Checks
- [ ] Has strict_pairs OR type_comparison (at least one)
- [ ] Unmatched list generated for reworked creatives
