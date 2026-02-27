# Daily Monitor 결정 이유 기록

## 목적
- 전일 대비 주요 지표 변동 감지
- 이상 신호 조기 발견
- 지점별 일일 변동 md 리포트 생성

## 스냅샷 구조
```json
{
  "date": "2026-02-27",
  "total_cost": 1234567,
  "total_conversions": 89,
  "avg_cpa": 13871,
  "by_branch": {
    "서울": {"cost": 500000, "conversions": 40},
    "일산": {"cost": 300000, "conversions": 25}
  },
  "top_creatives": [...]
}
```

## 이상 신호 임계값
- 비용 급증: 전일 대비 +50%
- CPA 급증: 전일 대비 +30%
- 전환 급락: 전일 대비 -30%
