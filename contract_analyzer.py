"""
契約書レビューエンジン (contract_analyzer.py)

契約書テキストをパターンマッチング + チェックリストで分析する。
LLM不使用。建築設計業務委託・工事請負契約に特化。
"""

import os
import re
from dataclasses import dataclass, field
from typing import Optional

from checklists import CONTRACT_CHECK_ITEMS, ContractCheckItem, CONSTRUCTION_LAW_REQUIRED


# ---------------------------------------------------------------------------
# データ構造
# ---------------------------------------------------------------------------

@dataclass
class ClauseInfo:
    """抽出した条項"""
    number: str          # 条項番号（第1条 等）
    title: str           # 条項タイトル
    text: str            # 条項本文
    start_pos: int = 0   # テキスト中の開始位置


@dataclass
class RiskItem:
    """リスク検出結果"""
    category: str
    item: str
    risk_level: str      # 高/中/低
    status: str          # "問題あり" / "確認推奨" / "OK" / "記載なし"
    description: str
    matched_text: str = ""  # マッチした箇所
    advice: str = ""


@dataclass
class ContractReport:
    """契約書レビューレポート"""
    file_name: str = ""
    contract_type: str = ""
    total_clauses: int = 0
    clauses: list[ClauseInfo] = field(default_factory=list)
    risks: list[RiskItem] = field(default_factory=list)
    missing_items: list[str] = field(default_factory=list)  # 欠落している必須項目
    summary: dict[str, int] = field(default_factory=dict)

    def count_by_risk(self) -> dict[str, int]:
        """リスクレベル別集計"""
        counts: dict[str, int] = {}
        for r in self.risks:
            counts[r.status] = counts.get(r.status, 0) + 1
        return counts


# ---------------------------------------------------------------------------
# テキスト抽出
# ---------------------------------------------------------------------------

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    PDFファイルからテキストを抽出する。

    Args:
        pdf_path: PDFファイルパス

    Returns:
        抽出されたテキスト
    """
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        pages = [page.get_text() for page in doc]
        doc.close()
        return "\n".join(pages)
    except ImportError:
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                pages = [p.extract_text() or "" for p in pdf.pages]
            return "\n".join(pages)
        except Exception as e:
            return f"[PDF読み込みエラー] {e}"


def extract_text_from_docx(docx_path: str) -> str:
    """
    Wordファイルからテキストを抽出する。

    Args:
        docx_path: Wordファイルパス

    Returns:
        抽出されたテキスト
    """
    try:
        from docx import Document
        doc = Document(docx_path)
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        return f"[Word読み込みエラー] {e}"


def extract_text_from_file(file_path: str) -> str:
    """
    ファイルからテキストを抽出する（拡張子で自動判定）。

    Args:
        file_path: ファイルパス

    Returns:
        テキスト
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext in (".docx", ".doc"):
        return extract_text_from_docx(file_path)
    elif ext in (".txt", ".md"):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        raise ValueError(f"未対応のファイル形式: {ext}")


# ---------------------------------------------------------------------------
# 条項パーサー
# ---------------------------------------------------------------------------

def parse_clauses(text: str) -> list[ClauseInfo]:
    """
    契約書テキストを条項単位に分割する。

    「第X条」パターンで分割し、条項タイトルと本文を抽出する。

    Args:
        text: 契約書全文テキスト

    Returns:
        条項のリスト
    """
    # 「第1条」「第１条」パターンでの分割
    pattern = re.compile(
        r'(第[0-9０-９一二三四五六七八九十百]+条[の0-9０-９]*)'
        r'[\s　]*[（\(]?([^）\)\n]*?)[）\)]?\s*\n?',
    )

    matches = list(pattern.finditer(text))
    clauses: list[ClauseInfo] = []

    for i, m in enumerate(matches):
        number = m.group(1)
        title = m.group(2).strip() if m.group(2) else ""

        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()

        clauses.append(ClauseInfo(
            number=number,
            title=title,
            text=body,
            start_pos=m.start(),
        ))

    return clauses


# ---------------------------------------------------------------------------
# ContractAnalyzer クラス
# ---------------------------------------------------------------------------

class ContractAnalyzer:
    """
    契約書をルールベースで分析するエンジン。

    Usage:
        analyzer = ContractAnalyzer()
        report = analyzer.analyze(contract_text, "設計業務委託")
    """

    def __init__(self):
        """初期化"""
        self.check_items = CONTRACT_CHECK_ITEMS

    def analyze(
        self,
        text: str,
        contract_type: str = "設計業務委託",
        file_name: str = "",
    ) -> ContractReport:
        """
        契約書テキストを分析する。

        Args:
            text: 契約書テキスト
            contract_type: 契約タイプ
            file_name: ファイル名

        Returns:
            契約書レビューレポート
        """
        # 条項パース
        clauses = parse_clauses(text)
        full_text = text.lower()

        report = ContractReport(
            file_name=file_name,
            contract_type=contract_type,
            total_clauses=len(clauses),
            clauses=clauses,
        )

        # 各チェック項目の検査
        for check in self.check_items:
            risk = self._check_item(check, text, full_text, clauses)
            report.risks.append(risk)

        # 建設業法19条の必須項目チェック（工事請負契約の場合）
        if contract_type in ["工事請負", "建設工事請負"]:
            report.missing_items = self._check_construction_law(text)

        report.summary = report.count_by_risk()
        return report

    def analyze_file(
        self,
        file_path: str,
        contract_type: str = "設計業務委託",
    ) -> ContractReport:
        """
        ファイルから契約書を読み込んで分析する。

        Args:
            file_path: ファイルパス
            contract_type: 契約タイプ

        Returns:
            契約書レビューレポート
        """
        text = extract_text_from_file(file_path)
        return self.analyze(
            text,
            contract_type=contract_type,
            file_name=os.path.basename(file_path),
        )

    def _check_item(
        self,
        check: ContractCheckItem,
        original_text: str,
        lower_text: str,
        clauses: list[ClauseInfo],
    ) -> RiskItem:
        """
        1チェック項目の検査を行う。

        Args:
            check: チェック項目
            original_text: 元のテキスト
            lower_text: 小文字化テキスト
            clauses: パース済み条項

        Returns:
            リスク検出結果
        """
        # 1. 必須キーワードの存在チェック
        required_found = []
        required_missing = []
        for kw in check.required_keywords:
            if kw in original_text:
                required_found.append(kw)
            else:
                required_missing.append(kw)

        # 必須キーワードがすべて欠落 → 記載なし
        if check.required_keywords and not required_found:
            return RiskItem(
                category=check.category,
                item=check.item,
                risk_level=check.risk_level,
                status="記載なし",
                description=f"関連する記載が見つかりませんでした",
                advice=check.advice,
            )

        # 2. リスクキーワードの検出
        risk_matches = []
        context = ""
        for kw in check.risk_keywords:
            if kw in original_text:
                risk_matches.append(kw)
                # マッチ箇所の周辺テキストを取得
                idx = original_text.index(kw)
                start = max(0, idx - 30)
                end = min(len(original_text), idx + len(kw) + 30)
                context = original_text[start:end]

        if risk_matches:
            return RiskItem(
                category=check.category,
                item=check.item,
                risk_level=check.risk_level,
                status="問題あり",
                description=f"リスクキーワード検出: {', '.join(risk_matches)}",
                matched_text=context if risk_matches else "",
                advice=check.advice,
            )

        # 3. 記載あり＆リスクキーワードなし → OK
        if required_found:
            return RiskItem(
                category=check.category,
                item=check.item,
                risk_level=check.risk_level,
                status="OK",
                description=f"記載確認: {', '.join(required_found[:3])}",
                advice="",
            )

        # 4. 必須キーワード指定なしの場合
        return RiskItem(
            category=check.category,
            item=check.item,
            risk_level=check.risk_level,
            status="確認推奨",
            description=check.description,
            advice=check.advice,
        )

    def _check_construction_law(self, text: str) -> list[str]:
        """
        建設業法19条の必須記載事項をチェックする。

        Args:
            text: 契約書テキスト

        Returns:
            欠落している必須項目のリスト
        """
        missing = []
        for item in CONSTRUCTION_LAW_REQUIRED:
            # 類似表現も含めてチェック
            synonyms = {
                "瑕疵担保責任": ["瑕疵担保", "契約不適合", "不適合責任"],
                "請負代金の額": ["請負代金", "工事費", "報酬額", "契約金額"],
                "紛争の解決": ["紛争", "調停", "仲裁", "裁判管轄"],
                "天災その他不可抗力": ["天災", "不可抗力", "天変地異"],
            }
            keywords = synonyms.get(item, [item])
            found = any(kw in text for kw in keywords)
            if not found:
                missing.append(item)
        return missing
