# TikTok 광고 분석 자동화 — 재설계 문서
> 바이브코딩 AI협업 지침 v2.0 기반
> 기존 설계 대비 변경점 중심으로 기술

---

## 🔍 현재 상태 vs v2.0 기준 GAP 분석

| Phase | v2.0 요구사항 | 현재 상태 | 평가 |
|-------|------------|---------|------|
| 0 SDD Spec | 주문서 먼저, 성공기준 측정 가능 | tiktok-project-final-spec.md 존재 | ⚠️ 형식 불일치 |
| 1 CLAUDE.md | 5~15KB, 실행명령 복붙 가능 | 존재하나 내용 미확인 | ⚠️ 보강 필요 |
| 2 Skills | Progressive Disclosure 구조 | `/skills/` (루트 위치) | ❌ 위치 오류 |
| 3 skill-rules.json | 3중 트리거 자동 활성화 | **없음** | ❌ 미구현 |
| 4 Agents | `.claude/agents/` + 3대 문서 | `/agents/` (루트, 비어있음) | ❌ 위치+내용 오류 |
| 5 Hooks | 3대 훅 (skill-activation/tracker/build-check) | `.claude/hooks/` 일부 존재 | ⚠️ 미완성 |
| 6 /insight | 지속 개선 루프 | **없음** | ❌ 미구현 |
| DDD | 도메인별 격리, 비즈니스 언어=코드명 | 스킬별 분리되나 DDD 미적용 | ⚠️ 부분 적용 |

**핵심 문제 3가지:**
1. `skill-rules.json` 없음 → AI가 스킬을 자동으로 읽지 않음 (가장 큰 원인)
2. `agents/`가 루트에 있고 비어있음 → 서브에이전트 분업 불가
3. 외부 기억 장치(3대 문서) 없음 → 긴 대화에서 맥락 소실

---

## 📁 재설계 디렉토리 구조

```
tiktok-report-automation/
│
├── CLAUDE.md                          ← Phase 1: 프로젝트 기억 (보강)
│
├── .claude/
│   ├── settings.json                  ← Phase 5: 훅 설정
│   │
│   ├── skills/                        ← Phase 2: 스킬 (루트→여기로 이동)
│   │   ├── skill-rules.json           ← Phase 3: 자동 활성화 규칙 (신규)
│   │   │
│   │   ├── tiktok-normalizer/         ← Phase 0: raw 표준화
│   │   │   ├── SKILL.md              ← 핵심 요약 (~100줄)
│   │   │   └── resources/
│   │   │       ├── column-mapping.md  ← 컬럼 표준화 규칙
│   │   │       └── calc-formulas.md  ← _calc 재계산 공식
│   │   │
│   │   ├── tiktok-parser/
│   │   │   ├── SKILL.md
│   │   │   └── resources/
│   │   │       ├── naming-rules.md    ← 광고명 파싱 규칙 상세
│   │   │       └── off-creative.md    ← OFF 소재 처리 규칙
│   │   │
│   │   ├── creative-analyzer/         ← 핵심 스킬
│   │   │   ├── SKILL.md
│   │   │   └── resources/
│   │   │       ├── tier-logic.md      ← TIER 분류 기준 상세
│   │   │       ├── hook-comparison.md ← 훅 비교 판정 기준
│   │   │       └── anomaly-rules.md   ← 이상치 감지 규칙
│   │   │
│   │   ├── report-generator/
│   │   │   ├── SKILL.md
│   │   │   └── resources/
│   │   │       ├── excel-structure.md ← 7시트 구성 + 차트 배치
│   │   │       ├── chart-spec.md      ← 11개 차트 구현 스펙
│   │   │       └── pdf-font.md        ← 한글 폰트 설정 (버그 수정)
│   │   │
│   │   ├── insight-writer/
│   │   │   ├── SKILL.md
│   │   │   └── resources/
│   │   │       └── insight-templates.md ← 인사이트 형식 + 판정 기준
│   │   │
│   │   └── daily-monitor/             ← 신규 스킬
│   │       ├── SKILL.md
│   │       └── resources/
│   │           ├── snapshot-schema.md ← 스냅샷 JSON 구조
│   │           └── anomaly-thresholds.md ← 이상 신호 임계값
│   │
│   ├── agents/                        ← Phase 4: 전문 에이전트 (위치 변경)
│   │   │
│   │   ├── planner.md                 ← 신규: Spec 기반 구현 계획 수립
│   │   ├── plan-reviewer.md           ← 신규: 계획 검토 + 위험 식별
│   │   │
│   │   ├── analysis-agent.md          ← 기존: 소재 집계 + TIER 분류
│   │   ├── hook-agent.md              ← 기존: 훅 효과 비교
│   │   ├── anomaly-agent.md           ← 기존: 이상치 감지
│   │   ├── insight-agent.md           ← 기존: 인사이트 생성
│   │   ├── daily-agent.md             ← 신규: 데일리 모니터링
│   │   ├── qa-agent.md                ← 기존: QA 검증
│   │   └── bug-resolver.md            ← 신규: 버그 자동 해결
│   │
│   └── hooks/
│       ├── skill-activation-prompt.sh ← 신규: 스킬 자동 활성화
│       ├── post-tool-use-tracker.sh   ← 신규: 변경 파일 추적
│       ├── pre-run.sh                 ← 기존: 입력 파일 유효성 검사
│       ├── post-analysis.sh           ← 기존: 분석 완료 후 트리거
│       └── build-check.sh             ← 신규: QA 자동 검증
│
├── dev/                               ← Phase 4-B: 외부 기억 장치 (신규)
│   └── active/
│       ├── weekly-report/
│       │   ├── weekly-report-plan.md      ← 전략 & 아키텍처
│       │   ├── weekly-report-context.md   ← 결정 이유 기록
│       │   └── weekly-report-tasks.md     ← 진행 체크리스트
│       ├── daily-monitor/
│       │   ├── daily-monitor-plan.md
│       │   ├── daily-monitor-context.md
│       │   └── daily-monitor-tasks.md
│       └── bug-fixes/
│           ├── bug-fixes-plan.md
│           ├── bug-fixes-context.md
│           └── bug-fixes-tasks.md
│
├── domain/                            ← DDD 도메인 구조 (신규)
│   ├── creative/                      ← 소재 도메인
│   │   ├── model.py                   ← Creative, TIER, HookPair 엔티티
│   │   ├── repository.py              ← parquet/csv 읽기/쓰기
│   │   └── service.py                 ← TIER 분류, 훅 비교 비즈니스 로직
│   ├── branch/                        ← 지점 도메인
│   │   ├── model.py
│   │   ├── repository.py
│   │   └── service.py
│   ├── campaign/                      ← 캠페인/일별 도메인
│   │   ├── model.py
│   │   ├── repository.py
│   │   └── service.py
│   └── report/                        ← 리포트 도메인
│       ├── model.py
│       ├── repository.py
│       └── service.py
│
├── scripts/                           ← 실행 스크립트 (skills 스크립트 → 여기로 통합)
│   ├── normalize_tiktok_raw.py
│   ├── parse_tiktok.py
│   ├── validate_input.py
│   ├── score_creatives.py
│   ├── hook_comparison.py
│   ├── detect_anomalies.py
│   ├── build_excel.py
│   ├── build_charts.py                ← 신규 (버그 수정 포함)
│   ├── build_pdf.py                   ← 버그 수정: 한글 폰트
│   ├── build_html.py                  ← 신규: HTML 인터랙티브 리포트
│   └── daily/
│       ├── daily_monitor.py
│       ├── save_snapshot.py
│       ├── compare_snapshots.py
│       ├── detect_daily_anomalies.py
│       └── build_daily_report.py
│
├── input/
├── output/YYYYMMDD/
├── daily/snapshots/
├── templates/
└── logs/
```

---

## Phase 0: SDD Spec 재작성

기존 `tiktok-project-final-spec.md`를 v2.0 형식으로 재구성.

```markdown
# TikTok 광고 분석 자동화 — 개발 Spec v2.0

## 1. 개요
- 목적: TikTok raw CSV 1개 업로드 → 주간 Excel+PDF+HTML + 데일리 md 자동 생성
- 범위:
  포함: 소재 TIER 분류, 훅 비교, 지점 분석, 나이대 분석, 데일리 스냅샷 비교
  제외: ROAS/내원율 (매체 컨트롤 불가 영역), TikTok API 직접 연동
- 성공 기준:
  [ ] raw CSV → 3종 리포트 생성까지 10분 이내
  [ ] qa_report.json all_pass = true
  [ ] 일별/지점/소재 전환 합계 3개 차원 일치
  [ ] PDF 한글 정상 출력 (■■■ 없음)
  [ ] 훅 판정 로직 CTR 방향 정확 반영

## 2. 기술 스택
| 영역 | 기술 | 버전 | 비고 |
|------|------|------|------|
| 데이터 처리 | pandas | 2.x | _calc 재계산값만 사용 |
| 파일 포맷 | parquet | - | 중간 산출물 저장 |
| Excel | openpyxl | 3.x | 차트 이미지 삽입 방식 |
| 차트 | matplotlib + seaborn | - | NanumGothic 폰트 |
| PDF | reportlab | 4.x | TTFont 한글 폰트 명시 |
| HTML | Chart.js | 4.4.1 | CDN, 단일 파일 |

## 3. 아키텍처
- 계층: domain/ (모델/로직) → scripts/ (실행) → output/ (산출물)
- 데이터 흐름: CSV → normalized.parquet → parsed.parquet
                → creative_tier.parquet → Excel+PDF+HTML
                → snapshots/ → daily_YYYYMMDD.md

## 4. 핵심 패턴 & 컨벤션
- 네이밍: 비즈니스 용어 = 코드명 (소재명/지점/TIER 그대로 사용)
- 절대 금지 규칙 6가지: (기존 섹션 0 유지)
- 수치 계산: CTR_calc / CVR_calc / CPA_calc (_calc 컬럼만)
- 검증: 모든 집계 함수는 3개 차원 교차 검증 후 저장

## 5. 단계별 구현 계획
| Phase | 작업 | 산출물 | 검증 명령 |
|-------|------|--------|----------|
| 1 | 디렉토리 재구성 | .claude/skills/, .claude/agents/ | ls -la .claude/ |
| 2 | skill-rules.json | 자동 활성화 설정 | 파일 존재 확인 |
| 3 | 버그 수정 4건 | build_pdf.py, insight_agent | qa_report.json |
| 4 | DDD 도메인 구조 | domain/ 4개 도메인 | python3 -c "import domain" |
| 5 | build_charts.py | 11개 차트 함수 | Excel 열어서 차트 확인 |
| 6 | build_html.py | 단일 HTML 파일 | 브라우저에서 열기 |
| 7 | 데일리 모니터링 | daily/ 스크립트 5개 | delta 계산 확인 |
| 8 | 3대 훅 | .claude/hooks/ 3개 sh | 수동 실행 후 등록 |

## 6. 검증 체크리스트
- [ ] python3 run_analysis.py 에러 없이 완료
- [ ] qa_report.json all_pass = true
- [ ] output/YYYYMMDD/ 에 xlsx + pdf + html + daily_md 4개 파일 존재
- [ ] PDF 2페이지에 한글 정상 출력
- [ ] improvement_suggestions.md 전체 한국어
- [ ] 훅 CTR +45.3% → "부분 효과" 판정 (Ineffective 아님)
```

---

## Phase 1: CLAUDE.md 보강 내용

기존 CLAUDE.md에 추가할 섹션:

```markdown
## 기술 스택 (정확한 버전)
- Python 3.12
- pandas 2.x, openpyxl 3.x, matplotlib (NanumGothic), reportlab 4.x
- Chart.js 4.4.1 (CDN)

## 핵심 실행 명령어
python3 run_analysis.py                    # 전체 파이프라인
python3 scripts/daily/daily_monitor.py     # 데일리만
python3 -m pytest tests/ -v               # QA 단위 테스트

## 스킬 위치 변경 (루트→.claude)
변경 전: skills/creative-analyzer/SKILL.md
변경 후: .claude/skills/creative-analyzer/SKILL.md

## 에이전트 위치 변경
변경 전: agents/analysis-agent.md
변경 후: .claude/agents/analysis-agent.md

## 흔한 실수 경고
⚠️ raw CTR/CVR/CPA 컬럼 직접 사용 금지 → _calc 컬럼만
⚠️ 훅 판정: CTR 양수 = 효과 있음 / 음수 = 효과 없음 (방향 역전 버그 수정됨)
⚠️ PDF 한글: TTFont('NanumGothic', '/path/to/NanumGothic.ttf') 명시 필수
⚠️ 차트 수치 하드코딩 금지 → DataFrame에서 직접 읽어서 사용

## 작업 프로세스
새 기능 추가 시:
1. dev/active/[task]/[task]-plan.md 먼저 작성
2. planner 에이전트로 계획 검토
3. plan-reviewer 에이전트로 위험 식별
4. 승인 후 구현 시작
5. 완료 시 [task]-tasks.md 체크리스트 업데이트

## 데일리 vs 주간 모드
- 단일 파일 업로드 → 주간 + 데일리 동시 생성
- 분석 기간: 캠페인 시작일 ~ 전일 (당일 제외)
- 스냅샷: daily/snapshots/YYYYMMDD_summary.json (삭제 금지)
```

---

## Phase 2: Skills — Progressive Disclosure 재구성

### creative-analyzer/SKILL.md 예시 (핵심 요약 ~100줄)

```markdown
---
name: creative-analyzer
description: "TikTok 소재를 CTR/CVR/CPA/랜딩도달률로 평가해 TIER1~4/LOW_VOLUME/UNCLASSIFIED로
  분류한다. 소재 분석, TIER 분류, 성과 평가 요청 시 자동 활성화."
---

## Purpose
소재 단위 집계 후 TIER 분류. 행 단위 분류는 절대 금지.

## When to Use
- "소재 분석해줘", "TIER 분류", "어떤 소재가 효율적"
- score_creatives.py 수정 시
- creative_tier.parquet 관련 작업 시

## Quick Reference
- 입력: output/parsed.parquet
- 출력: output/creative_tier.parquet
- TARGET_CPA: 평가 가능 소재의 CPA 중앙값
- 볼륨 게이트: 집행일수<7 → UNCLASSIFIED / 클릭<100 AND 비용<10만 → LOW_VOLUME

## ✅ DO
- 소재 단위 groupby 후 TIER 부여
- _calc 재계산값 컬럼만 사용 (CTR_calc, CVR_calc, CPA_calc)
- LOW_VOLUME/UNCLASSIFIED 소재는 버블 차트에서 제외

## ❌ DON'T
- 행 단위로 TIER 분류 (절대 금지)
- raw CTR/CVR/CPA 컬럼 직접 사용
- 클릭=0이면서 전환>0인 행으로 CVR 계산

## Resource Files
- [tier-logic.md](resources/tier-logic.md) — TIER 판정 로직 상세
- [hook-comparison.md](resources/hook-comparison.md) — 훅 판정 기준 (CTR 방향)
- [anomaly-rules.md](resources/anomaly-rules.md) — 이상치 감지 규칙
```

### creative-analyzer/resources/hook-comparison.md 핵심 내용

```markdown
# 훅 비교 판정 기준

## 판정 로직 (버그 수정 반영)
CTR_change = (재가공_CTR - 신규_CTR) / 신규_CTR * 100

if CTR_change > 0 and CVR_change > 0:
    verdict = "재가공 유효 — 클릭·전환 모두 개선"
elif CTR_change > 0 and CVR_change <= 0:
    verdict = "부분 효과 — 클릭↑ 전환↓ (랜딩 불일치 가능성)"
elif CTR_change <= 0:
    verdict = "재가공 효과 없음 — 원본 훅 복귀 검토"

## ❌ 잘못된 패턴 (수정된 버그)
CTR +45.3% → "Hook Ineffective" (X) ← 방향 역전 버그
CTR +45.3% → "부분 효과 — 클릭↑"  (O) ← 올바른 판정
```

---

## Phase 3: skill-rules.json (신규)

```json
{
  "version": "1.0",
  "skills": {

    "tiktok-normalizer": {
      "type": "domain",
      "enforcement": "suggest",
      "priority": "critical",
      "description": "TikTok raw CSV 표준화. 광고ID 지수표기 방지, KPI _calc 재계산",
      "promptTriggers": {
        "keywords": ["normalize", "표준화", "raw", "csv", "광고ID", "지수표기"],
        "intentPatterns": [
          "(표준화|normalize|변환).*?(csv|raw|틱톡)",
          "광고.*?ID.*?지수"
        ]
      },
      "fileTriggers": {
        "pathPatterns": ["scripts/normalize_tiktok_raw.py"],
        "contentPatterns": ["dtype={'광고 ID': str}", "CTR_calc"]
      }
    },

    "creative-analyzer": {
      "type": "domain",
      "enforcement": "block",
      "priority": "critical",
      "description": "소재 TIER 분류. 소재 단위 집계 후 분류 (행 단위 금지). _calc 컬럼만 사용",
      "promptTriggers": {
        "keywords": ["TIER", "소재", "creative", "CPA", "CTR", "CVR", "훅", "hook"],
        "intentPatterns": [
          "(분류|classify|평가|score).*?(소재|creative|TIER)",
          "(훅|hook).*?(비교|compare|효과|effect)"
        ]
      },
      "fileTriggers": {
        "pathPatterns": [
          "scripts/score_creatives.py",
          "scripts/hook_comparison.py",
          "domain/creative/*.py"
        ],
        "contentPatterns": ["creative_tier", "TIER1", "hook_comparison", "_calc"]
      }
    },

    "report-generator": {
      "type": "domain",
      "enforcement": "suggest",
      "priority": "high",
      "description": "Excel 7시트+차트, PDF 한글폰트, HTML 인터랙티브 리포트 생성",
      "promptTriggers": {
        "keywords": ["Excel", "PDF", "리포트", "차트", "report", "chart", "html"],
        "intentPatterns": [
          "(생성|generate|만들|build).*?(Excel|PDF|리포트|차트|html)",
          "(한글|폰트|font).*?(PDF|깨짐)"
        ]
      },
      "fileTriggers": {
        "pathPatterns": [
          "scripts/build_excel.py",
          "scripts/build_charts.py",
          "scripts/build_pdf.py",
          "scripts/build_html.py"
        ],
        "contentPatterns": ["openpyxl", "reportlab", "NanumGothic", "Chart.js"]
      }
    },

    "data-integrity-guardrail": {
      "type": "guardrail",
      "enforcement": "block",
      "priority": "critical",
      "description": "데이터 정합성 수호. raw 컬럼 직접 사용, 수치 하드코딩, 행 단위 CVR 계산 차단",
      "promptTriggers": {
        "keywords": ["CTR", "CVR", "CPA", "전환", "계산", "수치"],
        "intentPatterns": [
          "CTR.*?계산|CVR.*?계산|CPA.*?계산",
          "(수치|value|data).*?(입력|하드코딩|직접)"
        ]
      },
      "fileTriggers": {
        "pathPatterns": ["scripts/*.py", "domain/**/*.py"],
        "contentPatterns": ["df\\['CTR'\\]", "df\\['CVR'\\]", "df\\['CPA'\\]"]
      }
    },

    "insight-writer": {
      "type": "domain",
      "enforcement": "suggest",
      "priority": "high",
      "description": "인사이트 문장 생성. 훅 판정 방향 정확성, 한국어 출력, 확정/가설 등급 명시",
      "promptTriggers": {
        "keywords": ["인사이트", "insight", "개선", "제안", "액션", "권고"],
        "intentPatterns": [
          "(인사이트|insight).*?(생성|작성|write)",
          "(개선|improvement).*?(제안|suggestion)"
        ]
      },
      "fileTriggers": {
        "pathPatterns": [
          ".claude/agents/insight-agent.md",
          "output/**/improvement_suggestions.md"
        ],
        "contentPatterns": ["Hook.*?Ineffective", "확정", "가설"]
      }
    },

    "daily-monitor": {
      "type": "domain",
      "enforcement": "suggest",
      "priority": "high",
      "description": "데일리 모니터링. 전일 스냅샷 비교, 이상 신호 감지, 지점별 변동 md 생성",
      "promptTriggers": {
        "keywords": ["데일리", "daily", "모니터링", "전일", "스냅샷", "snapshot"],
        "intentPatterns": [
          "(데일리|daily).*?(리포트|report|모니터링)",
          "(전일|어제|yesterday).*?(비교|compare|변동)"
        ]
      },
      "fileTriggers": {
        "pathPatterns": ["scripts/daily/*.py", "daily/snapshots/*.json"],
        "contentPatterns": ["save_snapshot", "compare_snapshots", "daily_monitor"]
      }
    }
  }
}
```

---

## Phase 4: 에이전트 재설계

### 신규 에이전트 2개

#### .claude/agents/planner.md
```markdown
# Planner Agent

## Purpose
새 기능/버그 수정 전, Spec 기반 구현 계획을 수립한다. 코드 작성 금지.

## When to Use
- 새 스크립트 작성 전
- 기존 코드 대규모 수정 전
- 버그 수정 방향 결정 전

## Instructions
1. @tiktok-project-redesign.md 의 Spec 섹션을 읽는다
2. skill-rules.json 에서 관련 스킬을 확인한다
3. 아래 형식으로 계획을 dev/active/[task]/[task]-plan.md 에 저장한다:
   - 변경 파일 목록 (정확한 경로)
   - 단계별 작업 순서 (Small Chunks)
   - 각 단계 검증 명령어
   - 예상 리스크와 롤백 방법
4. 계획 저장 후 plan-reviewer 에이전트를 호출한다

## Tools Available
- Read, Glob (코드 탐색)
- Write (계획 문서 저장만)

## Expected Output Format
dev/active/[task]/[task]-plan.md 파일

## Success Criteria
- [ ] 변경 파일 목록이 정확한 경로로 명시되어 있는가
- [ ] 각 단계에 검증 명령어가 있는가
- [ ] 코드를 직접 작성하지 않았는가
```

#### .claude/agents/bug-resolver.md
```markdown
# Bug Resolver Agent

## Purpose
발견된 버그를 skill-rules.json의 guardrail과 SKILL.md를 참조해 수정한다.

## When to Use
- qa_report.json all_pass = false
- 알려진 버그 4개 수정 시:
  1. 훅 판정 로직 역전 (CTR 방향)
  2. PDF 한글 폰트 깨짐
  3. TIER 분포 수치 불일치
  4. improvement_suggestions.md 영어 혼재

## Instructions
1. .claude/skills/creative-analyzer/resources/hook-comparison.md 읽기
2. .claude/skills/report-generator/resources/pdf-font.md 읽기
3. 버그 원인 파악 후 dev/active/bug-fixes/bug-fixes-context.md 에 기록
4. 수정 → qa_report.json 재실행 → all_pass 확인

## Success Criteria
- [ ] CTR +45.3% → "부분 효과" 판정 (Ineffective 아님)
- [ ] PDF 한글 정상 출력 (■■■ 없음)
- [ ] TIER 분포 합계 24개 (Excel/PDF 일치)
- [ ] improvement_suggestions.md 전체 한국어
```

---

## Phase 5: 3대 훅 재설계

### skill-activation-prompt.sh (신규)
```bash
#!/bin/bash
# UserPromptSubmit 훅 — 프롬프트에서 관련 스킬 자동 감지 후 제안

PROMPT="$1"
RULES=".claude/skills/skill-rules.json"

# skill-rules.json 키워드 매칭
if echo "$PROMPT" | grep -qiE "TIER|소재|CTR|CVR|CPA|훅|hook"; then
  echo "📋 [SKILL 활성화] creative-analyzer 스킬을 참조하세요"
  echo "   경로: .claude/skills/creative-analyzer/SKILL.md"
fi

if echo "$PROMPT" | grep -qiE "Excel|PDF|차트|리포트|report|chart|한글|폰트"; then
  echo "📋 [SKILL 활성화] report-generator 스킬을 참조하세요"
  echo "   경로: .claude/skills/report-generator/SKILL.md"
fi

if echo "$PROMPT" | grep -qiE "데일리|daily|스냅샷|전일|모니터링"; then
  echo "📋 [SKILL 활성화] daily-monitor 스킬을 참조하세요"
  echo "   경로: .claude/skills/daily-monitor/SKILL.md"
fi

if echo "$PROMPT" | grep -qiE "수치.*입력|하드코딩|직접.*계산"; then
  echo "🚫 [GUARDRAIL] data-integrity-guardrail 위반 가능성 감지"
  echo "   _calc 재계산값 컬럼만 사용, DataFrame에서 직접 읽어야 합니다"
fi
```

### build-check.sh (신규)
```bash
#!/bin/bash
# Stop 훅 — 작업 완료 시 자동 QA 검증

echo "🔍 자동 QA 검증 시작..."

# 가장 최근 output 폴더 탐색
LATEST=$(ls -td output/20*/ 2>/dev/null | head -1)

if [ -z "$LATEST" ]; then
  echo "⚠️ output 폴더 없음 — QA 스킵"
  exit 0
fi

# qa_report.json 확인
QA_REPORT="$LATEST/qa_report.json"
if [ -f "$QA_REPORT" ]; then
  ALL_PASS=$(python3 -c "import json; d=json.load(open('$QA_REPORT')); print(d.get('all_pass','false'))")
  if [ "$ALL_PASS" = "True" ]; then
    echo "✅ QA 통과: $QA_REPORT"
  else
    echo "❌ QA 실패: $QA_REPORT — qa-agent 실행 권장"
    python3 -c "
import json
d=json.load(open('$QA_REPORT'))
for f in d.get('failures',[]):
    print('  ·', f)
"
  fi
fi

# 4개 리포트 파일 존재 확인
for ext in xlsx pdf html; do
  if ls "$LATEST"*.$ext 2>/dev/null | head -1 | grep -q .; then
    echo "✅ $ext 파일 존재"
  else
    echo "⚠️ $ext 파일 없음"
  fi
done

# 데일리 md 확인
if ls "$LATEST"daily_*.md 2>/dev/null | head -1 | grep -q .; then
  echo "✅ 데일리 md 존재"
fi
```

---

## Phase 6: /insight 개선 루프

```markdown
## 현재 확인된 마찰 패턴 (첫 /insight)

| # | 마찰 패턴 | 원인 | 반영 위치 |
|---|----------|------|---------|
| 1 | 훅 판정 방향 역전 | insight-agent 프롬프트에 판정 기준 없음 | hook-comparison.md + skill-rules block |
| 2 | PDF 한글 깨짐 | build_pdf.py에 TTFont 설정 없음 | pdf-font.md + report-generator SKILL |
| 3 | 수치 하드코딩 | "편리하게" 직접 입력 | data-integrity guardrail block 모드 |
| 4 | 영어 혼재 출력 | 프롬프트에 언어 강제 없음 | insight-writer SKILL + 템플릿 |
| 5 | TIER 수치 불일치 | PDF/Excel 데이터 소스 다름 | qa-agent 체크리스트에 추가 |

## 다음 /insight 실행 기준
4주 사용 후 또는 버그 3건 이상 재발 시
```

---

## 재설계 전후 비교

| 항목 | 기존 | 재설계 후 |
|------|------|---------|
| 스킬 위치 | `/skills/` (루트) | `.claude/skills/` |
| 에이전트 위치 | `/agents/` (루트, 비어있음) | `.claude/agents/` (13개) |
| SKILL.md 구조 | 단일 파일 (~900줄) | Progressive Disclosure (핵심 100줄 + resources/) |
| skill-rules.json | 없음 | 6개 스킬 트리거 + guardrail 1개 |
| 에이전트 수 | 5개 (미구현) | 9개 (planner, plan-reviewer, bug-resolver 신규) |
| 외부 기억 장치 | 없음 | dev/active/ 3대 문서 |
| 훅 | hooks/ 일부 | 3대 훅 완성 (skill-activation/tracker/build-check) |
| 도메인 구조 | 없음 | domain/ 4개 도메인 (DDD) |
| 리포트 종류 | Excel + PDF | Excel + PDF + HTML + 데일리 md |
| 버그 관리 | 없음 | bug-resolver 에이전트 + bug-fixes 기억 장치 |

---

## 구현 우선순위 (Small Chunks)

```
1단계 — 즉시 (구조 재배치, 하루)
  ☐ skills/ → .claude/skills/ 이동
  ☐ agents/ → .claude/agents/ 이동
  ☐ skill-rules.json 신규 생성
  ☐ dev/active/ 폴더 + 3대 문서 초기화

2단계 — 버그 수정 (이틀)
  ☐ bug-fixes-plan.md 작성 후 승인
  ☐ 훅 판정 로직 역전 수정
  ☐ PDF 한글 폰트 수정
  ☐ TIER 수치 불일치 수정
  ☐ improvement_suggestions.md 한국어화

3단계 — 미구현 기능 (사흘)
  ☐ build_charts.py 11개 차트
  ☐ build_html.py (정합성 검증 배너 포함)
  ☐ .claude/agents/ 파일 9개 작성

4단계 — 데일리 모니터링 (이틀)
  ☐ daily-monitor-plan.md 작성 후 승인
  ☐ scripts/daily/ 5개 스크립트
  ☐ run_analysis.py → 주간+데일리 동시 생성

5단계 — 훅 + DDD (이틀)
  ☐ 3대 훅 sh 파일 작성 + 수동 테스트 후 등록
  ☐ domain/ 4개 도메인 (수동으로 첫 도메인 작성 → AI 복제)
```
