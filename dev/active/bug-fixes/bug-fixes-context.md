# Bug Fixes 결정 이유 기록

## 훅 판정 로직 역전

### 문제
- CTR +45.3% 상황에서 "Hook Ineffective" 판정
- 방향이 역전되어 있었음

### 해결
```python
# generate_insights.py
elif '부분 효과' in verdict:
    # CTR+ but CVR- 또는 CTR- but CVR+ → 부분 효과
    self.add_insight(...)
```

### 결정 근거
- CTR 상승 = 클릭 유도 성공 = 훅 효과 있음
- CVR 하락 = 랜딩 불일치 가능성
- 따라서 "부분 효과"가 올바른 판정

## PDF 한글 폰트

### 문제
- PDF 출력 시 한글이 ■■■로 표시

### 해결
- `build_pdf.py`에 TTFont 등록
- `create_table_style(font_name)` 파라미터 추가

### 결정 근거
- reportlab 기본 폰트는 한글 미지원
- NanumGothic 또는 AppleSDGothicNeo 사용

## 에이전트 한국어화

### 결정 근거
- 프로젝트 전체가 한국어 기반
- insight-agent.md 등 5개 파일 한국어화
- 일관성 유지
