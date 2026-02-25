# TikTok 광고 분석 자동화 — 프로젝트 설계 최종 지시서

> 클라이언트: 다이트한의원  
> 캠페인 목적: 예약 상담 전환 (소재 관점 분석 특화)  
> 작성 기준: 대화 기반 설계 + 실제 데이터 검증 + 외부 코드리뷰 통합  

---

## 0. 핵심 설계 원칙

### 통제 가능 vs 불가능 영역 분리

```
[광고로 컨트롤 가능] ← 분석의 핵심
  소재 CTR / CVR / CPA / 랜딩도달률 / TIER 분류 / 예산 배분

[광고로 컨트롤 불가능] ← 지점 컨텍스트 패널로만 표시
  매체DB → 실제DB 전환율  (상담실장 역량)
  ROAS / 내원율           (지점 고객층 / 수납 역량)
```

### 절대 금지 규칙

```
1. raw CTR/CVR/CPA 컬럼으로 분석 금지 → 반드시 _calc 재계산값 사용
2. 클릭=0이면서 전환>0인 행의 행 단위 CVR 계산 금지
3. 파싱 실패(parse_status=FAIL) 소재 TIER 분류 금지
4. 볼륨 미달(클릭<100 AND 비용<100,000원) 소재 TIER 분류 금지
5. 지점 편중 소재 수치 보정 금지 → 주석으로 맥락 표시
6. 소재 TIER 평가를 일별×나이대 행 단위로 수행 금지
   → 반드시 소재 단위 집계 후 TIER 부여
```

---

## 1. 데이터 구조 설계

### 1-1. 입력 데이터 (input/)

| 파일 | 출처 | 필수여부 | 핵심 컬럼 |
|------|------|:-------:|-----------|
| `tiktok_raw.csv` | 틱톡 광고 매니저 | ✅ 필수 | 광고명, 일별, 나이, 비용, 전환수 등 |
| `db_by_branch.csv` | 내부 CRM | 선택 | 지점, 날짜, 매체DB, 실제DB, 내원율, ROAS |
| `target_cpa.csv` | 수동 관리 | 선택 | 지점, 목표CPA |
| `creative_lineage.csv` | 수동 관리 | 선택(2단계) | 원본소재명, 재가공소재명, 변경요소 |

> ℹ️ OFF 소재 구분은 별도 파일 없이 광고명 파싱으로 자동 처리 (아래 1-2 참고)  
> 선택 파일 없을 때: 해당 모듈 스킵 후 가능한 범위로 진행. 없으면 전체 평균값으로 대체.

### 1-2. 광고명 파싱 규칙

```
패턴 (ON):  (신/재)_지점_소재유형_소재명_날짜코드
패턴 (OFF): (신/재)_지점_소재유형_소재명_날짜코드_off

예시:
  (신)_서울_의료진정보_주사형비만치료제 10년은_260116      → ON
  (신)_서울_의료진정보_주사형비만치료제 10년은_260116_off  → OFF

추출 항목:
  소재구분  → (신) = 신규 소재
               (재) = 재가공 소재 (원본 영상 동일, 썸네일/초기카피(훅)만 변경)
  지점      → 서울 / 부평 / 수원 / 대구 / 창원 / 천안 / 일산
  소재유형  → 인플방문후기 / 진료셀프캠 / 의료진정보
  소재명    → 핵심 창의물 이름 (날짜코드 제외)
  날짜코드  → 5~6자리 허용 (260220 또는 26120 모두 처리)
  is_off    → 광고명 끝이 '_off'이면 True, 아니면 False
               (대소문자 무관: _OFF, _Off 모두 처리)
  매칭키    → 소재유형_소재명 (훅 쌍 매칭에 사용)

파싱 품질 평가:
  parse_status = OK / FAIL
  parse_issue  = UNKNOWN_BRANCH / UNKNOWN_TYPE / SHORT_CREATIVE_NAME
  → FAIL 소재는 분석 제외, parse_failures.csv에 로그 저장

OFF 파싱 코드:
  # _off 감지 후 제거하고 나머지 파싱
  is_off = name.lower().endswith('_off')
  clean_name = name[:-4] if is_off else name  # '_off' 4글자 제거
  parts = clean_name.split('_')
  # 이후 기존 파싱 로직 동일
```

**유효값 목록 (파싱 기준)**
```python
VALID_BRANCHES = ['부평', '서울', '수원', '대구', '창원', '천안', '일산']
VALID_AD_TYPES = ['인플방문후기', '진료셀프캠', '의료진정보']
```

### 1-3. 신규 ↔ 재가공 소재 쌍 매칭 규칙

```
재가공(재) 소재의 특성:
  - 원본 영상은 동일
  - 썸네일 또는 초기 카피(훅)만 변경
  → CTR 변화 = 훅 효과를 가장 직접적으로 측정

매칭 방식 (2단계):

A. Strict 매칭 (우선)
   매칭 키 = 소재유형 + 소재명 완전 일치
   → 지점이 달라도 소재유형+소재명이 같으면 동일 소재

B. 소재유형 집계 비교 (Strict 매칭 실패 시)
   → "인플방문후기 신규" vs "인플방문후기 재가공" 집계 단위 비교
   → 현재 데이터 구조상 소재명 자체가 바뀌는 재가공이 많으므로
      이 방식이 실질적으로 더 유용

C. creative_lineage.csv 도입 (2단계 고도화)
   → 사람이 직접 원본↔재가공 관계 매핑
   → 컬럼: creative_group_id, 원본소재명, 재가공소재명, 변경요소
```

---

## 2. 프로젝트 디렉토리 구조

```
tiktok-report-automation/
│
├── CLAUDE.md                          ← 오케스트레이터 (전체 워크플로우 지휘)
│
├── .claude/
│   └── hooks/
│       ├── pre-run.sh                 ← 입력파일 유효성 검사
│       ├── post-analysis.sh           ← 분석 완료 후 리포트 트리거
│       └── auto-approve.sh            ← 읽기/계산 작업 자동 승인
│
├── skills/
│   ├── tiktok-normalizer/             ← Phase 0: raw 표준화 (신규 핵심)
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       └── normalize_tiktok_raw.py
│   │
│   ├── tiktok-parser/                 ← Phase 1: 파싱 + 메타데이터 추출
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       ├── parse_tiktok.py        ← 광고명 파싱 + parse_status
│   │       └── validate_input.py      ← 컬럼 검증 + 구조화 JSON 출력
│   │
│   ├── creative-analyzer/             ← Phase 2: 소재 다차원 평가 ⭐ 핵심
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       ├── score_creatives.py     ← 소재 집계 + TIER 분류
│   │       ├── hook_comparison.py     ← 신규↔재가공 훅 효과 비교
│   │       └── detect_anomalies.py    ← 이상치 감지
│   │
│   ├── funnel-analyzer/               ← Phase 2: 매체DB + 내부DB 퍼널
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       └── merge_db.py
│   │
│   ├── report-generator/              ← Phase 5: Excel + PDF 생성
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       ├── build_excel.py
│   │       └── build_pdf.py
│   │
│   └── insight-writer/                ← Phase 3: AI 인사이트 생성
│       ├── SKILL.md
│       └── prompts/
│           ├── creative_insight.txt
│           ├── hook_insight.txt
│           └── branch_insight.txt
│
├── agents/
│   ├── analysis-agent.md              ← KPI 계산 + TIER 분류
│   ├── hook-agent.md                  ← 훅 쌍 매칭 + 비교
│   ├── insight-agent.md               ← 인사이트 문장 생성
│   ├── anomaly-agent.md               ← 이상치 감지
│   └── qa-agent.md                    ← 결과물 검증
│
├── input/                             ← 입력 데이터 드롭 폴더
├── output/YYYYMMDD/                   ← 생성 리포트 저장
├── templates/                         ← Excel/PDF 템플릿
└── logs/                              ← 실행 로그 + 파싱 실패 기록
```

---

## 3. CLAUDE.md 설계 (오케스트레이터)

```markdown
# 다이트한의원 TikTok 광고 분석 오케스트레이터

## 실행 조건
input/tiktok_raw.csv 존재 시 실행.
나머지 파일은 있으면 활용, 없으면 해당 모듈 스킵.

## 실행 워크플로우

### Phase 0 — raw 표준화 (동기, 순차) ← 반드시 첫 번째
tiktok-normalizer 스킬 실행:
  normalize_tiktok_raw.py → output/normalized.parquet 생성
  
  수행 내용:
  - 광고 ID 문자열 강제 로딩 (지수 표기 방지)
  - 컬럼명 표준화 (TikTok export 버전 차이 대응)
  - KPI 재계산: CTR_calc / CVR_calc / CPA_calc / LPV_rate_calc
    (raw 비율 컬럼은 참고용 보존, 이후 계산엔 _calc만 사용)
  - attribution_caution 플래그 생성 (클릭=0 AND 전환>0)
  - 날짜 파싱, 통화 단일값 확인, 중복 행 감지

### Phase 1 — 데이터 준비 (동기, 순차)
1. pre-run.sh → 필수 파일 확인 + 기본 검증
2. tiktok-parser 스킬:
   - 광고명 파싱 (소재구분/지점/소재유형/소재명/날짜코드)
   - parse_status = OK / FAIL 판정
   - FAIL 소재 → logs/parse_failures.csv 저장 후 분석 제외
   - 신규↔재가공 매칭키 생성 (소재유형_소재명)
3. validate_input.py → 검증 결과를 validation_report.json으로 저장

### Phase 2 — 병렬 분석 (서브에이전트 동시 실행)
use subagents:
  - analysis-agent : 소재 단위 집계 + TIER 분류
  - hook-agent     : 신규↔재가공 훅 효과 비교
  - anomaly-agent  : 이상치 감지
  - funnel-agent   : 퍼널 분석 (db_by_branch.csv 있을 때만)

### Phase 3 — 인사이트 생성
insight-agent: Phase 2 결과 기반 인사이트 생성
  형식: 수치 근거 → 해석 → 액션 제안
  등급: 확정 인사이트(표본 충분) / 가설 인사이트(표본 부족)

### Phase 4 — QA 검증 (동기)
qa-agent 체크리스트:
  □ raw 총비용 = 분석 총비용 일치
  □ raw 총전환 = 분석 총전환 일치
  □ CPA_calc = 비용/전환 재검증
  □ CVR raw 단위 혼재 감지 시 경고
  □ TIER 평가 대상에 7일 미만 / 볼륨 미달 소재 없는지 확인
  □ OFF 소재 보존 여부

### Phase 5 — 리포트 생성 (동기)
report-generator 스킬 → Excel + PDF → output/YYYYMMDD/ 저장

## 규칙
- 모든 수치 계산은 scripts/로만 실행 (직접 계산 금지)
- 소재 TIER 분류는 소재 단위 집계 후에만 수행 (행 단위 금지)
- 지점 편중 소재: 수치 보정 금지, 주석으로 맥락 표시
- OFF 소재: 별도 시트 분리, 마지막 성과 보존
- 재가공 쌍 없으면 소재유형 집계 비교로 대체
- target_cpa.csv 없으면 전체 중앙값 CPA로 대체
- CLAUDE.md 자동 업데이트: 파서 패턴 오류만 허용
  분석 로직 변경 제안 → output/YYYYMMDD/improvement_suggestions.md에만 저장
```

---

## 4. Phase 0: normalize_tiktok_raw.py 전체 코드

```python
import pandas as pd
import numpy as np

def normalize(input_path: str, output_path: str):

    # 1. 광고 ID 문자열 강제 로딩 (지수 표기 정밀도 손실 방지)
    df = pd.read_csv(input_path, dtype={'광고 ID': str})

    # 2. 컬럼명 표준화
    COLUMN_ALIAS = {
        '클릭수(목적지)': 'clicks',
        '노출수':        'impressions',
        '전환수':        'conversions',
        '비용':          'cost',
        '랜딩 페이지 조회(웹사이트)': 'landing_views',
        '일별':          'date',
        '나이':          'age_group',
        '광고 이름':     'ad_name',
        '광고 ID':       'ad_id',
        '도달':          'reach',
        '동영상 조회수': 'video_views',
    }
    df = df.rename(columns={k: v for k, v in COLUMN_ALIAS.items() if k in df.columns})

    # 3. 숫자형 강제 변환
    NUM_COLS = ['clicks', 'impressions', 'conversions', 'cost', 'landing_views', 'reach']
    for col in NUM_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(',', ''), errors='coerce'
            ).fillna(0)

    # 4. KPI 재계산 (_calc 컬럼만 이후 분석에 사용)
    df['CTR_calc']      = (df['clicks'] / df['impressions'].replace(0, np.nan) * 100).round(4)
    df['CVR_calc']      = (df['conversions'] / df['clicks'].replace(0, np.nan) * 100).round(4)
    df['CPA_calc']      = (df['cost'] / df['conversions'].replace(0, np.nan)).round(0)
    df['LPV_rate_calc'] = (df['landing_views'] / df['clicks'].replace(0, np.nan) * 100).round(4)
    # raw 비율 컬럼은 참고용으로 보존 (분석에 사용 금지)

    # 5. 귀속 주의 플래그 (클릭=0 AND 전환>0 → 뷰스루/지연 전환 추정)
    df['attribution_caution'] = (df['clicks'] == 0) & (df['conversions'] > 0)
    n_caution = df['attribution_caution'].sum()
    if n_caution > 0:
        print(f"[WARNING] attribution_caution {n_caution}건 감지 (클릭=0/전환>0)")

    # 6. 날짜 파싱
    df['date'] = pd.to_datetime(df['date'], errors='coerce')

    # 7. 통화 단일값 확인
    if '통화' in df.columns:
        currencies = df['통화'].unique()
        if len(currencies) > 1:
            print(f"[WARNING] 통화 혼재 감지: {currencies}")

    # 8. 중복 행 감지
    dup_key = ['ad_id', 'date', 'age_group']
    if all(k in df.columns for k in dup_key):
        dupes = df[df.duplicated(dup_key, keep=False)]
        if len(dupes) > 0:
            print(f"[WARNING] 중복 행 {len(dupes)}건 감지")

    # 9. 저장
    df.to_parquet(output_path, index=False)
    print(f"[OK] 표준화 완료: {len(df)}행 → {output_path}")
    return df
```

---

## 5. Phase 2: score_creatives.py 핵심 로직

### 5-0. ON/OFF 소재 분리 (집계 전 첫 번째 단계)

```python
# parse_tiktok.py에서 is_off 컬럼이 생성된 상태
# OFF 소재는 분석 대상에서 제외하고 별도 처리

df_on  = df_valid[df_valid['is_off'] == False].copy()  # TIER 분류 대상
df_off = df_valid[df_valid['is_off'] == True].copy()   # ⏸ OFF 소재 시트용

# OFF 소재: 마지막 성과만 보존 (TIER 분류 안 함)
creative_off = df_off.groupby(['소재구분', '소재유형', '소재명']).agg(
    집행지점목록    = ('지점', lambda x: sorted(x.unique().tolist())),
    총비용          = ('cost', 'sum'),
    총전환          = ('conversions', 'sum'),
    총클릭          = ('clicks', 'sum'),
    총노출          = ('impressions', 'sum'),
    마지막집행일    = ('date', 'max'),
    집행일수        = ('date', 'nunique'),
).reset_index()

creative_off['CPA']    = (creative_off['총비용'] / creative_off['총전환'].replace(0, np.nan)).round(0)
creative_off['CTR']    = (creative_off['총클릭'] / creative_off['총노출'].replace(0, np.nan) * 100).round(2)
creative_off['CVR']    = (creative_off['총전환'] / creative_off['총클릭'].replace(0, np.nan) * 100).round(2)
creative_off['상태']   = 'OFF'

# 이후 df_on만 사용하여 TIER 분류 진행
# df_off는 build_excel.py에서 ⏸ OFF 소재 시트에 출력
```

### 5-1. 소재 단위 집계

```python
import pandas as pd
import numpy as np

# ─────────────────────────────────────────
# STEP 1: 소재 단위 집계
# 일별×나이대 raw 행 → 소재 단위로 합산
# ─────────────────────────────────────────
# ✅ 집계 단위: 소재구분 + 소재유형 + 소재명 (지점/날짜코드 미포함)
# ❌ 금지: 광고명 전체 또는 광고ID 단위 집계 (지점별로 쪼개짐)

GROUP_KEY = ['소재구분', '소재유형', '소재명']

creative_df = df_valid.groupby(GROUP_KEY).agg(
    집행지점목록    = ('지점', lambda x: sorted(x.unique().tolist())),
    집행지점분포    = ('지점', lambda x: x.value_counts().to_dict()),
    집행지점수      = ('지점', 'nunique'),
    총비용          = ('cost', 'sum'),
    총전환          = ('conversions', 'sum'),
    총클릭          = ('clicks', 'sum'),
    총노출          = ('impressions', 'sum'),
    총랜딩          = ('landing_views', 'sum'),
    집행일수        = ('date', 'nunique'),       # 비용>0인 distinct 날짜 수
    귀속주의건수    = ('attribution_caution', 'sum'),
    매칭키          = ('매칭키', 'first'),
).reset_index()

# STEP 2: KPI 재계산 (집계 후 재계산 — 행 단위 CVR 사용 금지)
creative_df['CPA']    = (creative_df['총비용'] / creative_df['총전환'].replace(0, np.nan)).round(0)
creative_df['CTR']    = (creative_df['총클릭'] / creative_df['총노출'].replace(0, np.nan) * 100).round(2)
creative_df['CVR']    = (creative_df['총전환'] / creative_df['총클릭'].replace(0, np.nan) * 100).round(2)
creative_df['랜딩률'] = (creative_df['총랜딩'] / creative_df['총클릭'].replace(0, np.nan) * 100).round(1)
```

### 5-2. TIER 분류

```python
# ─────────────────────────────────────────
# 기준선 계산 (평가 가능 소재만 사용)
# ─────────────────────────────────────────
def is_evaluable(row):
    """TIER 평가 가능 여부: 집행일수 7일 이상 + 볼륨 조건 충족"""
    day_ok    = row['집행일수'] >= 7
    volume_ok = (row['총클릭'] >= 100) or (row['총비용'] >= 100_000)
    return day_ok and volume_ok

creative_df['평가가능'] = creative_df.apply(is_evaluable, axis=1)

# 기준선: 평가 가능 소재 기준으로만 계산
evaluable = creative_df[creative_df['평가가능']]
AVG_CTR     = evaluable['CTR'].mean()
AVG_LANDING = evaluable['랜딩률'].mean()

# 목표 CPA 로드
try:
    target_df = pd.read_csv('input/target_cpa.csv')
    TARGET_CPA_MAP = dict(zip(target_df['지점'], target_df['목표CPA']))
    def get_target_cpa(지점목록):
        cpas = [TARGET_CPA_MAP.get(b) for b in 지점목록 if TARGET_CPA_MAP.get(b)]
        return sum(cpas) / len(cpas) if cpas else evaluable['CPA'].median()
except FileNotFoundError:
    GLOBAL_TARGET_CPA = evaluable['CPA'].median()
    def get_target_cpa(지점목록):
        return GLOBAL_TARGET_CPA
    print(f"[INFO] target_cpa.csv 없음 → 중앙값 CPA {GLOBAL_TARGET_CPA:,.0f}원 적용")

# ─────────────────────────────────────────
# TIER 분류 함수
# ─────────────────────────────────────────
def classify_tier(row):

    # 게이트 1: 집행일수 7일 미만
    if row['집행일수'] < 7:
        return 'UNCLASSIFIED'

    # 게이트 2: 볼륨 미달 (집행일수 충족, 데이터 부족)
    if not row['평가가능']:
        return 'LOW_VOLUME'

    target_cpa = get_target_cpa(row['집행지점목록'])

    cpa_ok  = pd.notna(row['CPA'])  and row['CPA']  <= target_cpa
    cvr_ok  = pd.notna(row['CVR'])  and row['CVR']  >= 5.0
    ctr_ok  = pd.notna(row['CTR'])  and row['CTR']  >= AVG_CTR * 1.2
    land_ok = pd.notna(row['랜딩률']) and row['랜딩률'] >= AVG_LANDING * 1.1

    # 순서 중요: if/elif 순차 처리
    if cpa_ok and cvr_ok:
        return 'TIER1'
    elif ctr_ok and not cpa_ok:
        return 'TIER2'
    elif land_ok and not cvr_ok:
        return 'TIER3'
    else:
        return 'TIER4'

creative_df['TIER'] = creative_df.apply(classify_tier, axis=1)

# ─────────────────────────────────────────
# TIER 근거 문장 생성
# ─────────────────────────────────────────
def tier_reason(row):
    if row['TIER'] == 'TIER1':
        return f"CPA({row['CPA']:,.0f}원) ≤ 목표 AND CVR({row['CVR']:.1f}%) ≥ 5%"
    elif row['TIER'] == 'TIER2':
        return f"CTR({row['CTR']:.2f}%) ≥ 평균×1.2 / CPA 목표 초과"
    elif row['TIER'] == 'TIER3':
        return f"랜딩률({row['랜딩률']:.1f}%) ≥ 평균×1.1 / CVR 5% 미달"
    elif row['TIER'] == 'TIER4':
        return "CTR·CPA·랜딩률 모두 평균 이하"
    elif row['TIER'] == 'LOW_VOLUME':
        return f"클릭 {row['총클릭']}건 / 비용 {row['총비용']:,.0f}원 — 표본 부족"
    else:
        return f"집행 {row['집행일수']}일 — 데이터 누적 중"

creative_df['TIER_근거'] = creative_df.apply(tier_reason, axis=1)
```

### 5-3. 지점 편중 주석

```python
# 지점별 현재 데이터 기준 평균 CPA (target_cpa.csv 없을 때 참고)
BRANCH_AVG_CPA = {
    '서울': 15648, '일산': 15962, '대구': 22570,
    '천안': 32649, '부평': 34451, '수원': 42646, '창원': 48417
}

def branch_note(row):
    """특정 지점 70% 이상 집중 집행 시 주석 생성"""
    d = row['집행지점분포']
    if not d:
        return None
    total = sum(d.values())
    dominant = max(d, key=d.get)
    ratio = d[dominant] / total * 100
    if ratio >= 70:
        avg = BRANCH_AVG_CPA.get(dominant)
        note = f"⚠️ {dominant} {ratio:.0f}% 집중 집행"
        if avg:
            note += f" (해당 지점 평균 CPA {avg:,}원 참고)"
        return note
    return None

creative_df['지점편중주석'] = creative_df.apply(branch_note, axis=1)
```

### 5-4. 지점별 상대 평가 (Branch-relative Flag)

```python
def branch_relative_flag(row, branch_cpa_by_creative: dict):
    """
    같은 소재라도 지점에 따라 성과가 크게 다를 수 있음.
    각 지점에서의 소재 성과를 해당 지점 평균 대비로 평가.
    
    branch_cpa_by_creative: {소재명: {지점: CPA}} 형태의 사전
    """
    소재 = row['소재명']
    flags = []
    if 소재 in branch_cpa_by_creative:
        for 지점, cpa in branch_cpa_by_creative[소재].items():
            avg = BRANCH_AVG_CPA.get(지점)
            if avg and pd.notna(cpa):
                ratio = cpa / avg
                if ratio <= 0.7:
                    flags.append(f"✅ {지점} TOP (평균의 {ratio:.0%})")
                elif ratio >= 1.5:
                    flags.append(f"🔴 {지점} WORST (평균의 {ratio:.0%})")
    return " | ".join(flags) if flags else None

# 소재×지점 CPA 집계 (Layer 2)
branch_creative_df = df_valid.groupby(['소재명', '지점']).agg(
    총비용=('cost', 'sum'),
    총전환=('conversions', 'sum'),
).reset_index()
branch_creative_df['CPA'] = (
    branch_creative_df['총비용'] / branch_creative_df['총전환'].replace(0, np.nan)
).round(0)

branch_cpa_map = branch_creative_df.groupby('소재명').apply(
    lambda x: dict(zip(x['지점'], x['CPA']))
).to_dict()

creative_df['지점별_상대평가'] = creative_df.apply(
    lambda r: branch_relative_flag(r, branch_cpa_map), axis=1
)
```

---

## 6. Phase 2: hook_comparison.py

```python
def match_hook_pairs(creative_df):
    신규 = creative_df[creative_df['소재구분'] == '신규']
    재가공 = creative_df[creative_df['소재구분'] == '재가공']

    # A. Strict 매칭 (소재유형 + 소재명 완전 일치)
    strict_pairs = 신규.merge(
        재가공, on=['소재유형', '소재명'],
        suffixes=('_신규', '_재가공')
    )
    strict_pairs['match_type'] = 'strict'

    # B. 소재유형 집계 비교 (Strict 매칭 건수 보완용)
    type_comparison = creative_df.groupby(['소재유형', '소재구분']).agg(
        소재수=('소재명', 'count'),
        총비용=('총비용', 'sum'),
        총전환=('총전환', 'sum'),
        avg_CTR=('CTR', 'mean'),
        avg_CVR=('CVR', 'mean'),
        avg_CPA=('CPA', 'mean'),
        avg_랜딩률=('랜딩률', 'mean'),
    ).reset_index()

    return strict_pairs, type_comparison

def hook_verdict(orig_ctr, re_ctr, orig_cvr, re_cvr):
    ctr_up = re_ctr > orig_ctr
    cvr_up = re_cvr > orig_cvr
    if ctr_up and cvr_up:
        return '재가공 유효 — 클릭·전환 모두 개선'
    elif ctr_up and not cvr_up:
        return '부분 효과 — 클릭↑ 전환↓ (랜딩 불일치 가능성)'
    else:
        return '재가공 효과 없음 — 원본 훅 복귀 검토'
```

---

## 7. Phase 2: 나이대 분석 (예산 효율 점수 기반)

```python
# 캠페인 타겟: 전 지점 25~55+ 여성 → 25-34는 이상치가 아닌 저효율 타겟
# 분석 방향: 이상치 감지 아님 → 예산 대비 전환 효율 분석

VALID_AGE_GROUPS = ['25-34', '35-44', '45-54', '≥55']

df_age = df_valid[df_valid['age_group'].isin(VALID_AGE_GROUPS)].copy()

age_summary = df_age.groupby('age_group').agg(
    총비용    = ('cost', 'sum'),
    총전환    = ('conversions', 'sum'),
    총클릭    = ('clicks', 'sum'),
    총노출    = ('impressions', 'sum'),
    귀속주의  = ('attribution_caution', 'sum'),
).reset_index()

total_cost = age_summary['총비용'].sum()
total_conv = age_summary['총전환'].sum()

age_summary['비용비중']   = (age_summary['총비용'] / total_cost * 100).round(1)
age_summary['전환비중']   = (age_summary['총전환'] / total_conv * 100).round(1)
age_summary['CPA']        = (age_summary['총비용'] / age_summary['총전환'].replace(0, np.nan)).round(0)
age_summary['CTR']        = (age_summary['총클릭'] / age_summary['총노출'].replace(0, np.nan) * 100).round(2)

# 핵심 지표: 예산 효율 점수
# 1.0 이상 → 비용 대비 전환을 더 뽑아냄 (효율 우수)
# 1.0 미만 → 비용 대비 전환 부족 (효율 낮음)
age_summary['예산효율점수'] = (age_summary['전환비중'] / age_summary['비용비중']).round(2)

def age_efficiency_label(score):
    if pd.isna(score): return None
    if score >= 1.2:   return '✅ 효율 우수 — 비중 확대 검토'
    elif score >= 0.8: return '➡️ 양호'
    elif score >= 0.5: return '⬇️ 효율 낮음 — 소재/타겟 최적화 검토'
    else:              return '🔴 비효율 — 해당 나이대 맞춤 소재 개발 필요'

age_summary['효율판정'] = age_summary['예산효율점수'].apply(age_efficiency_label)
age_summary['신뢰도주의'] = age_summary['귀속주의'].apply(
    lambda n: f"⚠️ 귀속 주의 {n}건 포함" if n > 0 else None
)

# 소재유형 × 나이대 히트맵 (소재 개발 인사이트용)
pivot_ctr = df_age.pivot_table(
    index='소재유형', columns='age_group',
    values='CTR_calc', aggfunc='mean'
).round(2)

pivot_cvr = df_age.pivot_table(
    index='소재유형', columns='age_group',
    values='CVR_calc', aggfunc='mean'
).round(2)
```

---

## 8. 리포트 출력 구조

### 8-1. 필요 라이브러리

```bash
pip install openpyxl matplotlib seaborn --break-system-packages
```

| 라이브러리 | 역할 |
|-----------|------|
| `openpyxl` | Excel 파일 생성 + 기본 차트 (도넛, 막대) |
| `matplotlib` | 복잡한 차트 이미지 생성 (버블, 콤보, 라인) |
| `seaborn` | 히트맵 (소재유형 × 나이대) |
| `io` | 이미지 버퍼 — 파일 저장 없이 Excel에 직접 삽입 |

**한글 폰트 설정 (build_charts.py 최상단 필수)**
```python
import matplotlib.pyplot as plt
plt.rcParams['font.family']       = 'NanumGothic'   # Linux
# plt.rcParams['font.family']     = 'AppleGothic'   # macOS
# plt.rcParams['font.family']     = 'Malgun Gothic' # Windows
plt.rcParams['axes.unicode_minus'] = False           # 마이너스 기호 깨짐 방지
```

---

### 8-2. 차트 목록 (시트별 배치)

| # | 차트명 | 시트 | 유형 | 목적 |
|:-:|--------|------|:----:|------|
| 1 | TIER 분포 도넛 | 📊 요약 대시보드 | Donut | TIER별 소재 수/비중 한눈에 파악 |
| 2 | 지점별 CPA 가로막대 | 📊 요약 대시보드 | Bar(H) | 지점 간 효율 격차 · 목표CPA 기준선 |
| 3 | 소재유형 레이더 | 📊 요약 대시보드 | Radar | CTR/CVR/CPA/랜딩률 4지표 종합 비교 |
| 4 | 소재 버블 차트 | 🎬 소재 TIER 분석 | Bubble | CTR×CVR×비용 3차원 비교 — 예산 확대/축소 판단 |
| 5 | 소재유형별 CPA 분포 | 🎬 소재 TIER 분석 | Bar | 유형별 최소/평균/최대 CPA 분포 |
| 6 | 훅 전후 비교 막대 | 🔄 훅 개선 효과 | Bar(grouped) | 신규↔재가공 CTR/CVR/CPA 변화율 (±%) |
| 7 | 나이대 비용vs전환 | 👥 나이대 분석 | Bar(grouped) | 비용비중 vs 전환비중 격차 = 비효율 구간 시각화 |
| 8 | 나이대 효율 점수 | 👥 나이대 분석 | Bar | 효율점수 + 균형선(1.0) 표시 |
| 9 | 소재유형×나이대 히트맵 | 👥 나이대 분석 | Heatmap | CTR/CVR 패턴 색상 — 소재 개발 인사이트 |
| 10 | 일별 비용+전환 콤보 | 📅 일별 트렌드 | Line+Bar | 예산 리듬 vs 전환 발생 이중축 |
| 11 | 일별 CTR 라인 | 📅 일별 트렌드 | Line | 소재 피로도 감지 · 평균선 기준 |

---

### 8-3. 차트 색상 규칙 (전 시트 통일)

```python
TIER_COLORS = {
    'TIER1':       '#10b981',   # 초록
    'TIER2':       '#3b82f6',   # 파랑
    'TIER3':       '#f59e0b',   # 주황
    'TIER4':       '#ef4444',   # 빨강
    'LOW_VOLUME':  '#9ca3af',   # 회색
    'UNCLASSIFIED':'#a78bfa',   # 보라
}

# CPA 기반 색상 (지점/소재 공통)
def cpa_color(cpa, target):
    if cpa <= target:           return '#10b981'  # 목표 달성: 초록
    elif cpa <= target * 1.3:   return '#f59e0b'  # 근접: 주황
    else:                       return '#ef4444'  # 초과: 빨강
```

---

### 8-4. 핵심 차트 구현 코드

**차트 4: 소재 버블 차트** (가장 정보량이 많은 핵심 차트)
```python
def add_creative_bubble_chart(ws, creative_df, anchor_cell="A35"):
    """
    X축: CTR(%) · Y축: CVR(%) · 버블 크기: 총비용
    색상: TIER별 · 라벨: 소재명(10자 이내)
    평균 CTR/CVR 기준선 십자 표시
    사분면 레이블: 우상단=이상적 / 좌하단=제거검토
    """
    eval_df = creative_df[creative_df['TIER'].isin(['TIER1','TIER2','TIER3','TIER4'])
                         ].dropna(subset=['CTR','CVR'])
    fig, ax = plt.subplots(figsize=(14, 8))
    for tier, group in eval_df.groupby('TIER'):
        sizes = (group['총비용'] / group['총비용'].max() * 1500).clip(lower=100)
        ax.scatter(group['CTR'], group['CVR'], s=sizes,
                  c=TIER_COLORS[tier], alpha=0.7, label=tier,
                  edgecolors='white', linewidth=0.8)
        for _, row in group.iterrows():
            label = row['소재명'][:10] + '…' if len(row['소재명']) > 10 else row['소재명']
            ax.annotate(label, (row['CTR'], row['CVR']),
                       textcoords="offset points", xytext=(5,5), fontsize=7)
    # 기준선 + 사분면
    avg_ctr, avg_cvr = eval_df['CTR'].mean(), eval_df['CVR'].mean()
    ax.axvline(avg_ctr, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)
    ax.axhline(avg_cvr, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)
    ax.set_xlabel('CTR (%)'); ax.set_ylabel('CVR (%)')
    ax.set_title('소재 효율 버블 차트 (버블 크기 = 광고비)', fontweight='bold')
    ax.legend(loc='lower right', fontsize=8)
    # Excel에 이미지로 삽입
    _save_chart_to_excel(ws, fig, anchor_cell, width=900, height=500)
```

**차트 9: 히트맵** (seaborn 사용)
```python
def add_age_type_heatmap(ws, pivot_df, metric_name, anchor_cell="A20"):
    """소재유형 × 나이대 CTR 또는 CVR 히트맵 — seaborn"""
    import seaborn as sns
    fig, ax = plt.subplots(figsize=(8, 3.5))
    sns.heatmap(pivot_df, annot=True, fmt='.2f', cmap='YlGn',
                linewidths=0.5, ax=ax, cbar_kws={'label': f'{metric_name} (%)'})
    ax.set_title(f'소재유형 × 나이대 {metric_name} 히트맵', fontweight='bold')
    _save_chart_to_excel(ws, fig, anchor_cell, width=520, height=230)
```

**공통 헬퍼 함수**
```python
import io
from openpyxl.drawing.image import Image as XLImage

def _save_chart_to_excel(ws, fig, anchor_cell, width=900, height=400):
    """matplotlib figure → Excel 이미지 삽입"""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    img = XLImage(buf)
    img.width = width; img.height = height
    ws.add_image(img, anchor_cell)
```

---

### 8-5. Excel 시트 구성 (7개)

| 시트 | 데이터 테이블 | 차트 |
|------|-------------|------|
| `📊 요약 대시보드` | KPI 카드 4개 + 지점 요약 테이블 | 차트 1(TIER도넛) + 차트 2(CPA막대) + 차트 3(레이더) |
| `🎬 소재 TIER 분석` | TIER, CPA, CTR, CVR, 랜딩률, 집행일수, 표본충분여부, 귀속주의, 지점편중주석, 지점별_상대평가, TIER_근거 | 차트 4(버블) + 차트 5(CPA분포) |
| `🔄 훅 개선 효과` | Strict 쌍 비교 + 소재유형 집계 비교 + 매칭실패목록 | 차트 6(전후비교) |
| `🏢 지점 컨텍스트` | 퍼널 + 목표CPA 달성률 (맥락 정보 — 참고용) | 없음 |
| `👥 나이대 분석` | 예산 효율 점수 + 효율 판정 | 차트 7(비용vs전환) + 차트 8(효율점수) + 차트 9(히트맵×2) |
| `📅 일별 트렌드` | 일별 비용/전환/CTR/CVR | 차트 10(콤보) + 차트 11(CTR라인) |
| `⏸ OFF 소재` | 마지막집행일, 총비용, CPA, CTR, 집행지점목록 | 없음 |

---

### 8-6. PDF 요약 (2페이지)

```
[Page 1]  분석 기간 / 총 광고비 / 총 전환 / 평균 CPA
          TIER 분포 요약 (차트 1 축소)
          지점별 성과 요약 테이블
          핵심 인사이트 3줄

[Page 2]  소재 버블 차트 (차트 4 축소)
          훅 개선 효과 하이라이트
          이번 주 추천 액션 플랜
          이상 감지 알림 + 데이터 참고 사항
```

---

## 9. 인사이트 작성 원칙

```
형식: 수치 근거 → 해석 → 액션 제안

인사이트 등급:
  확정 인사이트 — 표본 충분 + QA 통과
  가설 인사이트 — 표본 부족 / 귀속 이슈 포함 시 명시

금지 표현:
  - 단일 나이대 소량 데이터로 단정하는 표현
  - 클릭0/전환>0 행 기반 단정 표현
  - "최고 효율" 등 단정 표현 (LOW_VOLUME 소재에)

훅 비교 판정 기준:
  CTR↑ + CVR↑ → "재가공 유효 — 클릭·전환 모두 개선"
  CTR↑ + CVR↓ → "부분 효과 — 클릭↑ 전환↓ (랜딩 불일치 가능성)"
  CTR↓         → "재가공 효과 없음 — 원본 훅 복귀 검토"

예시:
  "\"다이어트의 적!밥,빵,면\" 소재의 CTR 0.97%(전체 평균 0.60% 대비 +62%),
   CVR 7.40%, CPA 15,119원으로 전 지표 최우수입니다.
   현재 서울·일산 2개 지점에만 집행 중이므로 대구·천안 지점 추가 집행을 권장합니다."
```

---

## 10. QA 체크리스트 (qa-agent 실행 기준)

```
데이터 무결성
  □ raw 총비용 = 분석 총비용 (허용 오차 ±1원)
  □ raw 총전환 = 분석 총전환
  □ 파싱 실패(FAIL) 소재가 TIER 분류에 포함되지 않았는가

TIER 분류 품질
  □ TIER1~4에 집행일수 7일 미만 소재 없는가
  □ TIER1~4에 볼륨 미달(클릭<100 AND 비용<10만) 소재 없는가
  □ TIER3 소재가 0개이면 랜딩률 조건 로직 재검토 (elif 순서 확인)

계산 검증
  □ CPA = 총비용 / 총전환 (소재 집계 기준)
  □ CVR = 총전환 / 총클릭 (소재 집계 기준, 행 단위 아님)
  □ CTR = 총클릭 / 총노출

훅 비교
  □ Strict 매칭 쌍이 0개이면 소재유형 집계 비교라도 표시되는가
  □ 매칭 실패 재가공 소재 목록이 표시되는가

OFF 소재
  □ 광고명에 '_off' 포함된 소재가 is_off=True로 파싱되었는가
  □ OFF 소재(is_off=True)가 TIER 분류 대상(df_on)에서 완전히 제외되었는가
  □ ⏸ OFF 소재 시트에 마지막집행일, 총비용, CPA, CTR이 표시되는가
  □ 본 TIER 분석 시트에 OFF 소재가 섞이지 않았는가

출력
  □ Excel 7개 시트 모두 생성되었는가
  □ PDF 2페이지 생성되었는가
  □ analysis_raw.json 생성되었는가
```

---

## 11. 스킬 YAML 정의

### tiktok-normalizer/SKILL.md

```yaml
---
name: tiktok-normalizer
description: TikTok 광고 raw CSV를 분석 가능한 표준 형식으로 변환한다.
  광고 ID 지수 표기 보정, KPI 재계산(_calc), 귀속 주의 플래그 생성을 수행.
  틱톡 CSV 업로드, 분석 시작, normalize 언급 시 자동 트리거.
metadata:
  author: dayt-automation
  version: 1.0.0
---
```

### creative-analyzer/SKILL.md

```yaml
---
name: creative-analyzer
description: 틱톡 광고 소재를 CTR/CVR/CPA/랜딩도달률 복합 지표로 평가하여
  TIER 1~4 / LOW_VOLUME / UNCLASSIFIED로 분류하고 액션 플랜을 생성한다.
  소재 분석, TIER 분류, 어떤 소재가 효율적인지 물어볼 때 자동 트리거.
  반드시 소재 단위 집계 후 TIER 부여 (행 단위 금지).
metadata:
  author: dayt-automation
  version: 2.0.0
---
```

---

## 12. 구현 우선순위

```
1단계 — MVP (지금 당장)
  ☐ normalize_tiktok_raw.py (Phase 0 표준화)
  ☐ parse_tiktok.py (파싱 + parse_status)
  ☐ score_creatives.py (소재 집계 + TIER + 볼륨 게이트)
  ☐ build_excel.py 기본 출력
     → 소재 TIER 분석 시트 + 나이대 분석 시트

2단계 — 고도화
  ☐ hook_comparison.py (strict 매칭 + 소재유형 집계 비교)
  ☐ branch_relative_flag (지점별 상대 평가)
  ☐ detect_anomalies.py (이상치 감지)
  ☐ insight-agent (AI 인사이트 문장)
  ☐ build_pdf.py

3단계 — 자동화 완성
  ☐ hooks 설정 (파일 감지 → 자동 실행)
  ☐ funnel-analyzer (내부DB 연결)
  ☐ creative_lineage.csv 도입 (훅 매칭 정확도 향상)
  ☐ improvement_suggestions.md 자동 생성
```

---

## 13. 추가 입력 파일 포맷 정의

### target_cpa.csv
```
지점,목표CPA
서울,20000
일산,20000
대구,30000
천안,35000
부평,35000
수원,40000
창원,45000
```

### creative_lineage.csv (2단계)
```
creative_group_id,원본소재명,재가공소재명,변경요소,비고
GROUP_001,주사형비만치료제 10년은,체지방만쏙빼는(부산잇츠),썸네일+초기카피,2월 재가공
```
