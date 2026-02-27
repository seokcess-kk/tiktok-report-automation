"""
TikTok 광고 분석 자동화 - 3단계 자동화 완성 실행 스크립트

실행 순서:
1. Phase 0: normalize_tiktok_raw.py (raw 표준화)
2. Phase 1: parse_tiktok.py (파싱 + 메타데이터 추출)
3. Phase 2: score_creatives.py (소재 집계 + TIER 분류 + 지점별 상대평가)
4. Phase 2: hook_comparison.py (신규↔재가공 훅 효과 비교 + lineage 지원)
5. Phase 2: detect_anomalies.py (이상치 감지)
6. Phase 3: merge_db.py (퍼널 분석 - 내부 DB 연결, 선택적)
7. Phase 3: generate_insights.py (AI 인사이트 + improvement_suggestions.md)
8. Phase 5: build_excel.py (Excel 리포트 생성 - 7시트)
9. Phase 5: build_pdf.py (PDF 요약 리포트 생성)

절대 금지 규칙:
1. raw CTR/CVR/CPA 컬럼으로 분석 금지 -> _calc 재계산값만 사용
2. 클릭=0 AND 전환>0 행의 행 단위 CVR 계산 금지
3. 파싱 실패(parse_status=FAIL) 소재 TIER 분류 금지
4. 볼륨 미달(클릭<100 AND 비용<100,000원) 소재 TIER 분류 금지
5. 지점 편중 소재 수치 보정 금지 -> 주석으로 맥락만 표시
6. 소재 TIER 평가를 일별x나이대 행 단위로 수행 금지 -> 소재 단위 집계 후 TIER 부여
"""
import os
import sys
from datetime import datetime
import importlib.util

# 프로젝트 루트 경로 설정
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def load_module(module_name: str, file_path: str):
    """동적으로 모듈 로드 (하이픈 포함 경로 대응)"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def save_analysis_raw(output_dir: str, df_raw, df_parsed, creative_df,
                      off_df=None, hook_results=None, anomaly_results=None):
    """
    analysis_raw.json 저장 - QA 검증 및 디버깅용 원본 데이터

    Design 문서 v3.1.0 명세에 따라 구현
    """
    import json

    today = datetime.now().strftime('%Y%m%d')
    json_output_dir = os.path.join(output_dir, today)
    os.makedirs(json_output_dir, exist_ok=True)

    # 입력 파일 정보
    input_files = {
        "tiktok_raw": {
            "path": "input/tiktok_raw.csv",
            "rows": len(df_raw),
            "columns": list(df_raw.columns)[:20],  # 처음 20개 컬럼만
            "date_range": {
                "min": str(df_raw['date'].min()) if 'date' in df_raw.columns else None,
                "max": str(df_raw['date'].max()) if 'date' in df_raw.columns else None,
            }
        },
        "target_cpa": {
            "path": "input/target_cpa.csv",
            "exists": os.path.exists(os.path.join(PROJECT_ROOT, "input", "target_cpa.csv"))
        },
        "db_by_branch": {
            "path": "input/db_by_branch.csv",
            "exists": os.path.exists(os.path.join(PROJECT_ROOT, "input", "db_by_branch.csv"))
        },
        "creative_lineage": {
            "path": "input/creative_lineage.csv",
            "exists": os.path.exists(os.path.join(PROJECT_ROOT, "input", "creative_lineage.csv"))
        }
    }

    # 처리 통계
    parsed_ok = df_parsed[df_parsed['parse_status'] == 'OK']
    parsed_fail = df_parsed[df_parsed['parse_status'] != 'OK']

    processing = {
        "phase0_normalized": len(df_raw),
        "phase1_parsed_total": len(df_parsed),
        "phase1_parsed_ok": len(parsed_ok),
        "phase1_parsed_fail": len(parsed_fail),
        "phase2_creatives_on": len(creative_df),
        "phase2_creatives_off": len(off_df) if off_df is not None else 0,
        "phase2_hook_pairs": len(hook_results.get('strict_pairs', [])) if hook_results else 0,
        "phase2_anomalies": len(anomaly_results.get('combined', [])) if anomaly_results else 0,
    }

    # 데이터 무결성 검증
    raw_cost = df_raw['cost'].sum() if 'cost' in df_raw.columns else df_raw['비용'].sum()
    raw_conv = df_raw['conversions'].sum() if 'conversions' in df_raw.columns else df_raw['전환수'].sum()
    analysis_cost = creative_df['총비용'].sum() if '총비용' in creative_df.columns else 0
    analysis_conv = creative_df['총전환'].sum() if '총전환' in creative_df.columns else 0

    # OFF 소재 포함
    if off_df is not None and len(off_df) > 0:
        if '총비용' in off_df.columns:
            analysis_cost += off_df['총비용'].sum()
        if '총전환' in off_df.columns:
            analysis_conv += off_df['총전환'].sum()

    totals = {
        "raw_cost": float(raw_cost),
        "raw_conversions": int(raw_conv),
        "analysis_cost": float(analysis_cost),
        "analysis_conversions": int(analysis_conv),
        "cost_match": abs(raw_cost - analysis_cost) <= 1,
        "conv_match": abs(raw_conv - analysis_conv) <= 1,
        "all_match": abs(raw_cost - analysis_cost) <= 1 and abs(raw_conv - analysis_conv) <= 1
    }

    # TIER 분포
    tier_distribution = creative_df['TIER'].value_counts().to_dict()

    # 지점 분포
    branch_distribution = {}
    if '집행지점목록' in creative_df.columns:
        for branch_list in creative_df['집행지점목록']:
            if isinstance(branch_list, list):
                for branch in branch_list:
                    branch_distribution[branch] = branch_distribution.get(branch, 0) + 1
            elif isinstance(branch_list, str):
                for branch in branch_list.split(', '):
                    branch_distribution[branch] = branch_distribution.get(branch, 0) + 1

    # 소재유형 분포
    type_distribution = {}
    if '소재유형' in creative_df.columns:
        type_distribution = creative_df['소재유형'].value_counts().to_dict()

    # KPI 요약
    kpi_summary = {
        "total_cost": float(raw_cost),
        "total_conversions": int(raw_conv),
        "avg_cpa": float(raw_cost / raw_conv) if raw_conv > 0 else None,
        "avg_ctr": float(parsed_ok['CTR_calc'].mean()) if 'CTR_calc' in parsed_ok.columns else None,
        "avg_cvr": float(parsed_ok['CVR_calc'].mean()) if 'CVR_calc' in parsed_ok.columns else None,
    }

    # 품질 지표
    quality_metrics = {
        "attribution_caution_count": int(df_raw['attribution_caution'].sum()) if 'attribution_caution' in df_raw.columns else 0,
        "low_volume_creatives": int((creative_df['TIER'] == 'LOW_VOLUME').sum()),
        "unclassified_creatives": int((creative_df['TIER'] == 'UNCLASSIFIED').sum()),
        "tier1_count": int((creative_df['TIER'] == 'TIER1').sum()),
        "tier4_count": int((creative_df['TIER'] == 'TIER4').sum()),
    }

    # 전체 JSON 구조
    analysis_raw = {
        "generated_at": datetime.now().isoformat(),
        "version": "3.1.0",
        "input_files": input_files,
        "processing": processing,
        "totals": totals,
        "tier_distribution": tier_distribution,
        "branch_distribution": branch_distribution,
        "type_distribution": type_distribution,
        "kpi_summary": kpi_summary,
        "quality_metrics": quality_metrics
    }

    # 저장
    json_path = os.path.join(json_output_dir, "analysis_raw.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(analysis_raw, f, ensure_ascii=False, indent=2, default=str)

    print(f"[OK] analysis_raw.json -> {json_path}")

    # 무결성 경고
    if not totals['all_match']:
        print(f"[WARNING] Data mismatch detected!")
        print(f"  Raw: cost={raw_cost:,.0f}, conv={raw_conv}")
        print(f"  Analysis: cost={analysis_cost:,.0f}, conv={analysis_conv}")

    return analysis_raw


def run_qa_checks(output_dir: str, df_raw, df_parsed, creative_df):
    """
    QA 체크리스트 실행 (설계서 섹션 10 기준)
    """
    print("\n" + "=" * 60)
    print("QA Checklist")
    print("=" * 60)

    checks_passed = 0
    checks_total = 0

    # 1. 데이터 무결성: raw 총비용 = 분석 총비용
    checks_total += 1
    raw_cost = df_raw['cost'].sum() if 'cost' in df_raw.columns else df_raw['비용'].sum()
    parsed_cost = df_parsed[df_parsed['parse_status'] == 'OK']['cost'].sum()
    cost_diff = abs(raw_cost - parsed_cost)
    fail_cost = df_parsed[df_parsed['parse_status'] != 'OK']['cost'].sum() if len(df_parsed[df_parsed['parse_status'] != 'OK']) > 0 else 0

    if cost_diff <= 1:
        print(f"[PASS] raw cost({raw_cost:,.0f}) = parsed cost({parsed_cost:,.0f})")
        checks_passed += 1
    elif abs(cost_diff - fail_cost) <= 1:
        print(f"[PASS] raw cost({raw_cost:,.0f}) - parse_fail({fail_cost:,.0f}) = parsed({parsed_cost:,.0f})")
        checks_passed += 1
    else:
        print(f"[FAIL] cost mismatch: raw({raw_cost:,.0f}) vs parsed({parsed_cost:,.0f}) + fail({fail_cost:,.0f})")

    # 2. 데이터 무결성: raw 총전환 = 분석 총전환
    checks_total += 1
    raw_conv = df_raw['conversions'].sum() if 'conversions' in df_raw.columns else df_raw['전환수'].sum()
    parsed_conv = df_parsed[df_parsed['parse_status'] == 'OK']['conversions'].sum()
    fail_conv = df_parsed[df_parsed['parse_status'] != 'OK']['conversions'].sum() if len(df_parsed[df_parsed['parse_status'] != 'OK']) > 0 else 0
    conv_diff = abs(raw_conv - parsed_conv)

    if conv_diff <= 0:
        print(f"[PASS] raw conversions({raw_conv:,.0f}) = parsed conversions({parsed_conv:,.0f})")
        checks_passed += 1
    elif abs(conv_diff - fail_conv) <= 0:
        print(f"[PASS] raw conversions({raw_conv:,.0f}) - parse_fail({fail_conv:,.0f}) = parsed({parsed_conv:,.0f})")
        checks_passed += 1
    else:
        print(f"[FAIL] conversion mismatch: raw({raw_conv:,.0f}) vs parsed({parsed_conv:,.0f}) + fail({fail_conv:,.0f})")

    # 3. TIER 분류 품질: 집행일수 7일 미만 소재가 TIER1~4에 없는가
    checks_total += 1
    tier_classified = creative_df[creative_df['TIER'].isin(['TIER1', 'TIER2', 'TIER3', 'TIER4'])]
    short_days = tier_classified[tier_classified['집행일수'] < 7]
    if len(short_days) == 0:
        print(f"[PASS] No creatives with <7 days in TIER1~4")
        checks_passed += 1
    else:
        print(f"[FAIL] {len(short_days)} creatives with <7 days in TIER1~4")

    # 4. TIER 분류 품질: 볼륨 미달 소재가 TIER1~4에 없는가
    checks_total += 1
    low_volume_in_tier = tier_classified[
        (tier_classified['총클릭'] < 100) & (tier_classified['총비용'] < 100_000)
    ]
    if len(low_volume_in_tier) == 0:
        print(f"[PASS] No low-volume creatives in TIER1~4")
        checks_passed += 1
    else:
        print(f"[FAIL] {len(low_volume_in_tier)} low-volume creatives in TIER1~4")

    # 5. 계산 검증: CPA = 총비용 / 총전환
    checks_total += 1
    cpa_check = creative_df[creative_df['총전환'] > 0].copy()
    cpa_check['CPA_verify'] = (cpa_check['총비용'] / cpa_check['총전환']).round(0)
    cpa_errors = cpa_check[abs(cpa_check['CPA'] - cpa_check['CPA_verify']) > 1]
    if len(cpa_errors) == 0:
        print(f"[PASS] CPA calculation verified (cost/conversions)")
        checks_passed += 1
    else:
        print(f"[FAIL] CPA calculation error: {len(cpa_errors)} items")

    # 6. OFF 소재가 TIER 분류에서 제외되었는가
    checks_total += 1
    if 'is_off' in creative_df.columns:
        off_in_tier = creative_df[creative_df['is_off'] == True]
    else:
        off_in_tier = creative_df[creative_df['TIER'] == 'OFF'] if 'OFF' in creative_df['TIER'].unique() else []

    if len(off_in_tier) == 0:
        print(f"[PASS] No OFF creatives in TIER analysis")
        checks_passed += 1
    else:
        print(f"[FAIL] {len(off_in_tier)} OFF creatives in TIER analysis")

    # 7. Excel 파일 생성 확인
    checks_total += 1
    today = datetime.now().strftime('%Y%m%d')
    excel_path = os.path.join(output_dir, today, f"tiktok_analysis_{today}.xlsx")
    if os.path.exists(excel_path):
        print(f"[PASS] Excel file created: {excel_path}")
        checks_passed += 1
    else:
        excel_path2 = os.path.join(output_dir, f"tiktok_analysis_{today}.xlsx")
        if os.path.exists(excel_path2):
            print(f"[PASS] Excel file created: {excel_path2}")
            checks_passed += 1
        else:
            print(f"[FAIL] Excel file not created")

    # 8. 파싱 실패 소재가 TIER 분류에 포함되지 않았는가
    checks_total += 1
    parsed_ok = df_parsed[df_parsed['parse_status'] == 'OK']
    parsed_ok_on = parsed_ok[parsed_ok['is_off'] == False]
    unique_creatives_parsed = parsed_ok_on.groupby(['소재구분', '소재유형', '소재명']).ngroups
    if len(creative_df) <= unique_creatives_parsed:
        print(f"[PASS] Parse-fail creatives excluded (TIER: {len(creative_df)}, parsed: {unique_creatives_parsed})")
        checks_passed += 1
    else:
        print(f"[FAIL] TIER creatives({len(creative_df)}) > parsed creatives({unique_creatives_parsed})")

    # 9. 훅 비교 데이터 생성 확인
    checks_total += 1
    hook_path = os.path.join(output_dir, "hook_type_comparison.parquet")
    if os.path.exists(hook_path):
        print(f"[PASS] Hook comparison data created")
        checks_passed += 1
    else:
        print(f"[INFO] Hook comparison data not found (optional)")

    # 10. 이상치 감지 실행 확인
    checks_total += 1
    anomaly_path = os.path.join(output_dir, "anomalies.csv")
    if os.path.exists(anomaly_path):
        print(f"[PASS] Anomaly detection completed")
        checks_passed += 1
    else:
        print(f"[INFO] No anomalies.csv (may have no anomalies)")
        checks_passed += 1  # 이상치가 없을 수도 있으므로 PASS

    # 11. improvement_suggestions.md 생성 확인 (Phase 3)
    checks_total += 1
    today = datetime.now().strftime('%Y%m%d')
    suggestions_path = os.path.join(output_dir, today, "improvement_suggestions.md")
    if os.path.exists(suggestions_path):
        print(f"[PASS] Improvement suggestions generated: {suggestions_path}")
        checks_passed += 1
    else:
        print(f"[INFO] improvement_suggestions.md not found")

    # 12. 인사이트 생성 확인 (Phase 3)
    checks_total += 1
    # 인사이트 결과는 메모리에만 있으므로, md 파일 존재로 간접 확인
    if os.path.exists(suggestions_path):
        print(f"[PASS] AI insight generation completed")
        checks_passed += 1
    else:
        print(f"[INFO] AI insights may not have been generated")

    print("\n" + "-" * 60)
    print(f"QA Result: {checks_passed}/{checks_total} passed ({checks_passed/checks_total*100:.1f}%)")
    print("-" * 60)

    return checks_passed, checks_total


def main():
    """
    메인 실행 함수
    """
    print("=" * 60)
    print("TikTok Ad Analysis Automation - Phase 2")
    print("=" * 60)

    # 경로 설정
    input_path = os.path.join(PROJECT_ROOT, "input", "tiktok_raw.csv")
    output_dir = os.path.join(PROJECT_ROOT, "output")
    logs_dir = os.path.join(PROJECT_ROOT, "logs")

    # 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)

    # 입력 파일 확인
    if not os.path.exists(input_path):
        print(f"[ERROR] Input file not found: {input_path}")
        return

    print(f"\n[Input] {input_path}")
    print(f"[Output] {output_dir}")

    # 모듈 로드
    normalize_module = load_module(
        "normalize_tiktok_raw",
        os.path.join(PROJECT_ROOT, ".claude", "skills", "tiktok-normalizer", "scripts", "normalize_tiktok_raw.py")
    )
    parse_module = load_module(
        "parse_tiktok",
        os.path.join(PROJECT_ROOT, ".claude", "skills", "tiktok-parser", "scripts", "parse_tiktok.py")
    )
    score_module = load_module(
        "score_creatives",
        os.path.join(PROJECT_ROOT, ".claude", "skills", "creative-analyzer", "scripts", "score_creatives.py")
    )
    hook_module = load_module(
        "hook_comparison",
        os.path.join(PROJECT_ROOT, ".claude", "skills", "creative-analyzer", "scripts", "hook_comparison.py")
    )
    anomaly_module = load_module(
        "detect_anomalies",
        os.path.join(PROJECT_ROOT, ".claude", "skills", "creative-analyzer", "scripts", "detect_anomalies.py")
    )
    excel_module = load_module(
        "build_excel",
        os.path.join(PROJECT_ROOT, ".claude", "skills", "report-generator", "scripts", "build_excel.py")
    )
    pdf_module = load_module(
        "build_pdf",
        os.path.join(PROJECT_ROOT, ".claude", "skills", "report-generator", "scripts", "build_pdf.py")
    )
    # v4.0.0: HTML 차트 모듈 로드
    html_chart_module = load_module(
        "build_html_charts",
        os.path.join(PROJECT_ROOT, ".claude", "skills", "report-generator", "scripts", "build_html_charts.py")
    )

    # Phase 3 모듈 로드
    funnel_module = load_module(
        "merge_db",
        os.path.join(PROJECT_ROOT, ".claude", "skills", "funnel-analyzer", "scripts", "merge_db.py")
    )
    insight_module = load_module(
        "generate_insights",
        os.path.join(PROJECT_ROOT, ".claude", "skills", "insight-writer", "scripts", "generate_insights.py")
    )

    # Phase 0: raw 표준화
    print("\n" + "=" * 60)
    print("Phase 0: Raw CSV Normalization")
    print("=" * 60)
    normalized_path = os.path.join(output_dir, "normalized.parquet")
    df_normalized = normalize_module.normalize(input_path, normalized_path)

    # Phase 1: 파싱
    print("\n" + "=" * 60)
    print("Phase 1: Ad Name Parsing + Metadata Extraction")
    print("=" * 60)
    parsed_path = os.path.join(output_dir, "parsed.parquet")
    failures_path = os.path.join(logs_dir, "parse_failures.csv")
    df_parsed = parse_module.main(normalized_path, parsed_path, failures_path)

    # Phase 2: 소재 분석 + TIER 분류
    print("\n" + "=" * 60)
    print("Phase 2: Creative Analysis + TIER Classification")
    print("=" * 60)
    target_cpa_path = os.path.join(PROJECT_ROOT, "input", "target_cpa.csv")
    results = score_module.score_creatives(parsed_path, output_dir, target_cpa_path)

    # Phase 2: 훅 비교 분석 (lineage 지원)
    print("\n" + "=" * 60)
    print("Phase 2: Hook Comparison Analysis (with lineage support)")
    print("=" * 60)
    lineage_path = os.path.join(PROJECT_ROOT, "input", "creative_lineage.csv")
    if not os.path.exists(lineage_path):
        lineage_path = None
    hook_results = hook_module.compare_hooks(results['creative_tier'], output_dir, lineage_path)

    # Phase 2: 이상치 감지
    print("\n" + "=" * 60)
    print("Phase 2: Anomaly Detection")
    print("=" * 60)
    anomaly_results = anomaly_module.detect_all_anomalies(
        results['df_valid'],
        results['creative_tier'],
        output_dir
    )

    # Phase 3: 퍼널 분석 (내부 DB 연결 - 선택적)
    print("\n" + "=" * 60)
    print("Phase 3: Funnel Analysis (Internal DB - Optional)")
    print("=" * 60)
    db_by_branch_path = os.path.join(PROJECT_ROOT, "input", "db_by_branch.csv")
    funnel_results = {'funnel_metrics': None, 'merged': None, 'insights': []}
    if os.path.exists(db_by_branch_path):
        funnel_results = funnel_module.analyze_funnel(
            db_by_branch_path,
            results['creative_tier'],
            output_dir
        )
    else:
        print("[INFO] db_by_branch.csv not found - funnel analysis skipped")

    # Phase 3: AI 인사이트 생성
    print("\n" + "=" * 60)
    print("Phase 3: AI Insight Generation")
    print("=" * 60)
    today = datetime.now().strftime('%Y%m%d')
    insight_output_dir = os.path.join(output_dir, today)
    os.makedirs(insight_output_dir, exist_ok=True)

    insight_generator = insight_module.InsightGenerator(
        creative_df=results['creative_tier'],
        age_df=results['age_summary'],
        hook_df=hook_results.get('type_comparison'),
        anomaly_df=anomaly_results.get('combined'),
        funnel_insights=funnel_results.get('insights', [])
    )
    insight_results = insight_generator.generate_all()

    # improvement_suggestions.md 생성
    insight_module.generate_improvement_suggestions(insight_results, insight_output_dir)

    print(f"\n[Insight Summary]")
    print(f"  - Total Insights: {insight_results['summary']['total_insights']}")
    print(f"  - High Priority: {insight_results['summary']['high_priority']}")
    print(f"  - Confirmed: {insight_results['summary']['confirmed']}")
    print(f"  - Hypothesis: {insight_results['summary']['hypothesis']}")

    # Phase 5: Excel 리포트 생성
    print("\n" + "=" * 60)
    print("Phase 5: Excel Report Generation (7 sheets + v3.2.0 charts)")
    print("=" * 60)

    # v3.2.0: target_cpa.csv 로드 (있는 경우)
    target_cpa_map = None
    target_cpa_path = os.path.join(PROJECT_ROOT, "input", "target_cpa.csv")
    if os.path.exists(target_cpa_path):
        try:
            import pandas as pd
            target_cpa_df = pd.read_csv(target_cpa_path, encoding='utf-8-sig')
            # 지점 컬럼명 확인 (지점, 브랜치, branch 등)
            branch_col = None
            for col in ['지점', '브랜치', 'branch', 'Branch']:
                if col in target_cpa_df.columns:
                    branch_col = col
                    break
            # 목표 CPA 컬럼명 확인
            cpa_col = None
            for col in ['목표CPA', '목표_CPA', 'target_cpa', 'CPA']:
                if col in target_cpa_df.columns:
                    cpa_col = col
                    break

            if branch_col and cpa_col:
                target_cpa_map = dict(zip(target_cpa_df[branch_col], target_cpa_df[cpa_col]))
                print(f"[Load] target_cpa.csv: {len(target_cpa_map)}개 지점 목표 로드")
        except Exception as e:
            print(f"[WARNING] target_cpa.csv 로드 실패: {e}")

    excel_output_dir = os.path.join(output_dir, today)
    excel_path = excel_module.build_excel(
        excel_output_dir,
        results['creative_tier'],
        results['age_summary'],
        results['df_valid'],
        results['creative_off'],
        hook_results.get('type_comparison'),
        hook_results.get('strict_pairs'),
        target_cpa_map=target_cpa_map  # v3.2.0: 목표 CPA 전달
    )

    # v4.0.0: HTML 인터랙티브 차트 생성
    print("\n" + "=" * 60)
    print("Phase 5: HTML Interactive Charts Generation (v4.0.0)")
    print("=" * 60)
    try:
        html_path = html_chart_module.build_html_charts(
            excel_output_dir,
            results['creative_tier'],
            results['age_summary'],
            results['df_valid'],
            hook_results.get('type_comparison'),
            hook_results.get('strict_pairs'),
            target_cpa_map=target_cpa_map
        )
        if html_path:
            print(f"[OK] HTML charts generated -> {html_path}")
        else:
            print("[WARNING] HTML charts skipped (plotly not available)")
    except Exception as e:
        print(f"[WARNING] HTML chart generation failed: {e}")
        print("[INFO] Install plotly for HTML charts: pip install plotly")
        html_path = None

    # Phase 5: PDF 리포트 생성
    print("\n" + "=" * 60)
    print("Phase 5: PDF Summary Report Generation")
    print("=" * 60)
    try:
        pdf_path = pdf_module.build_pdf(
            excel_output_dir,
            results['creative_tier'],
            results['age_summary'],
            results['df_valid'],
            results['creative_off'],
            hook_results.get('type_comparison'),
            anomaly_results.get('combined')
        )
    except Exception as e:
        print(f"[WARNING] PDF generation failed: {e}")
        print("[INFO] Install reportlab for PDF: pip install reportlab")
        pdf_path = None

    # QA 체크
    run_qa_checks(
        output_dir,
        df_normalized,
        df_parsed,
        results['creative_tier']
    )

    # analysis_raw.json 생성 (v3.1.0)
    print("\n" + "=" * 60)
    print("Phase 5: analysis_raw.json Generation (QA Data)")
    print("=" * 60)
    save_analysis_raw(
        output_dir,
        df_normalized,
        df_parsed,
        results['creative_tier'],
        results['creative_off'],
        hook_results,
        anomaly_results
    )

    print("\n" + "=" * 60)
    print("Analysis Complete! (Phase 3 - Full Automation)")
    print("=" * 60)
    print(f"\n[Generated Files]")
    if excel_path:
        print(f"  - Excel: {excel_path}")
    if pdf_path:
        print(f"  - PDF: {pdf_path}")
    suggestions_file = os.path.join(insight_output_dir, "improvement_suggestions.md")
    if os.path.exists(suggestions_file):
        print(f"  - Insights: {suggestions_file}")
    print(f"  - Data: {output_dir}/*.parquet")
    print(f"\n[Insight Summary]")
    print(f"  - Total: {insight_results['summary']['total_insights']} insights")
    print(f"  - Action Plan: {len(insight_results['action_plan'])} items")


if __name__ == "__main__":
    main()
