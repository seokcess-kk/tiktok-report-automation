"""
PDF 리포트 생성
설계서 섹션 8 기준

PDF 요약 (2페이지):
[Page 1]
  - 분석 기간 / 총 광고비 / 총 전환(상담신청) / 평균 CPA
  - TIER 분포 요약
  - 지점별 성과 요약 테이블
  - 핵심 인사이트 3줄

[Page 2]
  - 소재 TIER 분류 결과 (상위/하위 소재)
  - 훅 개선 효과 하이라이트
  - 이번 주 추천 액션 플랜
  - 이상 감지 알림 + 데이터 참고 사항
"""
import pandas as pd
import numpy as np
import os
from datetime import datetime

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("[WARNING] reportlab not installed -> pip install reportlab")


def register_korean_font():
    """한글 폰트 등록 (시스템에 있는 경우)"""
    font_paths = [
        'C:/Windows/Fonts/malgun.ttf',  # Windows
        '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',  # Linux
        '/System/Library/Fonts/AppleGothic.ttf',  # Mac
    ]

    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('Korean', font_path))
                return 'Korean'
            except:
                pass

    return None


def create_table_style():
    """테이블 스타일 생성"""
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F2F2F2')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#E8E8E8')]),
    ])


def build_pdf(output_dir: str, creative_df: pd.DataFrame, age_df: pd.DataFrame,
              df_valid: pd.DataFrame, off_df: pd.DataFrame = None,
              hook_type_df: pd.DataFrame = None, anomalies_df: pd.DataFrame = None):
    """
    PDF 리포트 생성 (2페이지)
    """
    if not REPORTLAB_AVAILABLE:
        print("[ERROR] reportlab not installed. pip install reportlab")
        return None

    # 출력 경로 설정
    os.makedirs(output_dir, exist_ok=True)
    today = datetime.now().strftime('%Y%m%d')
    output_path = os.path.join(output_dir, f"tiktok_summary_{today}.pdf")

    # PDF 문서 생성
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=15*mm,
        leftMargin=15*mm,
        topMargin=15*mm,
        bottomMargin=15*mm
    )

    # 스타일 설정
    styles = getSampleStyleSheet()
    korean_font = register_korean_font()

    if korean_font:
        title_style = ParagraphStyle(
            'TitleKorean',
            parent=styles['Heading1'],
            fontName=korean_font,
            fontSize=18,
            spaceAfter=10
        )
        normal_style = ParagraphStyle(
            'NormalKorean',
            parent=styles['Normal'],
            fontName=korean_font,
            fontSize=10,
            spaceAfter=5
        )
        heading_style = ParagraphStyle(
            'HeadingKorean',
            parent=styles['Heading2'],
            fontName=korean_font,
            fontSize=14,
            spaceAfter=8
        )
    else:
        title_style = styles['Heading1']
        normal_style = styles['Normal']
        heading_style = styles['Heading2']

    # 컨텐츠 빌드
    content = []

    # ===== PAGE 1 =====
    # 제목
    content.append(Paragraph("TikTok Ad Analysis Report", title_style))
    content.append(Spacer(1, 5*mm))

    # 기본 정보
    date_min = df_valid['date'].min().strftime('%Y-%m-%d')
    date_max = df_valid['date'].max().strftime('%Y-%m-%d')
    total_cost = df_valid['cost'].sum()
    total_conv = df_valid['conversions'].sum()
    avg_cpa = total_cost / total_conv if total_conv > 0 else 0

    info_text = f"""
    <b>Analysis Period:</b> {date_min} ~ {date_max}<br/>
    <b>Report Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}<br/>
    """
    content.append(Paragraph(info_text, normal_style))
    content.append(Spacer(1, 5*mm))

    # KPI 요약 테이블
    content.append(Paragraph("Overall KPI Summary", heading_style))

    kpi_data = [
        ['Metric', 'Value'],
        ['Total Ad Spend', f'{total_cost:,.0f} KRW'],
        ['Total Conversions', f'{total_conv:,.0f}'],
        ['Average CPA', f'{avg_cpa:,.0f} KRW'],
        ['Average CTR', f'{df_valid["clicks"].sum() / df_valid["impressions"].sum() * 100:.2f}%'],
        ['Average CVR', f'{total_conv / df_valid["clicks"].sum() * 100:.2f}%'],
    ]

    kpi_table = Table(kpi_data, colWidths=[80*mm, 80*mm])
    kpi_table.setStyle(create_table_style())
    content.append(kpi_table)
    content.append(Spacer(1, 8*mm))

    # TIER 분포
    content.append(Paragraph("TIER Distribution", heading_style))

    tier_dist = creative_df['TIER'].value_counts()
    tier_data = [['TIER', 'Count', 'Description']]
    tier_desc = {
        'TIER1': 'High Performance (CPA OK + CVR >= 5%)',
        'TIER2': 'High CTR but CPA Over',
        'TIER3': 'High Landing Rate but Low CVR',
        'TIER4': 'Below Average',
        'LOW_VOLUME': 'Insufficient Data',
        'UNCLASSIFIED': 'Less than 7 days'
    }
    for tier in ['TIER1', 'TIER2', 'TIER3', 'TIER4', 'LOW_VOLUME', 'UNCLASSIFIED']:
        if tier in tier_dist.index:
            tier_data.append([tier, str(tier_dist[tier]), tier_desc.get(tier, '')])

    tier_table = Table(tier_data, colWidths=[30*mm, 25*mm, 105*mm])
    tier_table.setStyle(create_table_style())
    content.append(tier_table)
    content.append(Spacer(1, 8*mm))

    # 지점별 성과 요약
    content.append(Paragraph("Branch Performance Summary", heading_style))

    branch_summary = df_valid.groupby('지점').agg(
        Cost=('cost', 'sum'),
        Conv=('conversions', 'sum'),
    ).reset_index()
    branch_summary['CPA'] = (branch_summary['Cost'] / branch_summary['Conv'].replace(0, np.nan)).round(0)
    branch_summary = branch_summary.sort_values('CPA')

    branch_data = [['Branch', 'Cost (KRW)', 'Conversions', 'CPA (KRW)']]
    for _, row in branch_summary.iterrows():
        branch_data.append([
            row['지점'],
            f"{row['Cost']:,.0f}",
            f"{row['Conv']:.0f}",
            f"{row['CPA']:,.0f}" if pd.notna(row['CPA']) else 'N/A'
        ])

    branch_table = Table(branch_data, colWidths=[35*mm, 45*mm, 35*mm, 45*mm])
    branch_table.setStyle(create_table_style())
    content.append(branch_table)

    # ===== PAGE 2 =====
    content.append(PageBreak())

    # Top/Bottom 소재
    content.append(Paragraph("Top Performing Creatives (TIER1)", heading_style))

    tier1 = creative_df[creative_df['TIER'] == 'TIER1'].nsmallest(5, 'CPA')
    if len(tier1) > 0:
        top_data = [['Creative', 'CPA', 'CVR', 'CTR']]
        for _, row in tier1.iterrows():
            name = row['소재명'][:25] + '...' if len(row['소재명']) > 25 else row['소재명']
            top_data.append([
                name,
                f"{row['CPA']:,.0f}" if pd.notna(row['CPA']) else 'N/A',
                f"{row['CVR']:.2f}%" if pd.notna(row['CVR']) else 'N/A',
                f"{row['CTR']:.2f}%" if pd.notna(row['CTR']) else 'N/A',
            ])

        top_table = Table(top_data, colWidths=[80*mm, 30*mm, 25*mm, 25*mm])
        top_table.setStyle(create_table_style())
        content.append(top_table)
    else:
        content.append(Paragraph("No TIER1 creatives found.", normal_style))

    content.append(Spacer(1, 8*mm))

    # 훅 개선 효과
    content.append(Paragraph("Hook Effect Summary", heading_style))

    if hook_type_df is not None and len(hook_type_df) > 0:
        hook_data = [['Creative Type', 'Original CTR', 'Reworked CTR', 'Change', 'Verdict']]
        for _, row in hook_type_df.iterrows():
            hook_data.append([
                row.get('소재유형', 'N/A'),
                f"{row.get('신규_CTR', 0):.2f}%" if pd.notna(row.get('신규_CTR')) else 'N/A',
                f"{row.get('재가공_CTR', 0):.2f}%" if pd.notna(row.get('재가공_CTR')) else 'N/A',
                f"{row.get('CTR_변화율', 0):+.1f}%" if pd.notna(row.get('CTR_변화율')) else 'N/A',
                str(row.get('훅판정', 'N/A'))[:30]
            ])

        hook_table = Table(hook_data, colWidths=[35*mm, 30*mm, 30*mm, 25*mm, 40*mm])
        hook_table.setStyle(create_table_style())
        content.append(hook_table)
    else:
        content.append(Paragraph("No hook comparison data available.", normal_style))

    content.append(Spacer(1, 8*mm))

    # 이상 감지 알림
    content.append(Paragraph("Anomaly Alerts", heading_style))

    if anomalies_df is not None and len(anomalies_df) > 0:
        alert_count = len(anomalies_df)
        content.append(Paragraph(f"Total {alert_count} anomalies detected. See Excel report for details.", normal_style))

        # 주요 이상치 유형별 카운트
        if '감지유형' in anomalies_df.columns:
            type_counts = anomalies_df['감지유형'].value_counts()
            for atype, count in type_counts.items():
                content.append(Paragraph(f"  - {atype}: {count} cases", normal_style))
    else:
        content.append(Paragraph("No anomalies detected.", normal_style))

    content.append(Spacer(1, 8*mm))

    # 데이터 참고 사항
    content.append(Paragraph("Data Notes", heading_style))

    notes = []
    if 'attribution_caution' in df_valid.columns:
        caution_count = df_valid['attribution_caution'].sum()
        if caution_count > 0:
            notes.append(f"- Attribution caution: {caution_count} rows (click=0, conversion>0)")

    if off_df is not None and len(off_df) > 0:
        notes.append(f"- OFF creatives: {len(off_df)} (excluded from TIER analysis)")

    low_vol = creative_df[creative_df['TIER'] == 'LOW_VOLUME']
    if len(low_vol) > 0:
        notes.append(f"- Low volume creatives: {len(low_vol)} (insufficient data for evaluation)")

    if notes:
        for note in notes:
            content.append(Paragraph(note, normal_style))
    else:
        content.append(Paragraph("No special notes.", normal_style))

    # PDF 빌드
    doc.build(content)
    print(f"[OK] PDF report generated -> {output_path}")

    return output_path


def main(data_dir: str = "output", output_dir: str = None):
    """
    메인 실행 함수
    """
    if output_dir is None:
        today = datetime.now().strftime('%Y%m%d')
        output_dir = os.path.join(data_dir, today)

    # 데이터 로드
    creative_df = pd.read_parquet(os.path.join(data_dir, "creative_tier.parquet"))
    print(f"[Load] Creative TIER: {len(creative_df)}")

    try:
        age_df = pd.read_parquet(os.path.join(data_dir, "age_analysis.parquet"))
    except FileNotFoundError:
        age_df = pd.DataFrame()

    try:
        off_df = pd.read_parquet(os.path.join(data_dir, "creative_off.parquet"))
    except FileNotFoundError:
        off_df = pd.DataFrame()

    try:
        df_valid = pd.read_parquet(os.path.join(data_dir, "parsed.parquet"))
        df_valid = df_valid[df_valid['parse_status'] == 'OK']
    except FileNotFoundError:
        print("[ERROR] parsed.parquet not found")
        return None

    try:
        hook_type_df = pd.read_parquet(os.path.join(data_dir, "hook_type_comparison.parquet"))
    except FileNotFoundError:
        hook_type_df = None

    try:
        anomalies_df = pd.read_csv(os.path.join(data_dir, "anomalies.csv"))
    except FileNotFoundError:
        anomalies_df = None

    return build_pdf(output_dir, creative_df, age_df, df_valid, off_df, hook_type_df, anomalies_df)


if __name__ == "__main__":
    import sys
    data_directory = sys.argv[1] if len(sys.argv) > 1 else "output"
    output_directory = sys.argv[2] if len(sys.argv) > 2 else None
    main(data_directory, output_directory)
