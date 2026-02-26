# HTML 차트 분리 계획

> 생성일: 2026-02-26
> 버전: 4.0.0
> 상태: Plan 작성 완료

---

## 1. 요구사항

### 1.1 변경 목표

| 현재 | 변경 후 |
|------|--------|
| Excel 파일에 데이터 + 차트 이미지 포함 | Excel은 데이터만, 차트는 HTML 별도 파일 |

### 1.2 기대 효과

- **Excel 파일 경량화**: 차트 이미지 제거로 파일 크기 감소 (837KB → ~100KB)
- **인터랙티브 차트**: HTML에서 마우스 오버, 줌, 필터 기능 제공
- **공유 용이성**: HTML은 브라우저만 있으면 열람 가능
- **유지보수**: 데이터/시각화 분리로 각각 독립 수정 가능

---

## 2. 출력 파일 구조 변경

### 2.1 기존

```
output/YYYYMMDD/
├── tiktok_analysis_YYYYMMDD.xlsx    # 데이터 + 차트 이미지 (837KB)
├── tiktok_summary_YYYYMMDD.pdf
├── improvement_suggestions.md
└── analysis_raw.json
```

### 2.2 변경 후

```
output/YYYYMMDD/
├── tiktok_analysis_YYYYMMDD.xlsx    # 데이터만 (~100KB)
├── tiktok_charts_YYYYMMDD.html      # 인터랙티브 차트 (신규)
├── tiktok_summary_YYYYMMDD.pdf
├── improvement_suggestions.md
└── analysis_raw.json
```

---

## 3. 기술 선택

### 3.1 HTML 차트 라이브러리

| 옵션 | 장점 | 단점 |
|------|------|------|
| **Plotly** (선택) | 인터랙티브, 단일 HTML 파일, Python 연동 우수 | 파일 크기 다소 큼 |
| Chart.js | 경량 | JavaScript 코드 직접 작성 필요 |
| ECharts | 다양한 차트 | 학습 곡선 |

**결정: Plotly 사용** - `plotly.express` + `plotly.graph_objects`

### 3.2 의존성 추가

```bash
pip install plotly kaleido
```

---

## 4. 구현 범위

### 4.1 Excel 변경 (build_excel.py)

| 항목 | 변경 내용 |
|------|----------|
| 차트 삽입 코드 | 모두 제거 |
| `add_*_chart()` 호출 | 모두 제거 |
| 시트 구조 | 데이터 테이블만 유지 |
| KPI 카드 | 유지 (데이터 기반) |
| 스타일링 | 유지 |

### 4.2 HTML 차트 생성 (build_html_charts.py - 신규)

| 차트 | Plotly 유형 | 설명 |
|------|------------|------|
| TIER 분포 도넛 | `px.pie` | 소재 TIER 비중 |
| 지점별 CPA 막대 | `px.bar` | 목표선 포함 |
| 소재유형 레이더 | `go.Scatterpolar` | 4지표 비교 |
| 소재 버블 | `px.scatter` | CTR×CVR×비용 |
| 훅 전후 비교 | `px.bar` | grouped bar |
| 나이대 비용vs전환 | `px.bar` | grouped bar |
| 히트맵 (CTR/CVR) | `px.imshow` | 소재유형×나이대 |
| 일별 트렌드 | `px.line` | 콤보 차트 |
| 피로도 라인 | `px.line` | CVR 추이 |
| CPA 목표선 | `px.line` | 일별 CPA + 목표 |

### 4.3 HTML 구조

```html
<!DOCTYPE html>
<html>
<head>
    <title>TikTok 광고 분석 차트 - YYYYMMDD</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        /* 네비게이션 탭, 반응형 레이아웃 */
    </style>
</head>
<body>
    <nav>
        <button onclick="showSection('summary')">📊 요약</button>
        <button onclick="showSection('tier')">🎬 TIER</button>
        <button onclick="showSection('hook')">🔄 훅</button>
        <button onclick="showSection('age')">👥 나이대</button>
        <button onclick="showSection('daily')">📅 일별</button>
    </nav>

    <section id="summary">
        <!-- KPI 카드 + TIER 도넛 + 지점 CPA -->
    </section>

    <section id="tier">
        <!-- 버블 차트 + 레이더 -->
    </section>

    <!-- ... -->
</body>
</html>
```

---

## 5. 파일 변경 목록

| 파일 | 변경 유형 | 내용 |
|------|----------|------|
| `build_excel.py` | 수정 | 차트 삽입 코드 제거 |
| `build_charts.py` | 삭제/보관 | matplotlib 차트 (더 이상 사용 안 함) |
| `build_html_charts.py` | **신규** | Plotly 기반 HTML 차트 생성 |
| `run_analysis.py` | 수정 | HTML 생성 호출 추가 |

---

## 6. 구현 순서

```
1. build_html_charts.py 신규 작성 (핵심)
   - Plotly 차트 함수 11개
   - HTML 템플릿 + 네비게이션

2. build_excel.py 수정
   - 차트 삽입 코드 제거
   - import build_charts 제거

3. run_analysis.py 수정
   - build_html_charts 호출 추가

4. 테스트
   - Excel 정상 생성 (데이터만)
   - HTML 정상 생성 (차트만)
   - 브라우저에서 인터랙티브 동작 확인
```

---

## 7. 검증 기준

- [ ] Excel 파일 정상 열기 (차트 없이)
- [ ] Excel 파일 크기 감소 (< 200KB)
- [ ] HTML 파일 생성
- [ ] HTML 브라우저에서 정상 렌더링
- [ ] 11개 차트 모두 인터랙티브 동작
- [ ] QA 12/12 유지

---

*이 Plan 문서는 `/pdca design html-chart-separation` 명령으로 Design 단계로 진행할 수 있습니다.*
