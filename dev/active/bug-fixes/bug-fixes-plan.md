# Bug Fixes 전략 & 아키텍처

## 목표
v2.0 마이그레이션 과정에서 발견된 4개 버그 수정

## 수정 대상 파일
1. `.claude/skills/insight-writer/scripts/generate_insights.py`
2. `.claude/skills/report-generator/scripts/build_pdf.py`
3. `.claude/agents/*.md` (5개 파일)

## 검증 방법
- `python run_analysis.py` 실행
- `qa_report.json` all_pass 확인
- PDF 수동 검증 (한글 출력)
- improvement_suggestions.md 언어 확인

## 완료 상태
✅ 모든 버그 수정 완료 (2026-02-27)
