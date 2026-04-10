"""
Legal AI Agent — Streamlit アプリケーション (app.py)

建築法規チェック・契約書レビュー・判例リサーチ・条文検索を
ルールベース＋e-Gov API で実現するツール。

弁護士法72条に抵触しない「事務補助・リスク指摘ツール」として設計。
"""

import os
import tempfile
from datetime import datetime

import streamlit as st

from regulation_checker import RegulationChecker, ProjectInfo, RegulationReport
from contract_analyzer import ContractAnalyzer, ContractReport
from case_law_scraper import CaseLawScraper
from case_law_db import CaseLawDB
from law_tools import EgovClient
from checklists import (
    ALL_ZONES,
    ALL_USES,
    CASE_LAW_CATEGORIES,
)


# ---------------------------------------------------------------------------
# ページ設定
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Legal AI Agent — 建築法規チェック",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ---------------------------------------------------------------------------
# カスタムCSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;600;700&display=swap');

    * { font-family: 'Noto Sans JP', sans-serif; }

    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
        color: #e2e8f0;
    }

    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #60a5fa, #a78bfa, #f472b6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
    }

    .sub-title {
        text-align: center;
        color: #94a3b8;
        font-size: 0.95rem;
        margin-bottom: 2rem;
    }

    .disclaimer {
        background: rgba(245, 158, 11, 0.1);
        border-left: 4px solid #f59e0b;
        padding: 0.75rem 1rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 1.5rem;
        font-size: 0.85rem;
        color: #fbbf24;
    }

    .metric-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(148, 163, 184, 0.15);
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        backdrop-filter: blur(10px);
        transition: transform 0.2s;
    }
    .metric-card:hover { transform: translateY(-2px); }
    .metric-value { font-size: 2rem; font-weight: 700; color: #60a5fa; }
    .metric-label { font-size: 0.85rem; color: #94a3b8; margin-top: 0.3rem; }

    .result-card {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(148, 163, 184, 0.1);
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
    }

    .risk-high { border-left: 4px solid #ef4444; }
    .risk-medium { border-left: 4px solid #f59e0b; }
    .risk-low { border-left: 4px solid #22c55e; }

    .status-pass {
        background: rgba(34, 197, 94, 0.15); color: #22c55e;
        padding: 2px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: 600;
    }
    .status-fail {
        background: rgba(239, 68, 68, 0.15); color: #ef4444;
        padding: 2px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: 600;
    }
    .status-warn {
        background: rgba(245, 158, 11, 0.15); color: #f59e0b;
        padding: 2px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: 600;
    }
    .status-na {
        background: rgba(148, 163, 184, 0.15); color: #94a3b8;
        padding: 2px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: 600;
    }

    .article-text {
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(71, 85, 105, 0.3);
        border-radius: 8px;
        padding: 1rem;
        font-size: 0.85rem;
        color: #cbd5e1;
        line-height: 1.8;
        white-space: pre-wrap;
    }

    /* タブのスタイル */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: rgba(30, 41, 59, 0.6);
        border-radius: 10px;
        padding: 0.5rem 1rem;
        color: #94a3b8;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #3b82f6, #8b5cf6);
        color: white;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# ヘッダー
# ---------------------------------------------------------------------------
st.markdown('<div class="main-title">⚖️ Legal AI Agent</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">建築法規チェック・契約書レビュー・判例リサーチ・条文検索</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="disclaimer">'
    '⚠️ 本ツールは法的助言を提供するものではありません。'
    '弁護士法第72条に基づき、法律事務は弁護士のみが行えます。'
    '本ツールはリスク指摘・情報整理の補助ツールとしてご利用ください。'
    '</div>',
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# グローバル初期化
# ---------------------------------------------------------------------------
egov_client = EgovClient()
case_db = CaseLawDB()


# ---------------------------------------------------------------------------
# ヘルパー関数（タブ定義の前に配置）
# ---------------------------------------------------------------------------

def _generate_regulation_markdown(report: RegulationReport) -> str:
    """法規チェックレポートをMarkdown形式で生成する。"""
    lines = [
        f"# 法規チェックレポート",
        f"",
        f"- プロジェクト名: {report.project.project_name}",
        f"- 用途: {report.project.use_type}",
        f"- 用途地域: {report.project.zone_type}",
        f"- 敷地面積: {report.project.site_area} ㎡",
        f"- 延床面積: {report.project.total_floor_area} ㎡",
        f"- 高さ: {report.project.height} m",
        f"- チェック日: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"",
        f"## 結果サマリー",
        f"",
    ]
    counts = report.count_by_status()
    for status, count in counts.items():
        lines.append(f"- {status}: {count} 件")

    lines.append(f"")
    lines.append(f"## 詳細結果")
    lines.append(f"")

    for r in report.results:
        icon = {"適合": "✅", "不適合": "❌", "要確認": "⚠️", "該当なし": "➖"}.get(
            r.status, "❓"
        )
        lines.append(f"### {icon} [{r.status}] {r.category} — {r.subcategory}")
        lines.append(f"")
        lines.append(f"- 法令参照: {r.law_reference}")
        lines.append(f"- 判定: {r.detail}")
        if r.note:
            lines.append(f"- 補足: {r.note}")
        lines.append(f"")

    lines.append(f"---")
    lines.append(f"*Generated by Legal AI Agent*")
    return "\n".join(lines)


def _generate_contract_markdown(report: ContractReport) -> str:
    """契約書レビューレポートをMarkdown形式で生成する。"""
    lines = [
        f"# 契約書レビューレポート",
        f"",
        f"- ファイル名: {report.file_name}",
        f"- 契約タイプ: {report.contract_type}",
        f"- 条項数: {report.total_clauses}",
        f"- レビュー日: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"",
        f"## 結果サマリー",
        f"",
    ]
    counts = report.count_by_risk()
    for status, count in counts.items():
        lines.append(f"- {status}: {count} 件")

    if report.missing_items:
        lines.append(f"")
        lines.append(f"## ⚠️ 建設業法19条 欠落項目")
        for item in report.missing_items:
            lines.append(f"- ❌ {item}")

    lines.append(f"")
    lines.append(f"## 詳細結果")
    lines.append(f"")

    for r in report.risks:
        icon = {"問題あり": "🔴", "記載なし": "⚠️", "確認推奨": "🟡", "OK": "✅"}.get(
            r.status, "❓"
        )
        lines.append(f"### {icon} [{r.status}] {r.category} — {r.item}")
        lines.append(f"")
        lines.append(f"- リスク: {r.risk_level}")
        lines.append(f"- 詳細: {r.description}")
        if r.advice:
            lines.append(f"- 💡 アドバイス: {r.advice}")
        if r.matched_text:
            lines.append(f"- 📌 該当箇所: {r.matched_text[:100]}...")
        lines.append(f"")

    lines.append(f"---")
    lines.append(f"*Generated by Legal AI Agent*")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# タブ
# ---------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "🏗️ 建築法規チェック",
    "📝 契約書レビュー",
    "⚖️ 判例リサーチ",
    "📖 条文検索",
])


# ===========================================================================
# Tab 1: 建築法規チェック
# ===========================================================================
with tab1:
    st.markdown("### 🏗️ 建築法規チェック")
    st.caption("プロジェクト情報を入力すると、関連法規の適合性を網羅的にチェックします。")

    with st.form("regulation_form"):
        col1, col2 = st.columns(2)

        with col1:
            project_name = st.text_input(
                "プロジェクト名",
                placeholder="例: ○○ビル新築工事",
            )
            use_type = st.selectbox("用途", ALL_USES)
            zone_type = st.selectbox("用途地域", ALL_ZONES)
            fire_zone = st.selectbox(
                "防火地域",
                ["指定なし", "防火地域", "準防火地域"],
            )
            structure = st.selectbox(
                "構造種別", ["RC造", "S造", "SRC造", "W造", "その他"]
            )

        with col2:
            site_area = st.number_input("敷地面積 (㎡)", min_value=0.0, step=10.0)
            building_area = st.number_input("建築面積 (㎡)", min_value=0.0, step=10.0)
            total_floor_area = st.number_input("延床面積 (㎡)", min_value=0.0, step=10.0)
            road_width = st.number_input("前面道路幅員 (m)", min_value=0.0, step=0.5)
            floors_above = st.number_input("地上階数", min_value=0, step=1)
            floors_below = st.number_input("地下階数", min_value=0, step=1)
            height = st.number_input("建物高さ (m)", min_value=0.0, step=0.5)
            eave_height = st.number_input("軒高 (m)", min_value=0.0, step=0.5)

        col3, col4 = st.columns(2)
        with col3:
            designated_far = st.number_input(
                "指定容積率", min_value=0.0, max_value=20.0, step=0.1,
                help="例: 4.0 = 400%",
            )
            designated_bcr = st.number_input(
                "指定建蔽率", min_value=0.0, max_value=1.0, step=0.05,
                help="例: 0.8 = 80%",
            )
        with col4:
            is_corner_lot = st.checkbox("角地")
            is_fireproof = st.checkbox("耐火建築物")
            fetch_articles = st.checkbox("e-Gov APIから条文を取得", value=True)

        submitted = st.form_submit_button(
            "🔍 法規チェック実行", use_container_width=True, type="primary"
        )

    if submitted:
        project = ProjectInfo(
            project_name=project_name,
            use_type=use_type,
            zone_type=zone_type,
            fire_zone=fire_zone,
            site_area=site_area,
            building_area=building_area,
            total_floor_area=total_floor_area,
            road_width=road_width,
            floors_above=floors_above,
            floors_below=floors_below,
            height=height,
            eave_height=eave_height,
            designated_far=designated_far,
            designated_bcr=designated_bcr,
            structure=structure,
            is_corner_lot=is_corner_lot,
            is_fireproof=is_fireproof,
        )

        checker = RegulationChecker(fetch_articles=fetch_articles)

        with st.spinner("法規チェックを実行中..."):
            report = checker.check(project)

        # サマリーメトリクス
        st.markdown("---")
        st.markdown("### 📊 チェック結果サマリー")

        counts = report.count_by_status()
        cols = st.columns(4)
        with cols[0]:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-value">{counts.get("適合", 0)}</div>
                <div class="metric-label">✅ 適合</div>
            </div>""", unsafe_allow_html=True)
        with cols[1]:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-value">{counts.get("不適合", 0)}</div>
                <div class="metric-label">❌ 不適合</div>
            </div>""", unsafe_allow_html=True)
        with cols[2]:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-value">{counts.get("要確認", 0)}</div>
                <div class="metric-label">⚠️ 要確認</div>
            </div>""", unsafe_allow_html=True)
        with cols[3]:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-value">{counts.get("該当なし", 0)}</div>
                <div class="metric-label">➖ 該当なし</div>
            </div>""", unsafe_allow_html=True)

        # 詳細結果
        st.markdown("---")
        st.markdown("### 📋 詳細チェック結果")

        # 不適合を先頭に表示
        priority_order = {"不適合": 0, "要確認": 1, "適合": 2, "該当なし": 3}
        sorted_results = sorted(
            report.results,
            key=lambda r: priority_order.get(r.status, 9),
        )

        for result in sorted_results:
            status_class = {
                "適合": "status-pass",
                "不適合": "status-fail",
                "要確認": "status-warn",
                "該当なし": "status-na",
            }.get(result.status, "status-na")

            risk_class = {
                "不適合": "risk-high",
                "要確認": "risk-medium",
            }.get(result.status, "risk-low")

            with st.container():
                st.markdown(f"""
                <div class="result-card {risk_class}">
                    <span class="{status_class}">{result.status}</span>
                    &nbsp; <strong>{result.category}</strong> — {result.subcategory}
                    <br><small style="color:#94a3b8">{result.law_reference}</small>
                    <p style="margin:0.5rem 0 0 0; color:#cbd5e1">{result.detail}</p>
                    {"<p style='color:#64748b; font-size:0.8rem; margin:0.3rem 0 0 0'>💡 " + result.note + "</p>" if result.note else ""}
                </div>
                """, unsafe_allow_html=True)

                if result.article_text:
                    with st.expander(f"📜 条文テキスト: {result.law_reference}"):
                        st.markdown(f'<div class="article-text">{result.article_text}</div>',
                                    unsafe_allow_html=True)

        # Markdownエクスポート
        st.markdown("---")
        md_report = _generate_regulation_markdown(report)
        st.download_button(
            "📥 レポートをMarkdownでダウンロード",
            data=md_report,
            file_name=f"法規チェック_{project_name or 'report'}_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
        )


# ===========================================================================
# Tab 2: 契約書レビュー
# ===========================================================================
with tab2:
    st.markdown("### 📝 契約書リーガルチェック")
    st.caption("契約書をアップロードすると、リスク条項を自動検出しチェックバックします。")

    col_up, col_type = st.columns([2, 1])
    with col_up:
        uploaded_file = st.file_uploader(
            "契約書ファイル",
            type=["pdf", "docx", "txt"],
            help="PDF / Word / テキストファイルに対応",
        )
    with col_type:
        contract_type = st.selectbox(
            "契約タイプ",
            ["設計業務委託", "工事請負", "設計監理", "業務委託（その他）"],
        )

    # テキスト直接入力も可能
    with st.expander("📋 テキストを直接入力する場合"):
        direct_text = st.text_area(
            "契約書テキスト",
            height=200,
            placeholder="ここに契約書のテキストを貼り付けてください...",
        )

    if st.button("🔍 契約書レビュー実行", use_container_width=True, type="primary"):
        text = ""

        if uploaded_file:
            # ファイルから読み込み
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=os.path.splitext(uploaded_file.name)[1],
            ) as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name

            from contract_analyzer import extract_text_from_file
            text = extract_text_from_file(tmp_path)
            os.unlink(tmp_path)
        elif direct_text:
            text = direct_text

        if not text:
            st.warning("契約書ファイルをアップロードするか、テキストを入力してください。")
        else:
            analyzer = ContractAnalyzer()
            with st.spinner("契約書を分析中..."):
                report = analyzer.analyze(
                    text,
                    contract_type=contract_type,
                    file_name=uploaded_file.name if uploaded_file else "直接入力",
                )

            # サマリー
            st.markdown("---")
            st.markdown("### 📊 レビュー結果サマリー")

            status_counts = report.count_by_risk()
            cols = st.columns(4)
            with cols[0]:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-value">{status_counts.get("問題あり", 0)}</div>
                    <div class="metric-label">🔴 問題あり</div>
                </div>""", unsafe_allow_html=True)
            with cols[1]:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-value">{status_counts.get("記載なし", 0)}</div>
                    <div class="metric-label">⚠️ 記載なし</div>
                </div>""", unsafe_allow_html=True)
            with cols[2]:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-value">{status_counts.get("確認推奨", 0)}</div>
                    <div class="metric-label">🟡 確認推奨</div>
                </div>""", unsafe_allow_html=True)
            with cols[3]:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-value">{status_counts.get("OK", 0)}</div>
                    <div class="metric-label">✅ OK</div>
                </div>""", unsafe_allow_html=True)

            # 建設業法必須項目
            if report.missing_items:
                st.markdown("---")
                st.error(f"⚠️ 建設業法19条 必須記載事項の欠落: {len(report.missing_items)} 項目")
                for item in report.missing_items:
                    st.markdown(f"- ❌ **{item}**")

            # 詳細結果
            st.markdown("---")
            st.markdown("### 📋 項目別チェック結果")

            priority = {"問題あり": 0, "記載なし": 1, "確認推奨": 2, "OK": 3}
            sorted_risks = sorted(
                report.risks,
                key=lambda r: priority.get(r.status, 9),
            )

            for risk in sorted_risks:
                risk_class = {
                    "問題あり": "risk-high",
                    "記載なし": "risk-medium",
                    "確認推奨": "risk-medium",
                    "OK": "risk-low",
                }.get(risk.status, "")

                status_class = {
                    "問題あり": "status-fail",
                    "記載なし": "status-warn",
                    "確認推奨": "status-warn",
                    "OK": "status-pass",
                }.get(risk.status, "status-na")

                st.markdown(f"""
                <div class="result-card {risk_class}">
                    <span class="{status_class}">{risk.status}</span>
                    &nbsp; <strong>[{risk.category}]</strong> {risk.item}
                    <span style="color:#64748b; font-size:0.75rem"> リスク:{risk.risk_level}</span>
                    <p style="margin:0.5rem 0 0 0; color:#cbd5e1">{risk.description}</p>
                    {"<p style='color:#fbbf24; font-size:0.85rem; margin:0.3rem 0 0 0'>💡 " + risk.advice + "</p>" if risk.advice else ""}
                    {"<p style='color:#94a3b8; font-size:0.8rem; margin:0.3rem 0 0 0'>📌 該当箇所: " + risk.matched_text[:100] + "...</p>" if risk.matched_text else ""}
                </div>
                """, unsafe_allow_html=True)

            # 条項一覧
            if report.clauses:
                st.markdown("---")
                with st.expander(f"📑 抽出された条項一覧（{report.total_clauses} 条）"):
                    for clause in report.clauses:
                        title_str = f"（{clause.title}）" if clause.title else ""
                        st.markdown(f"**{clause.number}** {title_str}")
                        st.text(clause.text[:200] + ("..." if len(clause.text) > 200 else ""))
                        st.markdown("---")

            # エクスポート
            md_contract = _generate_contract_markdown(report)
            st.download_button(
                "📥 レポートをMarkdownでダウンロード",
                data=md_contract,
                file_name=f"契約書レビュー_{datetime.now().strftime('%Y%m%d')}.md",
                mime="text/markdown",
            )


# ===========================================================================
# Tab 3: 判例リサーチ
# ===========================================================================
with tab3:
    st.markdown("### ⚖️ 判例リサーチ")
    st.caption("建築関連の判例をキーワードで検索します。")

    # 判例DB管理
    col_search, col_admin = st.columns([3, 1])

    with col_admin:
        st.markdown("#### 🗄️ 判例DB管理")

        stats = case_db.get_stats()
        st.metric("登録判例数", f"{stats['total']} 件")

        if stats["categories"]:
            st.markdown("**カテゴリ別:**")
            for cat, cnt in stats["categories"].items():
                st.markdown(f"- {cat}: {cnt} 件")

        if st.button("📥 判例データを収集", help="裁判所サイトから建築関連判例を収集します"):
            scraper = CaseLawScraper()
            with st.spinner("判例データを収集中...（数分かかります）"):
                try:
                    cases = scraper.search_all(max_per_keyword=5)
                    if cases:
                        scraper.save_cases(cases)
                        st.success(f"✅ {len(cases)} 件の判例を収集・保存しました")
                        st.rerun()
                    else:
                        st.warning("判例データを取得できませんでした")
                except Exception as e:
                    st.error(f"収集中にエラーが発生: {e}")

    with col_search:
        st.markdown("#### 🔍 判例検索")

        search_query = st.text_input(
            "検索キーワード",
            placeholder="例: 設計瑕疵 損害賠償、建築確認取消、日照権侵害...",
        )

        category_filter = st.selectbox(
            "カテゴリフィルタ",
            ["全て"] + list(CASE_LAW_CATEGORIES.keys()),
        )

        top_k = st.slider("表示件数", min_value=1, max_value=30, value=10)

        if search_query and st.button("🔍 検索実行", use_container_width=True, type="primary"):
            cat_filter = None if category_filter == "全て" else category_filter

            # 判例DBで検索
            results = case_db.search(search_query, top_k=top_k, category=cat_filter)

            if results:
                st.markdown(f"---\n### 📋 検索結果: {len(results)} 件")

                for i, (case, score) in enumerate(results, 1):
                    cat_badge = f'<span style="background:#312e81; color:#a5b4fc; padding:2px 8px; border-radius:10px; font-size:0.75rem">{case.category}</span>' if case.category else ""

                    st.markdown(f"""
                    <div class="result-card">
                        <strong>[{i}] {case.case_name or "（事件名未取得）"}</strong>
                        {cat_badge}
                        <span style="color:#64748b; float:right; font-size:0.75rem">関連度: {score:.3f}</span>
                        <br>
                        <small style="color:#94a3b8">
                            {case.court or ""} | {case.date or ""} | {case.case_number or ""}
                        </small>
                        {"<p style='color:#cbd5e1; margin:0.5rem 0 0 0; font-size:0.85rem'>" + case.summary[:300] + "...</p>" if case.summary else ""}
                    </div>
                    """, unsafe_allow_html=True)

                    if case.full_text:
                        with st.expander(f"📜 判例全文（抜粋）"):
                            st.text(case.full_text[:2000])
            else:
                st.info("🔍 該当する判例が見つかりませんでした。判例データを収集してください。")


# ===========================================================================
# Tab 4: 条文検索
# ===========================================================================
with tab4:
    st.markdown("### 📖 法令条文検索")
    st.caption("e-Gov APIで法令の条文を直接検索します。")

    col_law, col_art = st.columns([2, 1])
    with col_law:
        law_name_input = st.text_input(
            "法令名",
            placeholder="例: 建築基準法、建基法、民法、消防法施行令...",
        )
    with col_art:
        article_input = st.text_input(
            "条番号",
            placeholder="例: 20、第52条、第56条の2...",
        )

    if st.button("📖 条文を検索", use_container_width=True, type="primary"):
        if not law_name_input or not article_input:
            st.warning("法令名と条番号を入力してください。")
        else:
            egov = EgovClient()
            with st.spinner(f"条文を取得中: {law_name_input} 第{article_input}条..."):
                result = egov.get_article(law_name_input, article_input)

            if result.success:
                st.markdown(f"### {result.law_name} 第{result.article_num}条")
                st.markdown(f'<div class="article-text">{result.text}</div>',
                            unsafe_allow_html=True)
            else:
                st.error(f"❌ {result.error}")

    # 登録法令一覧
    with st.expander("📚 登録済み法令一覧"):
        laws = egov_client.get_registered_laws()
        for name, lid in laws.items():
            st.markdown(f"- **{name}** (ID: `{lid}`)")
