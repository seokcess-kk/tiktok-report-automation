# TikTok 광고 분석 오케스트레이터

> 클라이언트: 데이트 클리닉
> 캠페인 목표: 상담 전환 (소재 중심 분석)
> 버전: 3.0.0 (완전 자동화)

## 실행 조건

**필수:** `input/tiktok_raw.csv`
**선택:** `db_by_branch.csv`, `target_cpa.csv`, `creative_lineage.csv`

선택 파일이 없으면 해당 모듈은 건너뜁니다.

## 워크플로우

### Phase 0 - 원본 정규화 (순차)
```
tiktok-normalizer 스킬:
  - normalize_tiktok_raw.py -> output/normalized.parquet
  - Ad ID 문자열 변환 (지수 표기 방지)
  - 컬럼명 표준화
  - KPI 재계산: CTR_calc / CVR_calc / CPA_calc / LPV_rate_calc
  - 귀속 주의 플래그 (클릭=0 AND 전환>0)
```

### Phase 1 - 데이터 준비 (순차)
```
tiktok-parser 스킬:
  - 광고명 파싱 (소재구분/지점/소재유형/소재명/날짜코드)
  - parse_status = OK / FAIL
  - FAIL 소재 -> logs/parse_failures.csv (분석 제외)
  - 매칭 키 생성 (소재유형_소재명)
```

### Phase 2 - 병렬 분석 (서브에이전트)
```
서브에이전트 사용:
  - analysis-agent: 소재 집계 + TIER 분류 + 지점 상대평가
  - hook-agent: 신규 vs 재가공 훅 비교 (creative_lineage.csv 지원)
  - anomaly-agent: 이상치 감지
  - funnel-agent: 퍼널 분석 (db_by_branch.csv 있을 때)
```

### Phase 3 - 인사이트 생성
```
insight-agent:
  - 형식: 수치 근거 -> 해석 -> 액션 제안
  - 등급: 확정 인사이트 (표본 충분) / 가설 인사이트 (표본 부족)
  - improvement_suggestions.md 자동 생성
```

### Phase 4 - QA 검증 (순차)
```
qa-agent 체크리스트:
  [ ] raw total_cost = analysis total_cost (오차 +-1)
  [ ] raw total_conversions = analysis total_conversions
  [ ] CPA_calc = cost/conversions 검증
  [ ] TIER1~4에 <7일 또는 저볼륨 소재 없음
  [ ] OFF 소재 TIER 분석에서 제외됨
  [ ] Excel 7개 시트 생성됨
```

### Phase 5 - 리포트 생성 (순차)
```
report-generator 스킬:
  - Excel (7개 시트) -> output/YYYYMMDD/tiktok_analysis_YYYYMMDD.xlsx
  - PDF (2페이지) -> output/YYYYMMDD/tiktok_summary_YYYYMMDD.pdf
  - improvement_suggestions.md -> output/YYYYMMDD/
```

## 절대 규칙

1. **원본 CTR/CVR/CPA 컬럼 사용 금지** -> _calc 재계산 값만 사용
2. **클릭=0 AND 전환>0일 때 행 단위 CVR 계산 금지**
3. **parse_status=FAIL 소재 TIER 분류 금지**
4. **저볼륨 소재 TIER 분류 금지** (클릭<100 AND 비용<100,000)
5. **지점 편중 소재 수치 보정 금지** -> 주석 처리만
6. **행 단위 TIER 평가 금지** -> 소재별 집계 후 TIER 부여

## 입력 파일 형식

### tiktok_raw.csv (필수)
TikTok 광고 관리자 내보내기 컬럼:
- Ad Name, Ad ID, Date, Age, Cost, Impressions, Clicks, Conversions 등

### target_cpa.csv (선택)
```csv
지점,목표CPA
서울,20000
일산,20000
...
```

### db_by_branch.csv (선택)
```csv
지점,날짜,매체DB,실제DB,내원율,ROAS
서울,2026-02-01,50,40,30,150
...
```

### creative_lineage.csv (선택 - Phase 3)
```csv
creative_group_id,원본소재명,재가공소재명,변경요소,비고
GROUP_001,주사형비만치료제 10년은,체지방만쏙빼는(부산잇츠),썸네일+초기카피,2월 재가공
...
```

## 스킬 정의

### tiktok-normalizer
```yaml
name: tiktok-normalizer
description: TikTok 원본 CSV를 분석 가능한 형식으로 변환
triggers: tiktok csv 업로드, 분석 시작, 정규화
```

### creative-analyzer
```yaml
name: creative-analyzer
description: CTR/CVR/CPA/랜딩률 복합 지표로 소재 평가
  TIER1~4 / LOW_VOLUME / UNCLASSIFIED로 분류
triggers: 소재 분석, TIER 분류, 효율 좋은 소재
```

### hook-comparison
```yaml
name: hook-comparison
description: 신규 vs 재가공 소재 비교로 훅 효과 측정
triggers: 훅 비교, A/B 테스트, 재가공 효과
```

### funnel-analyzer
```yaml
name: funnel-analyzer
description: 매체DB -> 실제DB -> 내원 전환 퍼널 분석
triggers: 퍼널 분석, 내부 DB, 지점별 전환율
```

### insight-writer
```yaml
name: insight-writer
description: 분석 결과 기반 AI 인사이트 생성
triggers: 인사이트 생성, 액션 플랜, 개선 제안
```

## 자동 업데이트 정책

- 파서 패턴 오류: 자동 업데이트 허용
- 분석 로직 변경: `output/YYYYMMDD/improvement_suggestions.md`에만 저장

---

*실행: `python run_analysis.py`*
