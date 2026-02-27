# Daily Monitor 전략 & 아키텍처

## 목표
주간 리포트 생성 시 자동으로 데일리 스냅샷 저장 및 비교

## 데이터 흐름
```
parsed.parquet
    ↓
save_snapshot.py → daily/snapshots/YYYYMMDD_summary.json
    ↓
compare_snapshots.py → delta 계산
    ↓
detect_daily_anomalies.py → 이상 신호 감지
    ↓
build_daily_report.py → output/YYYYMMDD/daily_YYYYMMDD.md
```

## 통합 방식
- run_analysis.py Phase 5 이후 자동 호출
- 스냅샷 폴더: daily/snapshots/
- 삭제 금지 (히스토리 누적)

## 구현 우선순위
STEP 3~6 완료 후 4단계에서 구현
