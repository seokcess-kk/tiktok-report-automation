# TikTok 광고 분석 시스템 재설계 계획

> 생성일: 2026-02-25
> 버전: 3.1.0
> 상태: Plan 작성 완료

---

## 1. 프로젝트 개요

### 1.1 현재 상태 요약

| 구분 | 설계 문서 (v3.0) | 현재 구현 |
|------|-----------------|----------|
| Phase 0: 정규화 | normalize_tiktok_raw.py | ✅ 구현됨 |
| Phase 1: 파싱 | parse_tiktok.py | ✅ 구현됨 |
| Phase 2: 소재 분석 | score_creatives.py | ✅ 구현됨 |
| Phase 2: 훅 비교 | hook_comparison.py | ✅ 구현됨 |
| Phase 2: 이상치 감지 | detect_anomalies.py | ✅ 구현됨 |
| Phase 2: 퍼널 분석 | merge_db.py | ✅ 구현됨 (선택) |
| Phase 3: 인사이트 | generate_insights.py | ✅ 구현됨 |
| Phase 5: Excel | build_excel.py | ✅ 구현됨 (7시트) |
| Phase 5: PDF | build_pdf.py | ✅ 구현됨 (2페이지) |
| Phase 5: 차트 | build_charts.py | ✅ 구현됨 (8개 차트) |
| 오케스트레이터 | CLAUDE.md | ✅ 한글화 완료 |
| 메인 실행기 | run_analysis.py | ✅ 구현됨 |
| QA 체크 | QA 12/12 통과 | ✅ 통과 |

### 1.2 최근 수정 이력

- Excel NaN/inf 에러 수정 완료
- 시트명 7개 한글화 완료
- 차트 제목/라벨 8개 한글화 완료
- CLAUDE.md 전체 한글화 완료
- improvement_suggestions.md 템플릿 한글화 완료

---

## 2. 설계 문서 대비 Gap 분석

### 2.1 완료된 항목 (Match)

| 설계 항목 | 구현 상태 | 비고 |
|----------|---------|------|
| 광고 ID 문자열 로딩 | ✅ | 지수 표기 방지 |
| KPI _calc 재계산 | ✅ | CTR/CVR/CPA/LPV_rate |
| attribution_caution 플래그 | ✅ | 클릭=0 AND 전환>0 |
| parse_status OK/FAIL | ✅ | FAIL 소재 분석 제외 |
| TIER 분류 로직 | ✅ | TIER1~4/LOW_VOLUME/UNCLASSIFIED |
| 볼륨 게이트 | ✅ | 클릭<100 AND 비용<100,000 |
| 집행일수 7일 조건 | ✅ | UNCLASSIFIED 처리 |
| 지점 편중 주석 | ✅ | 70% 이상 집중 시 |
| 지점별 상대평가 | ✅ | TOP/WORST 플래그 |
| 훅 Strict 매칭 | ✅ | 소재유형+소재명 |
| 훅 소재유형 집계 비교 | ✅ | Fallback 방식 |
| 나이대 예산효율점수 | ✅ | 전환비중/비용비중 |
| OFF 소재 분리 | ✅ | 별도 시트 |

### 2.2 Gap 항목 (Missing/Partial)

| 설계 항목 | 현재 상태 | 우선순위 | 비고 |
|----------|---------|---------|------|
| 차트 3개 미구현 | ⚠️ Partial | 중 | 레이더/CPA분포/효율점수 차트 |
| creative_lineage.csv 지원 | ❌ Missing | 하 | 2단계 고도화 항목 |
| 소재 피로도 차트 | ⚠️ Partial | 중 | 일별 CTR로 대체 중 |
| hooks 자동화 | ❌ Missing | 하 | 3단계 자동화 항목 |
| analysis_raw.json | ❌ Missing | 중 | QA용 원본 데이터 저장 |

### 2.3 설계 대비 개선된 항목 (Enhancement)

| 항목 | 설계 | 구현 | 비고 |
|------|-----|-----|------|
| 차트 수 | 11개 | 8개 | 핵심 차트 유지, 중복 제거 |
| 한글화 | 영문 | 완전 한글 | UX 개선 |
| NaN 처리 | 미언급 | 완료 | Excel 호환성 |

---

## 3. 재설계 방향

### 3.1 유지할 항목 (Keep)

1. **핵심 워크플로우**: Phase 0~5 순차 실행 구조
2. **절대 규칙 6가지**: raw 컬럼 금지, 소재 단위 집계 등
3. **TIER 분류 로직**: 볼륨 게이트, 집행일수 조건
4. **Excel 7시트 구조**: 요약~OFF 소재
5. **PDF 2페이지 구조**: KPI 요약 + 인사이트

### 3.2 개선할 항목 (Improve)

| 우선순위 | 항목 | 현재 | 개선안 |
|---------|------|-----|-------|
| 높음 | 시트명 이모지 | 없음 | 설계대로 이모지 추가 |
| 높음 | analysis_raw.json | 미생성 | QA용 원본 데이터 저장 |
| 중간 | 레이더 차트 | 미구현 | 소재유형별 4지표 비교 |
| 중간 | 소재 피로도 차트 | 일별 CTR | 주요 소재별 CVR 추이 |
| 낮음 | creative_lineage | 미지원 | 수동 훅 매핑 지원 |

### 3.3 삭제/간소화할 항목 (Simplify)

1. **중복 차트 제거**: 나이대 효율점수 막대 (비용vs전환 차트로 충분)
2. **복잡한 조건부 서식**: 기본 색상 규칙으로 통일

---

## 4. 액션 플랜

### Phase 1: 즉시 수정 (v3.1.0)

| # | 작업 | 파일 | 예상 시간 |
|---|-----|-----|---------|
| 1 | 시트명 이모지 추가 | build_excel.py | - |
| 2 | analysis_raw.json 생성 | run_analysis.py | - |
| 3 | 요약 시트 KPI 카드 개선 | build_excel.py | - |

### Phase 2: 차트 고도화 (v3.2.0)

| # | 작업 | 파일 | 비고 |
|---|-----|-----|-----|
| 1 | 소재유형 레이더 차트 | build_charts.py | 새 차트 |
| 2 | 소재 피로도 라인 차트 | build_charts.py | 설계 명세 참조 |
| 3 | 지점별 CPA 목표선 추가 | build_charts.py | target_cpa.csv 연동 |

### Phase 3: 자동화 (v3.3.0)

| # | 작업 | 파일 | 비고 |
|---|-----|-----|-----|
| 1 | pre-run.sh 훅 | .claude/hooks/ | 파일 감지 |
| 2 | post-analysis.sh 훅 | .claude/hooks/ | 리포트 트리거 |
| 3 | creative_lineage.csv 지원 | hook_comparison.py | 수동 매핑 |

---

## 5. 설계 문서 업데이트 권장사항

### 5.1 CLAUDE.md 개선

```markdown
현재: 한글화 완료, 기본 워크플로우 기술
개선:
- 입력 파일별 처리 흐름도 추가
- 에러 발생 시 대응 가이드 추가
- 출력 파일 목록 및 용도 명시
```

### 5.2 차트 명세 (tiktok-chart-spec.md) 개선

```markdown
현재: 11개 차트 명세
개선:
- 실제 구현된 8개 차트로 조정
- 한글 라벨 명세 추가
- 색상 코드 통일 (TIER_COLORS)
```

### 5.3 QA 체크리스트 개선

```markdown
현재: 10개 항목
개선:
- Excel 열기 테스트 추가
- 한글 깨짐 확인 추가
- 차트 이미지 렌더링 확인 추가
```

---

## 6. 검증 기준

### 6.1 성공 기준

- [ ] Excel 파일 정상 열기 (NaN/inf 에러 없음)
- [ ] 시트명 7개 한글 표시
- [ ] 차트 8개 정상 렌더링
- [ ] QA 12/12 통과
- [ ] PDF 2페이지 생성
- [ ] improvement_suggestions.md 한글 생성

### 6.2 현재 달성 상태

| 기준 | 상태 |
|-----|------|
| Excel 열기 | ✅ 통과 |
| 시트명 한글 | ✅ 통과 |
| 차트 렌더링 | ✅ 통과 |
| QA 12/12 | ✅ 통과 |
| PDF 생성 | ✅ 통과 |
| 인사이트 한글 | ✅ 통과 |

---

## 7. 결론

### 7.1 현재 시스템 평가

**전체 완성도: 90%** (설계 대비)

- 핵심 기능 100% 구현
- 차트 73% 구현 (8/11)
- 자동화 기능 미구현 (3단계)

### 7.2 권장 다음 단계

1. **즉시**: 시트명 이모지 추가 (UX 개선)
2. **단기**: 레이더 차트, 피로도 차트 추가
3. **중기**: creative_lineage.csv 지원
4. **장기**: 완전 자동화 (hooks)

---

*이 Plan 문서는 `/pdca design tiktok-redesign` 명령으로 Design 단계로 진행할 수 있습니다.*
