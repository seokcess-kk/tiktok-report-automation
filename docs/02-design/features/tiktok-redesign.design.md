# TikTok 광고 분석 시스템 재설계 - Design 문서

> 생성일: 2026-02-25
> 버전: 3.1.0
> Plan 참조: docs/01-plan/features/tiktok-redesign.plan.md

---

## 1. 설계 개요

### 1.1 목적

Plan 문서에서 정의된 Gap 항목을 해결하고, 설계 문서(v3.0)와의 일관성을 높이기 위한 상세 설계

### 1.2 범위

| 버전 | 범위 | 우선순위 |
|-----|------|---------|
| v3.1.0 | 즉시 수정 (시트명 이모지, analysis_raw.json) | 높음 |
| v3.2.0 | 차트 고도화 (레이더, 피로도) | 중간 |
| v3.3.0 | 자동화 (hooks, creative_lineage) | 낮음 |

---

## 2. v3.1.0 상세 설계

### 2.1 시트명 이모지 추가

**파일**: `skills/report-generator/scripts/build_excel.py`

**현재 → 변경**:

| 현재 | 변경 |
|-----|------|
| 1.요약 대시보드 | 📊 요약 대시보드 |
| 2.소재 TIER 분석 | 🎬 소재 TIER 분석 |
| 3.훅 개선 효과 | 🔄 훅 개선 효과 |
| 4.지점 컨텍스트 | 🏢 지점 컨텍스트 |
| 5.나이대 분석 | 👥 나이대 분석 |
| 6.일별 트렌드 | 📅 일별 트렌드 |
| 7.OFF 소재 | ⏸ OFF 소재 |

**구현 코드**:

```python
# build_excel.py 시트 생성 함수들

def create_summary_sheet(ws, ...):
    ws.title = "📊 요약 대시보드"

def create_tier_sheet(ws, ...):
    ws.title = "🎬 소재 TIER 분석"

def create_hook_sheet(ws, ...):
    ws.title = "🔄 훅 개선 효과"

def create_branch_sheet(ws, ...):
    ws.title = "🏢 지점 컨텍스트"

def create_age_sheet(ws, ...):
    ws.title = "👥 나이대 분석"

def create_daily_trend_sheet(ws, ...):
    ws.title = "📅 일별 트렌드"

def create_off_sheet(ws, ...):
    ws.title = "⏸ OFF 소재"
```

### 2.2 analysis_raw.json 생성

**파일**: `run_analysis.py`

**목적**: QA 검증 및 디버깅용 원본 데이터 저장

**구조**:

```json
{
  "generated_at": "2026-02-25T12:00:00",
  "input_files": {
    "tiktok_raw": {
      "path": "input/tiktok_raw.csv",
      "rows": 3763,
      "columns": ["ad_name", "cost", "conversions", ...]
    },
    "target_cpa": {
      "path": "input/target_cpa.csv",
      "exists": true
    },
    "db_by_branch": {
      "path": "input/db_by_branch.csv",
      "exists": false
    }
  },
  "processing": {
    "phase0_normalized": 3763,
    "phase1_parsed_ok": 3763,
    "phase1_parsed_fail": 0,
    "phase2_creatives": 16,
    "phase2_off_creatives": 0
  },
  "totals": {
    "raw_cost": 12613261,
    "raw_conversions": 483,
    "analysis_cost": 12613261,
    "analysis_conversions": 483,
    "match": true
  },
  "tier_distribution": {
    "TIER1": 6,
    "TIER2": 0,
    "TIER3": 0,
    "TIER4": 5,
    "LOW_VOLUME": 4,
    "UNCLASSIFIED": 1
  }
}
```

**구현 위치**: `run_analysis.py` Phase 5 이후

```python
def save_analysis_raw(output_dir, df_raw, df_parsed, creative_df):
    """analysis_raw.json 저장"""
    import json

    raw_data = {
        "generated_at": datetime.now().isoformat(),
        "input_files": { ... },
        "processing": { ... },
        "totals": { ... },
        "tier_distribution": creative_df['TIER'].value_counts().to_dict()
    }

    with open(f"{output_dir}/analysis_raw.json", 'w', encoding='utf-8') as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=2)
```

### 2.3 요약 시트 KPI 카드 개선

**파일**: `skills/report-generator/scripts/build_excel.py`

**현재 → 변경**:

| 현재 | 변경 |
|-----|------|
| 텍스트 리스트 | 박스형 KPI 카드 4개 |

**KPI 카드 구성**:

```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│ 총 광고비   │ 총 전환수   │ 평균 CPA    │ 평균 CTR    │
│ 12,613,261원│ 483건       │ 26,114원    │ 0.61%       │
│ (기간 합계) │ (기간 합계) │ (목표 대비) │ (업계 평균) │
└─────────────┴─────────────┴─────────────┴─────────────┘
```

---

## 3. v3.2.0 상세 설계

### 3.1 소재유형 레이더 차트

**파일**: `skills/report-generator/scripts/build_charts.py`

**목적**: 소재유형별 4지표(CTR/CVR/CPA/랜딩률) 종합 비교

**함수 시그니처**:

```python
def add_type_radar_chart(ws, creative_df, anchor_cell="K2"):
    """
    소재유형별 레이더 차트
    축: CTR, CVR, 1/CPA(정규화), 랜딩률
    그룹: 인플방문후기, 진료셀프캠, 의료진정보
    """
```

**데이터 준비**:

```python
# 소재유형별 평균 계산
type_summary = creative_df.groupby('소재유형').agg({
    'CTR': 'mean',
    'CVR': 'mean',
    'CPA': 'mean',
    '랜딩률': 'mean'
}).reset_index()

# CPA는 낮을수록 좋으므로 역수 정규화
type_summary['CPA_norm'] = type_summary['CPA'].max() / type_summary['CPA']
```

**차트 설정**:

```python
categories = ['CTR', 'CVR', 'CPA 효율', '랜딩률']
colors = ['#3b82f6', '#10b981', '#f59e0b']  # 소재유형별
```

### 3.2 소재 피로도 라인 차트

**파일**: `skills/report-generator/scripts/build_charts.py`

**목적**: 주요 소재별 일별 CVR 추이로 피로도 감지

**함수 시그니처**:

```python
def add_fatigue_line_chart(ws, df_daily, top_creatives, anchor_cell="A45"):
    """
    상위 5개 소재의 일별 CVR 추이
    - TIER1 + 비용 상위 소재 선택
    - CVR 5% 기준선 표시
    - 하락 추세 감지 시 주석
    """
```

**데이터 준비**:

```python
# 상위 5개 소재 선택 (TIER1 우선, 비용 상위)
tier1_creatives = creative_df[creative_df['TIER'] == 'TIER1']['소재명'].tolist()
top_cost_creatives = creative_df.nlargest(5, '총비용')['소재명'].tolist()
top_creatives = list(dict.fromkeys(tier1_creatives + top_cost_creatives))[:5]

# 일별 CVR 계산
daily_cvr = df_valid.groupby(['소재명', 'date']).agg({
    'conversions': 'sum',
    'clicks': 'sum'
}).reset_index()
daily_cvr['CVR'] = (daily_cvr['conversions'] / daily_cvr['clicks'].replace(0, np.nan) * 100)
```

**차트 설정**:

```python
colors = ['#10b981', '#3b82f6', '#ef4444', '#f59e0b', '#9b59b6']
ax.axhline(5.0, color='gray', linestyle='--')  # CVR 5% 기준선
```

### 3.3 지점별 CPA 목표선 추가

**파일**: `skills/report-generator/scripts/build_charts.py`

**현재 함수**: `add_branch_cpa_bar()`

**변경 사항**:

```python
def add_branch_cpa_bar(ws, branch_df, target_cpa_map=None, anchor_cell="K18"):
    """
    지점별 CPA 가로막대 + 목표 CPA 기준선

    target_cpa_map: {지점: 목표CPA} 딕셔너리
    - 있으면 지점별 개별 목표선
    - 없으면 전체 중앙값 기준선
    """
    # 기존 코드 + 목표선 추가
    if target_cpa_map:
        for i, branch in enumerate(branches):
            target = target_cpa_map.get(branch)
            if target:
                ax.axvline(target, color='red', linestyle=':', alpha=0.5)
                ax.text(target, i, f'목표', fontsize=7, color='red')
```

---

## 4. v3.3.0 상세 설계

### 4.1 pre-run.sh 훅

**파일**: `.claude/hooks/pre-run.sh`

**목적**: 분석 실행 전 입력 파일 검증

```bash
#!/bin/bash
# pre-run.sh - 입력 파일 검증

INPUT_DIR="input"
REQUIRED_FILE="tiktok_raw.csv"

if [ ! -f "$INPUT_DIR/$REQUIRED_FILE" ]; then
    echo "[ERROR] 필수 파일 없음: $INPUT_DIR/$REQUIRED_FILE"
    exit 1
fi

# CSV 컬럼 검증
REQUIRED_COLS="광고 이름,비용,전환수"
HEADER=$(head -1 "$INPUT_DIR/$REQUIRED_FILE")

for col in $(echo $REQUIRED_COLS | tr ',' ' '); do
    if ! echo "$HEADER" | grep -q "$col"; then
        echo "[WARNING] 필수 컬럼 없음: $col"
    fi
done

echo "[OK] 입력 파일 검증 완료"
```

### 4.2 post-analysis.sh 훅

**파일**: `.claude/hooks/post-analysis.sh`

**목적**: 분석 완료 후 리포트 트리거

```bash
#!/bin/bash
# post-analysis.sh - 분석 완료 후 처리

OUTPUT_DIR="output/$(date +%Y%m%d)"

# Excel 파일 생성 확인
if [ -f "$OUTPUT_DIR/tiktok_analysis_*.xlsx" ]; then
    echo "[OK] Excel 리포트 생성 완료"
else
    echo "[ERROR] Excel 리포트 생성 실패"
    exit 1
fi

# 자동 열기 (선택)
# start "$OUTPUT_DIR/tiktok_analysis_*.xlsx"

echo "[OK] 분석 완료"
```

### 4.3 creative_lineage.csv 지원

**파일**: `skills/creative-analyzer/scripts/hook_comparison.py`

**변경 사항**:

```python
def match_hook_pairs_with_lineage(creative_df, lineage_path=None):
    """
    1. creative_lineage.csv 있으면 수동 매핑 우선 사용
    2. 없으면 기존 Strict 매칭 + 소재유형 집계 비교
    """

    # 1. Lineage 파일 로드 시도
    if lineage_path and os.path.exists(lineage_path):
        lineage_df = pd.read_csv(lineage_path)
        # 원본-재가공 쌍 매핑
        lineage_pairs = lineage_df.merge(
            creative_df, left_on='원본소재명', right_on='소재명'
        ).merge(
            creative_df, left_on='재가공소재명', right_on='소재명',
            suffixes=('_원본', '_재가공')
        )
        lineage_pairs['match_type'] = 'lineage'
        return lineage_pairs, None

    # 2. 기존 로직 (Strict + Type 집계)
    return match_hook_pairs(creative_df)
```

---

## 5. 파일 변경 목록

### 5.1 v3.1.0

| 파일 | 변경 유형 | 변경 내용 |
|-----|---------|----------|
| `build_excel.py` | 수정 | 시트명 이모지 추가 (7곳) |
| `run_analysis.py` | 추가 | `save_analysis_raw()` 함수 |
| `build_excel.py` | 수정 | `create_summary_sheet()` KPI 카드 |

### 5.2 v3.2.0

| 파일 | 변경 유형 | 변경 내용 |
|-----|---------|----------|
| `build_charts.py` | 추가 | `add_type_radar_chart()` |
| `build_charts.py` | 추가 | `add_fatigue_line_chart()` |
| `build_charts.py` | 수정 | `add_branch_cpa_bar()` 목표선 |
| `build_excel.py` | 수정 | 새 차트 호출 추가 |

### 5.3 v3.3.0

| 파일 | 변경 유형 | 변경 내용 |
|-----|---------|----------|
| `.claude/hooks/pre-run.sh` | 신규 | 입력 검증 훅 |
| `.claude/hooks/post-analysis.sh` | 신규 | 완료 후 처리 훅 |
| `hook_comparison.py` | 수정 | lineage 지원 추가 |

---

## 6. 테스트 계획

### 6.1 v3.1.0 테스트

| # | 테스트 항목 | 검증 방법 |
|---|-----------|----------|
| 1 | 시트명 이모지 | Excel 열어서 시트 탭 확인 |
| 2 | analysis_raw.json | 파일 존재 및 JSON 유효성 |
| 3 | KPI 카드 | 요약 시트 레이아웃 확인 |

### 6.2 v3.2.0 테스트

| # | 테스트 항목 | 검증 방법 |
|---|-----------|----------|
| 1 | 레이더 차트 | 3개 소재유형 모두 표시 |
| 2 | 피로도 차트 | 5개 이하 소재 라인 표시 |
| 3 | CPA 목표선 | target_cpa.csv 있을 때만 표시 |

### 6.3 v3.3.0 테스트

| # | 테스트 항목 | 검증 방법 |
|---|-----------|----------|
| 1 | pre-run.sh | 파일 없을 때 에러 |
| 2 | post-analysis.sh | 분석 후 자동 실행 |
| 3 | lineage 매핑 | 수동 매핑 우선 적용 |

---

## 7. 구현 순서

### 7.1 권장 구현 순서

```
v3.1.0:
  1. build_excel.py 시트명 이모지 (15분)
  2. run_analysis.py analysis_raw.json (30분)
  3. build_excel.py KPI 카드 (30분)
  4. 테스트 및 QA (15분)

v3.2.0:
  1. build_charts.py 레이더 차트 (1시간)
  2. build_charts.py 피로도 차트 (1시간)
  3. build_charts.py CPA 목표선 (30분)
  4. build_excel.py 차트 연동 (30분)
  5. 테스트 및 QA (30분)

v3.3.0:
  1. hooks 스크립트 작성 (30분)
  2. hook_comparison.py lineage 지원 (1시간)
  3. 통합 테스트 (30분)
```

### 7.2 의존성

```
build_excel.py ← build_charts.py (차트 함수 호출)
run_analysis.py ← 모든 스킬 스크립트
hook_comparison.py ← creative_lineage.csv (선택)
```

---

## 8. 가독성 및 시인성 개선 설계

### 8.1 전체 디자인 원칙

| 원칙 | 설명 | 적용 |
|------|------|------|
| **시각적 계층** | 정보 중요도에 따른 시각적 구분 | 제목 > 섹션 > 데이터 |
| **여백 활용** | 적절한 공간 확보로 가독성 향상 | 행 높이, 셀 패딩 |
| **색상 일관성** | TIER 색상 체계 일관 적용 | 모든 시트 동일 |
| **정렬 통일** | 데이터 유형별 정렬 규칙 | 텍스트=좌측, 숫자=우측 |
| **직관적 흐름** | 왼쪽→오른쪽, 위→아래 | 중요 정보 먼저 |

### 8.2 시트별 UX 개선

#### 8.2.1 📊 요약 대시보드

**현재 문제점**:
- 텍스트 리스트 형태로 KPI가 나열됨
- 시각적 구분이 없어 중요 정보 파악 어려움
- 차트와 텍스트의 배치가 산만함

**개선 설계**:

```
┌─────────────────────────────────────────────────────────────────────┐
│  🎯 TikTok 광고 분석 리포트                                          │
│  분석 기간: 2026-02-01 ~ 2026-02-20  │  생성: 2026-02-25 20:28       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ╔═══════════╗  ╔═══════════╗  ╔═══════════╗  ╔═══════════╗         │
│  ║ 총 광고비 ║  ║ 총 전환수 ║  ║ 평균 CPA  ║  ║ 평균 CTR  ║         │
│  ║12,613,261║  ║    483    ║  ║  26,114   ║  ║   0.61%   ║         │
│  ║    원    ║  ║    건    ║  ║    원     ║  ║          ║         │
│  ╚═══════════╝  ╚═══════════╝  ╚═══════════╝  ╚═══════════╝         │
│                                                                      │
├────────────────────────────────┬────────────────────────────────────┤
│  📊 TIER 분포                   │  🏢 지점별 CPA                      │
│  ┌──────────────────┐          │  ┌──────────────────────────┐      │
│  │   [도넛 차트]     │          │  │    [가로막대 차트]        │      │
│  │                  │          │  │                          │      │
│  │   TIER1: 6개     │          │  │   일산 ████████ 15,588원  │      │
│  │   TIER4: 5개     │          │  │   서울 ██████████ 18,323원│      │
│  │   LOW_VOL: 4개   │          │  │   부평 ████████████ 25,114│      │
│  │                  │          │  │   창원 ██████████████ 39,8│      │
│  └──────────────────┘          │  └──────────────────────────┘      │
├────────────────────────────────┴────────────────────────────────────┤
│  ⚠️ 데이터 품질 참고사항                                             │
│  • 분석 소재: 16개  │  OFF 소재: 0개  │  귀속주의: 36건              │
└─────────────────────────────────────────────────────────────────────┘
```

**스타일 코드**:

```python
# KPI 카드 스타일
KPI_CARD_FILL = PatternFill(start_color="EBF5FB", end_color="EBF5FB", fill_type="solid")
KPI_CARD_BORDER = Border(
    left=Side(style='medium', color='3498DB'),
    right=Side(style='medium', color='3498DB'),
    top=Side(style='medium', color='3498DB'),
    bottom=Side(style='medium', color='3498DB')
)
KPI_VALUE_FONT = Font(bold=True, size=20, color='2C3E50')
KPI_LABEL_FONT = Font(bold=False, size=10, color='7F8C8D')

# 섹션 헤더
SECTION_HEADER_FILL = PatternFill(start_color="34495E", end_color="34495E", fill_type="solid")
SECTION_HEADER_FONT = Font(bold=True, size=12, color="FFFFFF")
```

#### 8.2.2 🎬 소재 TIER 분석

**현재 문제점**:
- 컬럼이 많아 한 눈에 파악 어려움 (17개 컬럼)
- TIER 색상이 행 전체에 적용되어 과함
- 숫자 포맷이 일관되지 않음

**개선 설계**:

| 개선 항목 | 현재 | 변경 |
|---------|------|------|
| 컬럼 그룹화 | 평면 나열 | 핵심/상세/참고 그룹 |
| TIER 색상 | 행 전체 | TIER 셀만 + 연한 행 배경 |
| 숫자 정렬 | 혼합 | 모든 숫자 우측 정렬 |
| 행 높이 | 기본 | 20pt (가독성) |
| 컬럼 너비 | 자동 | 내용별 최적화 |

**컬럼 구조 개선**:

```
그룹 A - 핵심 (굵은 테두리)
┌──────┬────────┬────────┬─────┬─────┬─────┬──────┐
│ TIER │ 소재명  │ 소재유형│ CPA │ CTR │ CVR │랜딩률│
├──────┼────────┼────────┼─────┼─────┼─────┼──────┤
│TIER1 │ 끝내...│인플방문 │15006│0.78│7.0  │62.3  │
└──────┴────────┴────────┴─────┴─────┴─────┴──────┘

그룹 B - 상세 (일반 테두리)
┌────────┬────────┬────────┬────────┬───────┐
│ 총비용 │ 총전환 │ 총클릭 │집행일수│집행지점│
├────────┼────────┼────────┼────────┼───────┤
│586,932 │   39   │  555   │   20   │ 창원  │
└────────┴────────┴────────┴────────┴───────┘

그룹 C - 참고 (회색 배경)
┌──────────┬───────────┬──────────┐
│지점편중   │상대평가    │TIER 근거 │
├──────────┼───────────┼──────────┤
│창원 100% │창원:TOP    │CPA≤목표..│
└──────────┴───────────┴──────────┘
```

**숫자 포맷 규칙**:

| 컬럼 유형 | 포맷 | 예시 |
|---------|------|------|
| CPA, 비용 | #,##0 | 15,006 |
| CTR, CVR, 랜딩률 | 0.0% | 7.0% |
| 건수 | #,##0 | 39 |
| 일수 | 0 | 20 |

#### 8.2.3 🔄 훅 개선 효과

**현재 문제점**:
- 섹션 구분이 텍스트로만 되어 있음
- 변화율 양수/음수 색상 구분 없음
- 훅 판정 결과가 눈에 안 띔

**개선 설계**:

```
┌─────────────────────────────────────────────────────────────────┐
│ 🔍 정확 매칭 (동일 소재명)                                       │
├─────────┬────────┬───────────┬───────────┬───────────┬─────────┤
│ 소재유형 │ 소재명  │ CTR 변화  │ CVR 변화  │ CPA 변화  │ 훅 판정 │
├─────────┼────────┼───────────┼───────────┼───────────┼─────────┤
│의료진정보│ 주사형..│ ▼-25.4%  │ ▲+8.2%   │ ▼-12.3%  │ 부분효과│
│인플방문 │ 체지방..│ ▲+45.3%  │ ▲+15.1%  │ ▼-28.7%  │ 유효 ✓ │
└─────────┴────────┴───────────┴───────────┴───────────┴─────────┘

[변화율 양수: 초록 ▲ / 음수: 빨강 ▼ / CPA는 반대]
```

**훅 판정 스타일**:

| 판정 | 배경색 | 글자색 | 아이콘 |
|------|--------|--------|--------|
| 유효 | E8F5E9 | 2E7D32 | ✓ |
| 부분효과 | FFF3E0 | EF6C00 | △ |
| 효과없음 | FFEBEE | C62828 | ✗ |

#### 8.2.4 🏢 지점 컨텍스트

**개선 설계**:

```
┌─────────────────────────────────────────────────────────────┐
│  🏆 지점별 성과 순위 (CPA 기준 오름차순)                      │
├──────┬────────┬────────┬────────┬─────┬─────┬─────┬────────┤
│ 순위 │ 지점   │ 총비용  │ 총전환 │ CPA │ CTR │ CVR │ 평가   │
├──────┼────────┼────────┼────────┼─────┼─────┼─────┼────────┤
│ 🥇 1 │ 일산   │2.1M    │ 135   │15.6K│0.72│5.8  │ 최우수 │
│ 🥈 2 │ 서울   │3.8M    │ 208   │18.3K│0.68│5.2  │ 우수   │
│ 🥉 3 │ 부평   │2.9M    │ 115   │25.1K│0.58│4.1  │ 보통   │
│   4 │ 창원   │3.8M    │  95   │39.8K│0.45│3.2  │ 개선필요│
└──────┴────────┴────────┴────────┴─────┴─────┴─────┴────────┘
```

**대용량 숫자 표시**:

| 금액 범위 | 표시 | 예시 |
|---------|------|------|
| < 1,000,000 | 원 단위 | 586,932 |
| 1M ~ 1B | M 단위 | 3.8M |
| ≥ 1B | B 단위 | 1.2B |

#### 8.2.5 👥 나이대 분석

**개선 설계**:

```
┌────────────────────────────────────────────────────────────────┐
│  👥 나이대별 예산 효율 분석                                     │
├────────┬────────┬────────┬────────┬────────┬────────┬─────────┤
│ 나이대 │ 비용비중│ 전환비중│ 효율점수│  CPA   │  CTR   │ 판정   │
├────────┼────────┼────────┼────────┼────────┼────────┼─────────┤
│ 35-44  │ 38.2% │ 45.1% │  1.18  │ 22.1K │ 0.72% │ ✅ 우수 │
│ 45-54  │ 32.4% │ 35.8% │  1.10  │ 23.6K │ 0.65% │ ➡️ 양호 │
│ ≥55    │ 14.7% │ 11.4% │  0.78  │ 33.5K │ 0.48% │ ⬇️ 낮음 │
│ 25-34  │ 14.7% │  6.7% │  0.46  │ 57.2K │ 0.42% │ 🔴 비효율│
└────────┴────────┴────────┴────────┴────────┴────────┴─────────┘
```

**효율 판정 시각화**:

| 효율점수 | 판정 | 배경색 | 아이콘 |
|---------|------|--------|--------|
| ≥1.2 | 우수 | E8F5E9 | ✅ |
| 0.8~1.2 | 양호 | FFFFFF | ➡️ |
| 0.5~0.8 | 낮음 | FFF8E1 | ⬇️ |
| <0.5 | 비효율 | FFEBEE | 🔴 |

#### 8.2.6 📅 일별 트렌드

**개선 설계**:

```
┌─────────────────────────────────────────────────────────────────┐
│  📅 일별 성과 추이                                              │
├──────────┬────────┬────────┬────────┬─────────┬────────────────┤
│ 날짜     │ 비용   │ 전환   │  CPA   │CPA 변화  │ 트렌드 표시   │
├──────────┼────────┼────────┼────────┼─────────┼────────────────┤
│ 02-01    │ 485K  │   18  │ 26.9K │   -     │ ▁▁▁▁▁▁▁▁▁▁    │
│ 02-02    │ 523K  │   22  │ 23.8K │ -11.6%  │ ▂▂▂▂▂▂▂▂▂▂ ▼  │
│ 02-03    │ 612K  │   19  │ 32.2K │ +35.3%  │ ▆▆▆▆▆▆▆▆▆▆ ▲  │
│ ...      │       │       │       │         │               │
└──────────┴────────┴────────┴────────┴─────────┴────────────────┘
```

**스파크라인 표시**:

| 변화율 | 색상 | 막대 |
|--------|------|------|
| < -20% | 초록 | ▼▼ |
| -20% ~ 0% | 연초록 | ▼ |
| 0% ~ +20% | 연빨강 | ▲ |
| > +20% | 빨강 | ▲▲ |

#### 8.2.7 ⏸ OFF 소재

**개선 설계**:

```
┌─────────────────────────────────────────────────────────────────┐
│  ⏸ OFF 소재 (집행 종료)                                         │
│  마지막 성과 기록 보존용                                         │
├────────┬────────┬────────┬────────┬────────┬──────────────────┤
│ 소재명  │ 소재유형│  CPA   │  CTR   │마지막일│ 상태 / 사유     │
├────────┼────────┼────────┼────────┼────────┼──────────────────┤
│ 이전..  │의료진정보│ 45.2K │ 0.32% │ 02-15 │ 📴 성과 미달    │
│ 테스트..│인플방문 │ N/A   │ 0.18% │ 02-10 │ 📴 테스트 종료  │
└────────┴────────┴────────┴────────┴────────┴──────────────────┘
```

### 8.3 색상 체계

**Primary 색상**:

| 용도 | 색상 코드 | 예시 |
|------|----------|------|
| 헤더 배경 | #4472C4 | 파란색 |
| 섹션 제목 | #34495E | 진회색 |
| 강조 텍스트 | #2C3E50 | 어두운 파랑 |
| 보조 텍스트 | #7F8C8D | 회색 |

**TIER 색상 (기존 유지)**:

| TIER | 배경색 | 글자색 |
|------|--------|--------|
| TIER1 | #90EE90 | #155724 |
| TIER2 | #ADD8E6 | #004085 |
| TIER3 | #FFFFE0 | #856404 |
| TIER4 | #FFB6C1 | #721C24 |
| LOW_VOLUME | #D3D3D3 | #383D41 |
| UNCLASSIFIED | #E8E8E8 | #6C757D |

**상태 색상**:

| 상태 | 배경색 | 글자색 |
|------|--------|--------|
| 양수/개선 | #E8F5E9 | #2E7D32 |
| 중립 | #FFFFFF | #333333 |
| 음수/주의 | #FFEBEE | #C62828 |
| 경고 | #FFF8E1 | #F57C00 |

### 8.4 폰트 및 정렬

**폰트 크기 체계**:

| 요소 | 크기 | 굵기 | 용도 |
|------|------|------|------|
| 리포트 제목 | 18pt | Bold | 최상단 |
| 시트 제목 | 14pt | Bold | 각 시트 상단 |
| 섹션 제목 | 12pt | Bold | 섹션 구분 |
| 데이터 헤더 | 10pt | Bold | 테이블 헤더 |
| 데이터 본문 | 10pt | Regular | 일반 데이터 |
| 주석/참고 | 9pt | Regular | 부가 정보 |

**정렬 규칙**:

| 데이터 유형 | 가로 정렬 | 세로 정렬 |
|------------|----------|----------|
| 텍스트 | 좌측 | 중앙 |
| 숫자 | 우측 | 중앙 |
| 백분율 | 우측 | 중앙 |
| 상태/판정 | 중앙 | 중앙 |
| 날짜 | 중앙 | 중앙 |

### 8.5 행/열 규격

| 요소 | 높이/너비 | 비고 |
|------|----------|------|
| 헤더 행 높이 | 25pt | 가독성 확보 |
| 데이터 행 높이 | 20pt | 기본 |
| KPI 카드 행 높이 | 50pt | 강조 |
| TIER 컬럼 | 80px | 고정 |
| 소재명 컬럼 | 200px | 최소 |
| 숫자 컬럼 | 80px | 고정 |
| 비율 컬럼 | 60px | 고정 |

### 8.6 구현 코드 (build_excel.py 추가)

```python
# 새로운 스타일 상수 추가
KPI_CARD_FILL = PatternFill(start_color="EBF5FB", end_color="EBF5FB", fill_type="solid")
KPI_CARD_BORDER = Border(
    left=Side(style='medium', color='3498DB'),
    right=Side(style='medium', color='3498DB'),
    top=Side(style='medium', color='3498DB'),
    bottom=Side(style='medium', color='3498DB')
)
KPI_VALUE_FONT = Font(bold=True, size=20, color='2C3E50')
KPI_LABEL_FONT = Font(bold=False, size=10, color='7F8C8D')

SECTION_HEADER_FILL = PatternFill(start_color="34495E", end_color="34495E", fill_type="solid")
SECTION_HEADER_FONT = Font(bold=True, size=12, color="FFFFFF")

# 상태 색상
STATUS_COLORS = {
    'positive': PatternFill(start_color="E8F5E9", end_color="E8F5E9", fill_type="solid"),
    'negative': PatternFill(start_color="FFEBEE", end_color="FFEBEE", fill_type="solid"),
    'warning': PatternFill(start_color="FFF8E1", end_color="FFF8E1", fill_type="solid"),
    'neutral': PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid"),
}

def apply_number_alignment(ws, start_row=2):
    """숫자 컬럼 우측 정렬 자동 적용"""
    for row in ws.iter_rows(min_row=start_row, max_row=ws.max_row):
        for cell in row:
            if isinstance(cell.value, (int, float)):
                cell.alignment = Alignment(horizontal='right', vertical='center')
            elif isinstance(cell.value, str):
                cell.alignment = Alignment(horizontal='left', vertical='center')

def set_row_heights(ws, header_height=25, data_height=20):
    """행 높이 설정"""
    ws.row_dimensions[1].height = header_height
    for row_num in range(2, ws.max_row + 1):
        ws.row_dimensions[row_num].height = data_height

def format_change_rate(value):
    """변화율 포맷팅 (▲/▼ 아이콘 포함)"""
    if pd.isna(value) or value == '':
        return ''
    if value > 0:
        return f"▲+{value:.1f}%"
    elif value < 0:
        return f"▼{value:.1f}%"
    else:
        return "0.0%"

def apply_change_rate_colors(ws, col_idx, start_row=2, reverse=False):
    """변화율 셀에 색상 적용 (CPA는 reverse=True)"""
    green_font = Font(color='2E7D32')
    red_font = Font(color='C62828')

    for row in ws.iter_rows(min_row=start_row, max_row=ws.max_row):
        cell = row[col_idx - 1]
        value = cell.value
        if value and isinstance(value, str):
            if '▲' in value:
                cell.font = red_font if reverse else green_font
            elif '▼' in value:
                cell.font = green_font if reverse else red_font
```

---

## 9. 검증 기준 (DoD)

### 8.1 v3.1.0 완료 기준

- [ ] 시트명 7개 모두 이모지 포함
- [ ] analysis_raw.json 생성됨
- [ ] JSON 파싱 오류 없음
- [ ] QA 12/12 유지

### 8.2 v3.2.0 완료 기준

- [ ] 레이더 차트 정상 렌더링
- [ ] 피로도 차트 정상 렌더링
- [ ] CPA 목표선 조건부 표시
- [ ] QA 12/12 유지

### 8.3 v3.3.0 완료 기준

- [ ] hooks 자동 실행
- [ ] lineage 매핑 정상 작동
- [ ] 기존 기능 회귀 없음

---

*이 Design 문서는 `/pdca do tiktok-redesign` 명령으로 구현 단계로 진행할 수 있습니다.*
