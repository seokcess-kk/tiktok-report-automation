# 차트 구현 설계 — build_charts.py

> TikTok 광고 분석 리포트 시각화 명세  
> 라이브러리: openpyxl (Excel 내장 차트) + matplotlib (이미지 삽입)  
> 원칙: 차트는 데이터 테이블 바로 옆 또는 아래에 배치, 테이블과 항상 함께 존재

---

## 차트 목록 및 시트 배치

| # | 차트명 | 시트 | 차트 유형 | 목적 |
|:-:|--------|------|:---------:|------|
| 1 | TIER 분포 도넛 차트 | 📊 요약 대시보드 | Donut | TIER별 소재 수/비용 비중 한눈에 파악 |
| 2 | 지점별 CPA 가로 막대 | 📊 요약 대시보드 | Bar (H) | 지점 간 효율 격차 시각화 |
| 3 | 소재 CPA 버블 차트 | 🎬 소재 TIER 분석 | Bubble | CTR×CVR×비용 3차원 비교 |
| 4 | 훅 개선 전후 비교 | 🔄 훅 개선 효과 | Bar (grouped) | 신규↔재가공 CTR/CVR/CPA 변화 |
| 5 | 나이대 예산 효율 막대 | 👥 나이대 분석 | Bar (stacked) | 비용비중 vs 전환비중 대비 |
| 6 | 소재유형×나이대 히트맵 | 👥 나이대 분석 | Heatmap (image) | CTR/CVR 패턴 색상 시각화 |
| 7 | 일별 비용+전환 콤보 | 📅 일별 트렌드 | Line + Bar | 예산 집행과 전환 추이 동시 확인 |
| 8 | 소재 피로도 라인 | 📅 일별 트렌드 | Line (multi) | 주요 소재별 일별 CVR 변화 |

---

## 차트별 상세 구현 명세

---

### 차트 1: TIER 분포 도넛 차트
**시트**: 📊 요약 대시보드 | **위치**: KPI 카드 우측

```python
from openpyxl.chart import DoughnutChart, Reference

def add_tier_donut(ws, creative_df, start_row=2, start_col=6):
    """
    TIER별 소재 수 기준 도넛 차트
    색상 규칙:
      TIER1      → 초록  (#2ECC71)
      TIER2      → 파랑  (#3498DB)
      TIER3      → 주황  (#F39C12)
      TIER4      → 빨강  (#E74C3C)
      LOW_VOLUME → 회색  (#95A5A6)
      UNCLASSIFIED → 연회색 (#BDC3C7)
    """
    tier_order = ['TIER1', 'TIER2', 'TIER3', 'TIER4', 'LOW_VOLUME', 'UNCLASSIFIED']
    tier_colors = {
        'TIER1': 'FF2ECC71', 'TIER2': 'FF3498DB',
        'TIER3': 'FFF39C12', 'TIER4': 'FFE74C3C',
        'LOW_VOLUME': 'FF95A5A6', 'UNCLASSIFIED': 'FFBDC3C7'
    }
    
    counts = creative_df['TIER'].value_counts().reindex(tier_order, fill_value=0)
    
    # 데이터를 시트에 임시 기입 (차트 소스용)
    data_start = start_row + 15  # 차트 아래쪽 숨김 영역에 배치
    for i, (tier, cnt) in enumerate(counts.items()):
        ws.cell(data_start + i, start_col, tier)
        ws.cell(data_start + i, start_col + 1, cnt)
    
    chart = DoughnutChart()
    chart.title = "소재 TIER 분포"
    chart.style = 10
    chart.holeSize = 40  # 도넛 구멍 크기
    
    data_ref   = Reference(ws, min_col=start_col+1, min_row=data_start,
                           max_row=data_start+len(counts)-1)
    labels_ref = Reference(ws, min_col=start_col,   min_row=data_start,
                           max_row=data_start+len(counts)-1)
    chart.add_data(data_ref)
    chart.set_categories(labels_ref)
    chart.width  = 12
    chart.height = 12
    
    ws.add_chart(chart, f"{get_col_letter(start_col+3)}{start_row}")
```

---

### 차트 2: 지점별 CPA 가로 막대 차트
**시트**: 📊 요약 대시보드 | **위치**: TIER 도넛 우측

```python
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.series import SeriesLabel

def add_branch_cpa_bar(ws, branch_df, start_row=2, start_col=12):
    """
    지점별 CPA 가로 막대 차트
    - 목표CPA 기준선 보조선 추가
    - 색상: CPA ≤ 목표 → 초록, CPA > 목표 → 빨강
    - 정렬: CPA 오름차순 (효율 좋은 지점이 위)
    """
    sorted_df = branch_df.sort_values('CPA', ascending=True)
    
    data_start = start_row + 20
    for i, row in enumerate(sorted_df.itertuples()):
        ws.cell(data_start + i, start_col, row.지점)
        ws.cell(data_start + i, start_col + 1, row.CPA)
    
    chart = BarChart()
    chart.type    = "bar"   # 가로 막대
    chart.title   = "지점별 CPA (원)"
    chart.y_axis.title = "지점"
    chart.x_axis.title = "CPA (원)"
    chart.style   = 10
    chart.shape   = 4
    
    data_ref   = Reference(ws, min_col=start_col+1, min_row=data_start,
                           max_row=data_start+len(sorted_df)-1)
    labels_ref = Reference(ws, min_col=start_col,   min_row=data_start,
                           max_row=data_start+len(sorted_df)-1)
    chart.add_data(data_ref)
    chart.set_categories(labels_ref)
    chart.width  = 14
    chart.height = 12
    
    ws.add_chart(chart, f"{get_col_letter(start_col+3)}{start_row}")
```

---

### 차트 3: 소재 CPA 버블 차트 (핵심 차트)
**시트**: 🎬 소재 TIER 분석 | **위치**: 테이블 하단

```python
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import io
from openpyxl.drawing.image import Image as XLImage

def add_creative_bubble_chart(ws, creative_df, output_path, anchor_cell="A35"):
    """
    X축: CTR (%)
    Y축: CVR (%)
    버블 크기: 총비용 (클수록 많은 예산 투입)
    색상: TIER별 색상
    라벨: 소재명 (짧게 자름)

    이 차트로 한눈에:
      - 우상단 + 큰 버블 → TIER1 이상적 소재 (CTR↑ CVR↑ 비용↑)
      - 우상단 + 작은 버블 → 예산 확대 후보
      - 좌하단 → TIER4 제거 후보
    """
    TIER_COLORS = {
        'TIER1': '#2ECC71', 'TIER2': '#3498DB',
        'TIER3': '#F39C12', 'TIER4': '#E74C3C',
        'LOW_VOLUME': '#95A5A6', 'UNCLASSIFIED': '#BDC3C7'
    }
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    eval_df = creative_df[creative_df['TIER'].isin(
        ['TIER1','TIER2','TIER3','TIER4']
    )].dropna(subset=['CTR','CVR','CPA'])
    
    for tier, group in eval_df.groupby('TIER'):
        sizes = (group['총비용'] / group['총비용'].max() * 1500).clip(lower=100)
        ax.scatter(
            group['CTR'], group['CVR'],
            s=sizes,
            c=TIER_COLORS.get(tier, '#999'),
            alpha=0.7,
            label=tier,
            edgecolors='white',
            linewidth=0.8
        )
        # 소재명 라벨 (10자 이상이면 자름)
        for _, row in group.iterrows():
            label = row['소재명'][:10] + '…' if len(row['소재명']) > 10 else row['소재명']
            ax.annotate(label, (row['CTR'], row['CVR']),
                       textcoords="offset points", xytext=(5, 5),
                       fontsize=7, color='#333')
    
    # 평균선 (기준선)
    avg_ctr = eval_df['CTR'].mean()
    avg_cvr = eval_df['CVR'].mean()
    ax.axvline(avg_ctr, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)
    ax.axhline(avg_cvr, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)
    ax.text(avg_ctr, ax.get_ylim()[1]*0.98, f' 평균CTR\n {avg_ctr:.2f}%',
            fontsize=7, color='gray')
    ax.text(ax.get_xlim()[1]*0.02, avg_cvr, f'평균CVR {avg_cvr:.1f}%',
            fontsize=7, color='gray')
    
    # 사분면 레이블
    ax.text(ax.get_xlim()[1]*0.85, ax.get_ylim()[1]*0.90,
            "유입↑전환↑\n(이상적)", fontsize=8, color='#2ECC71', alpha=0.6)
    ax.text(ax.get_xlim()[0]*1.02, ax.get_ylim()[0]*1.05,
            "유입↓전환↓\n(제거 검토)", fontsize=8, color='#E74C3C', alpha=0.6)
    
    ax.set_xlabel('CTR (%)', fontsize=10)
    ax.set_ylabel('CVR (%)', fontsize=10)
    ax.set_title('소재 효율 버블 차트 (버블 크기 = 광고비)', fontsize=12, fontweight='bold')
    ax.legend(loc='lower right', fontsize=8)
    ax.grid(True, alpha=0.2)
    
    plt.tight_layout()
    
    # 이미지로 저장 후 Excel에 삽입
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png', dpi=150, bbox_inches='tight')
    img_buf.seek(0)
    plt.close()
    
    xl_img = XLImage(img_buf)
    xl_img.width  = 900
    xl_img.height = 500
    ws.add_image(xl_img, anchor_cell)
```

---

### 차트 4: 훅 개선 전후 비교 막대 차트
**시트**: 🔄 훅 개선 효과 | **위치**: 비교 테이블 우측

```python
def add_hook_comparison_chart(ws, hook_pairs_df, anchor_cell="I3"):
    """
    신규 vs 재가공: CTR / CVR / CPA 변화율 묶음 막대
    
    - CPA는 음수가 좋음 (낮을수록 좋으므로 감소율로 표시)
    - CTR/CVR은 양수가 좋음
    - 기준선(0%) 표시
    """
    if hook_pairs_df.empty:
        return
    
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    
    metrics = [
        ('CTR_변화율', 'CTR 변화율 (%)', '#3498DB', True),   # 양수 = 좋음
        ('CVR_변화율', 'CVR 변화율 (%)', '#2ECC71', True),
        ('CPA_변화율', 'CPA 변화율 (%)', '#E74C3C', False),  # 음수 = 좋음
    ]
    
    for ax, (col, title, color, higher_better) in zip(axes, metrics):
        values = hook_pairs_df[col].fillna(0)
        names  = hook_pairs_df['소재명'].apply(
            lambda x: x[:8] + '…' if len(x) > 8 else x
        )
        colors = []
        for v in values:
            if higher_better:
                colors.append('#2ECC71' if v > 0 else '#E74C3C')
            else:
                colors.append('#2ECC71' if v < 0 else '#E74C3C')
        
        bars = ax.bar(range(len(values)), values, color=colors, alpha=0.8)
        ax.axhline(0, color='black', linewidth=0.8)
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels(names, rotation=30, ha='right', fontsize=7)
        ax.set_title(title, fontsize=9, fontweight='bold')
        ax.set_ylabel('%', fontsize=8)
        
        # 값 레이블
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width()/2,
                   bar.get_height() + (0.3 if val >= 0 else -0.8),
                   f'{val:+.1f}%', ha='center', fontsize=7)
    
    fig.suptitle('훅(썸네일/카피) 변경 효과 — 신규 대비 재가공', 
                fontsize=11, fontweight='bold')
    plt.tight_layout()
    
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png', dpi=150, bbox_inches='tight')
    img_buf.seek(0)
    plt.close()
    
    xl_img = XLImage(img_buf)
    xl_img.width  = 900
    xl_img.height = 320
    ws.add_image(xl_img, anchor_cell)
```

---

### 차트 5: 나이대 예산 vs 전환 비중 스택 막대
**시트**: 👥 나이대 분석 | **위치**: 테이블 우측

```python
def add_age_efficiency_chart(ws, age_summary_df, anchor_cell="I3"):
    """
    나이대별 비용비중(파랑) vs 전환비중(초록) 나란히 막대
    → 두 막대의 격차가 예산 효율 점수를 직관적으로 보여줌
    
    예: 25-34세: 비용 14.6% bar가 전환 5.2% bar보다 훨씬 크면 → 비효율 명확
    """
    fig, ax = plt.subplots(figsize=(9, 5))
    
    ages   = age_summary_df['age_group']
    x      = range(len(ages))
    width  = 0.35
    
    bars1 = ax.bar([i - width/2 for i in x],
                   age_summary_df['비용비중'], width,
                   label='비용 비중 (%)', color='#3498DB', alpha=0.8)
    bars2 = ax.bar([i + width/2 for i in x],
                   age_summary_df['전환비중'], width,
                   label='전환 비중 (%)', color='#2ECC71', alpha=0.8)
    
    # 예산 효율 점수 텍스트
    for i, row in age_summary_df.iterrows():
        score = row['예산효율점수']
        color = '#2ECC71' if score >= 0.8 else '#E74C3C'
        ax.text(i, max(row['비용비중'], row['전환비중']) + 0.5,
               f'효율 {score:.2f}', ha='center', fontsize=8,
               color=color, fontweight='bold')
    
    ax.set_xticks(list(x))
    ax.set_xticklabels(ages, fontsize=10)
    ax.set_ylabel('비중 (%)', fontsize=10)
    ax.set_title('나이대별 비용 vs 전환 비중\n(효율점수 = 전환비중 ÷ 비용비중)', 
                fontsize=10, fontweight='bold')
    ax.legend(fontsize=9)
    ax.grid(axis='y', alpha=0.3)
    ax.axhline(0, color='black', linewidth=0.5)
    
    plt.tight_layout()
    
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png', dpi=150, bbox_inches='tight')
    img_buf.seek(0)
    plt.close()
    
    xl_img = XLImage(img_buf)
    xl_img.width  = 580
    xl_img.height = 330
    ws.add_image(xl_img, anchor_cell)
```

---

### 차트 6: 소재유형 × 나이대 히트맵
**시트**: 👥 나이대 분석 | **위치**: 예산효율 차트 아래

```python
def add_age_type_heatmap(ws, pivot_df, metric_name, anchor_cell="A20"):
    """
    소재유형 × 나이대 CTR 또는 CVR 히트맵
    → 어떤 소재유형이 어느 나이대에서 잘 반응하는지 패턴 파악
    
    색상: 낮음(흰색) → 높음(진한 초록)
    """
    fig, ax = plt.subplots(figsize=(8, 3.5))
    
    import seaborn as sns
    sns.heatmap(
        pivot_df,
        annot=True, fmt='.2f',
        cmap='YlGn',
        linewidths=0.5,
        ax=ax,
        cbar_kws={'label': f'{metric_name} (%)'}
    )
    ax.set_title(f'소재유형 × 나이대 {metric_name} 히트맵', 
                fontsize=10, fontweight='bold')
    ax.set_xlabel('나이대', fontsize=9)
    ax.set_ylabel('소재유형', fontsize=9)
    plt.tight_layout()
    
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png', dpi=150, bbox_inches='tight')
    img_buf.seek(0)
    plt.close()
    
    xl_img = XLImage(img_buf)
    xl_img.width  = 520
    xl_img.height = 230
    ws.add_image(xl_img, anchor_cell)
```

---

### 차트 7: 일별 비용 + 전환 콤보 차트
**시트**: 📅 일별 트렌드 | **위치**: 테이블 하단

```python
def add_daily_combo_chart(ws, daily_df, anchor_cell="A25"):
    """
    막대(비용) + 라인(전환수) 이중축 차트
    → 예산 집행 리듬과 전환 발생의 관계 파악
    → 비용은 많은데 전환 없는 날 → 이상 감지
    """
    fig, ax1 = plt.subplots(figsize=(14, 5))
    
    dates = daily_df['date']
    x     = range(len(dates))
    
    # 막대: 비용
    bars = ax1.bar(x, daily_df['cost'], color='#AED6F1', alpha=0.8, label='비용 (원)')
    ax1.set_ylabel('비용 (원)', color='#3498DB', fontsize=10)
    ax1.tick_params(axis='y', labelcolor='#3498DB')
    
    # 라인: 전환수 (이중축)
    ax2 = ax1.twinx()
    ax2.plot(x, daily_df['conversions'], color='#E74C3C', linewidth=2,
            marker='o', markersize=4, label='전환수')
    ax2.set_ylabel('전환수', color='#E74C3C', fontsize=10)
    ax2.tick_params(axis='y', labelcolor='#E74C3C')
    
    ax1.set_xticks(list(x))
    ax1.set_xticklabels([str(d)[-5:] for d in dates], rotation=45, ha='right', fontsize=7)
    ax1.set_title('일별 광고 비용 vs 전환수', fontsize=11, fontweight='bold')
    
    # 범례 합치기
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=8)
    
    ax1.grid(axis='y', alpha=0.2)
    plt.tight_layout()
    
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png', dpi=150, bbox_inches='tight')
    img_buf.seek(0)
    plt.close()
    
    xl_img = XLImage(img_buf)
    xl_img.width  = 900
    xl_img.height = 330
    ws.add_image(xl_img, anchor_cell)
```

---

### 차트 8: 주요 소재 피로도 라인 차트
**시트**: 📅 일별 트렌드 | **위치**: 콤보 차트 아래

```python
def add_fatigue_line_chart(ws, df_daily, top_creatives, anchor_cell="A45"):
    """
    상위 5개 소재의 일별 CVR 추이
    → 시간이 지남에 따라 CVR이 떨어지면 소재 피로도 감지
    
    top_creatives: TIER1 + 비용 상위 소재 이름 리스트 (최대 5개)
    """
    fig, ax = plt.subplots(figsize=(14, 5))
    
    colors = ['#2ECC71', '#3498DB', '#E74C3C', '#F39C12', '#9B59B6']
    
    for i, creative_name in enumerate(top_creatives[:5]):
        mask = df_daily['소재명'] == creative_name
        grp  = df_daily[mask].groupby('date').agg(
            CVR=('CVR_calc', 'mean')
        ).reset_index().sort_values('date')
        
        if len(grp) < 3:
            continue
        
        label = creative_name[:12] + '…' if len(creative_name) > 12 else creative_name
        ax.plot(range(len(grp)), grp['CVR'],
               marker='o', markersize=4, linewidth=1.8,
               color=colors[i], label=label, alpha=0.85)
    
    ax.set_title('주요 소재 일별 CVR 추이 (피로도 감지)', 
                fontsize=11, fontweight='bold')
    ax.set_ylabel('CVR (%)', fontsize=10)
    ax.set_xlabel('집행일', fontsize=10)
    ax.legend(loc='upper right', fontsize=8)
    ax.grid(alpha=0.2)
    ax.axhline(5.0, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)
    ax.text(0.01, 5.1, 'CVR 기준선 (5%)', transform=ax.get_yaxis_transform(),
           fontsize=7, color='gray')
    
    plt.tight_layout()
    
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png', dpi=150, bbox_inches='tight')
    img_buf.seek(0)
    plt.close()
    
    xl_img = XLImage(img_buf)
    xl_img.width  = 900
    xl_img.height = 330
    ws.add_image(xl_img, anchor_cell)
```

---

## build_excel.py 통합 호출 구조

```python
# build_excel.py에 차트 호출 추가

from build_charts import (
    add_tier_donut,
    add_branch_cpa_bar,
    add_creative_bubble_chart,
    add_hook_comparison_chart,
    add_age_efficiency_chart,
    add_age_type_heatmap,
    add_daily_combo_chart,
    add_fatigue_line_chart,
)

def build_excel(data: dict, output_path: str):
    wb = openpyxl.Workbook()
    
    # ── 📊 요약 대시보드 ──────────────────────────────
    ws_summary = wb.active
    ws_summary.title = "📊 요약 대시보드"
    write_kpi_cards(ws_summary, data['summary'])
    write_branch_table(ws_summary, data['branch'])
    add_tier_donut(ws_summary, data['creative'])        # 차트 1
    add_branch_cpa_bar(ws_summary, data['branch'])      # 차트 2
    
    # ── 🎬 소재 TIER 분석 ─────────────────────────────
    ws_tier = wb.create_sheet("🎬 소재 TIER 분석")
    write_tier_table(ws_tier, data['creative'])
    add_creative_bubble_chart(ws_tier, data['creative'], anchor_cell="A35")  # 차트 3
    
    # ── 🔄 훅 개선 효과 ───────────────────────────────
    ws_hook = wb.create_sheet("🔄 훅 개선 효과")
    write_hook_table(ws_hook, data['hook_pairs'], data['type_comparison'])
    add_hook_comparison_chart(ws_hook, data['hook_pairs'], anchor_cell="I3")  # 차트 4
    
    # ── 🏢 지점 컨텍스트 ──────────────────────────────
    ws_branch = wb.create_sheet("🏢 지점 컨텍스트")
    write_branch_context(ws_branch, data['branch'])
    # (지점 컨텍스트는 차트 없이 테이블만)
    
    # ── 👥 나이대 분석 ────────────────────────────────
    ws_age = wb.create_sheet("👥 나이대 분석")
    write_age_table(ws_age, data['age'])
    add_age_efficiency_chart(ws_age, data['age'], anchor_cell="I3")       # 차트 5
    add_age_type_heatmap(ws_age, data['pivot_ctr'], 'CTR', anchor_cell="A20")  # 차트 6-1
    add_age_type_heatmap(ws_age, data['pivot_cvr'], 'CVR', anchor_cell="K20")  # 차트 6-2
    
    # ── 📅 일별 트렌드 ────────────────────────────────
    ws_daily = wb.create_sheet("📅 일별 트렌드")
    write_daily_table(ws_daily, data['daily'])
    add_daily_combo_chart(ws_daily, data['daily'], anchor_cell="A25")     # 차트 7
    top5 = data['creative'][data['creative']['TIER']=='TIER1']['소재명'].tolist()[:5]
    add_fatigue_line_chart(ws_daily, data['df_daily_raw'], top5, anchor_cell="A45")  # 차트 8
    
    # ── ⏸ OFF 소재 ────────────────────────────────────
    ws_off = wb.create_sheet("⏸ OFF 소재")
    write_off_table(ws_off, data['creative_off'])
    
    wb.save(output_path)
    print(f"[OK] Excel 저장: {output_path}")
```

---

## 필요 라이브러리

```bash
pip install openpyxl matplotlib seaborn --break-system-packages
```

```
라이브러리 역할:
  openpyxl  → Excel 파일 생성 + 기본 차트 (도넛, 막대)
  matplotlib → 복잡한 차트 이미지 생성 (버블, 콤보, 라인)
  seaborn    → 히트맵 (소재유형×나이대)
  io         → 이미지 버퍼 (파일 저장 없이 Excel에 직접 삽입)
```

---

## QA 체크리스트 (차트 추가분)

```
차트 렌더링
  □ Excel 파일 열었을 때 차트 8개가 모두 표시되는가?
  □ 버블 차트에 소재명 라벨이 겹치지 않고 읽히는가?
  □ 히트맵 숫자가 셀 안에 표시되는가?
  □ 일별 콤보 차트의 날짜 레이블이 겹치지 않는가?

데이터 정합성
  □ 도넛 차트의 TIER별 수가 테이블 합계와 일치하는가?
  □ 버블 차트에 LOW_VOLUME / UNCLASSIFIED 소재가 표시되지 않는가?
  □ 피로도 차트에 7일 미만 집행 소재가 포함되지 않는가?

예외 처리
  □ hook_pairs_df가 비어있을 때 훅 비교 차트가 스킵되는가?
  □ matplotlib 한글 폰트 깨짐 없는가?
     → plt.rcParams['font.family'] = 'NanumGothic' 설정 필요
```

---

## 한글 폰트 설정 (필수)

```python
# build_charts.py 최상단에 반드시 추가
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 한글 폰트 설정
plt.rcParams['font.family'] = 'NanumGothic'   # Linux
# plt.rcParams['font.family'] = 'AppleGothic'  # macOS
# plt.rcParams['font.family'] = 'Malgun Gothic' # Windows
plt.rcParams['axes.unicode_minus'] = False      # 마이너스 기호 깨짐 방지

# 폰트 없는 환경 대비 (서버 실행 시)
try:
    fm.findfont('NanumGothic', fallback_to_default=False)
except:
    # 폰트 없으면 영문으로 대체 처리
    plt.rcParams['font.family'] = 'DejaVu Sans'
    print("[WARNING] 한글 폰트 없음 → 영문 폰트로 대체")
```
