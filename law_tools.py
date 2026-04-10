"""
法令検索ツール ラッパー (law_tools.py)

既存の tool_egov.py の機能をライブラリとして提供する。
CLI経由ではなく、Pythonオブジェクトとして直接呼び出し可能。
"""

import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional

import requests

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------
EGOV_API_BASE = "https://laws.e-gov.go.jp/api/2"
REQUEST_TIMEOUT = 60

# ---------------------------------------------------------------------------
# 法令レジストリ
# ---------------------------------------------------------------------------
LAW_REGISTRY: dict[str, str] = {
    "建築基準法": "325AC0000000201",
    "建築基準法施行令": "325CO0000000338",
    "建築基準法施行規則": "325M50004000040",
    "都市計画法": "343AC0000000100",
    "都市計画法施行令": "344CO0000000158",
    "都市計画法施行規則": "344M50004000049",
    "建築士法": "325AC1000000202",
    "消防法": "323AC1000000186",
    "消防法施行令": "336CO0000000037",
    "消防法施行規則": "336M50000008006",
    "建築物の耐震改修の促進に関する法律": "307AC0000000123",
    "浄化槽法": "358AC0000000043",
    "建築物のエネルギー消費性能の向上等に関する法律": "427AC0000000053",
    "高齢者、障害者等の移動等の円滑化の促進に関する法律": "418AC0000000091",
    "都市緑地法": "348AC0000000072",
    "景観法": "416AC0000000110",
    "住宅の品質確保の促進等に関する法律": "411AC0000000081",
    "駐車場法": "332AC0000000106",
    "宅地造成及び特定盛土等規制法": "336AC0000000191",
    "建物の区分所有等に関する法律": "337AC0000000069",
    "民法": "129AC0000000089",
    "文化財保護法": "325AC0000000214",
    "旅館業法": "323AC0000000138",
    "旅館業法施行令": "332CO0000000152",
    "旅館業法施行規則": "323M40000100028",
    "建設業法": "324AC0000000100",
    "食品衛生法": "322AC0000000233",
    "水道法": "332AC0000000177",
    "下水道法": "333AC0000000079",
    "騒音規制法": "343AC0000000098",
    "振動規制法": "351AC0000000064",
    "高齢者の居住の安定確保に関する法律": "413AC0000000026",
    "長期優良住宅の普及の促進に関する法律": "420AC0000000087",
}

ALIAS_MAP: dict[str, str] = {
    "建基法": "建築基準法",
    "基準法": "建築基準法",
    "施行令": "建築基準法施行令",
    "建基令": "建築基準法施行令",
    "都計法": "都市計画法",
    "士法": "建築士法",
    "消防令": "消防法施行令",
    "省エネ法": "建築物のエネルギー消費性能の向上等に関する法律",
    "バリアフリー法": "高齢者、障害者等の移動等の円滑化の促進に関する法律",
    "品確法": "住宅の品質確保の促進等に関する法律",
    "区分所有法": "建物の区分所有等に関する法律",
    "耐震改修促進法": "建築物の耐震改修の促進に関する法律",
}


# ---------------------------------------------------------------------------
# データクラス
# ---------------------------------------------------------------------------
@dataclass
class ArticleResult:
    """条文取得結果"""
    law_name: str
    article_num: str
    text: str
    success: bool = True
    error: str = ""


@dataclass
class LawSearchResult:
    """法令キーワード検索結果"""
    law_id: str
    law_name: str
    law_num: str
    category: str = ""


# ---------------------------------------------------------------------------
# EgovClient クラス
# ---------------------------------------------------------------------------
class EgovClient:
    """
    e-Gov 法令検索 API v2 のクライアントクラス。

    Usage:
        client = EgovClient()
        result = client.get_article("建築基準法", "20")
        print(result.text)
    """

    def __init__(self, timeout: int = REQUEST_TIMEOUT):
        """
        Args:
            timeout: API リクエストのタイムアウト秒数
        """
        self.timeout = timeout
        self._xml_cache: dict[str, ET.Element] = {}

    def resolve_law_name(self, name_or_alias: str) -> str:
        """
        略称・通称を正式名称に解決する。

        Args:
            name_or_alias: 法令名（略称可）

        Returns:
            正式名称

        Raises:
            ValueError: 法令が見つからない場合
        """
        if name_or_alias in ALIAS_MAP:
            return ALIAS_MAP[name_or_alias]
        if name_or_alias in LAW_REGISTRY:
            return name_or_alias
        candidates = [k for k in LAW_REGISTRY if name_or_alias in k]
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            raise ValueError(
                f"「{name_or_alias}」に複数の法令が該当: {candidates}"
            )
        raise ValueError(f"「{name_or_alias}」は登録済み法令辞書に見つかりません")

    def parse_article_num(self, article_input: str) -> str:
        """
        条番号をパースして Num 属性値形式に変換する。

        Args:
            article_input: ユーザー入力の条番号（例: "20", "第20条の2"）

        Returns:
            Num 属性値（例: "20", "20_2"）
        """
        m = re.search(r'(\d+)[条]?の(\d+)', article_input)
        if m:
            return f"{m.group(1)}_{m.group(2)}"
        m = re.search(r'(\d+)', article_input)
        if m:
            return m.group(1)
        raise ValueError(f"条番号を解析できません: {article_input}")

    def fetch_law_xml(self, law_id: str) -> ET.Element:
        """
        e-Gov API から法令 XML を取得する（キャッシュ付き）。

        Args:
            law_id: e-Gov 法令 ID

        Returns:
            XML ルート要素
        """
        if law_id in self._xml_cache:
            return self._xml_cache[law_id]

        url = f"{EGOV_API_BASE}/law_data/{law_id}"
        params = {"response_format": "xml"}

        try:
            resp = requests.get(url, params=params, timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"API リクエスト失敗: {e}")

        if resp.status_code != 200:
            raise ConnectionError(f"API エラー (HTTP {resp.status_code})")

        root = ET.fromstring(resp.content)
        self._xml_cache[law_id] = root
        return root

    def get_article(self, law_name: str, article: str) -> ArticleResult:
        """
        指定した法令の条文テキストを取得する。

        Args:
            law_name: 法令名（略称可）
            article: 条番号（例: "20", "第52条"）

        Returns:
            ArticleResult
        """
        try:
            formal_name = self.resolve_law_name(law_name)
            law_id = LAW_REGISTRY[formal_name]
            target_num = self.parse_article_num(article)
            root = self.fetch_law_xml(law_id)
            articles = self._find_articles(root, target_num)
            if not articles:
                return ArticleResult(
                    law_name=formal_name,
                    article_num=target_num,
                    text="",
                    success=False,
                    error=f"第{target_num}条は見つかりませんでした",
                )
            texts = [self._extract_article_text(a) for a in articles]
            return ArticleResult(
                law_name=formal_name,
                article_num=target_num,
                text="\n\n".join(texts),
            )
        except (ValueError, ConnectionError) as e:
            return ArticleResult(
                law_name=law_name,
                article_num=article,
                text="",
                success=False,
                error=str(e),
            )

    def search_laws(self, keyword: str) -> list[LawSearchResult]:
        """
        e-Gov API でキーワード検索する。

        Args:
            keyword: 検索キーワード

        Returns:
            検索結果リスト
        """
        url = f"{EGOV_API_BASE}/laws"
        params = {"law_title": keyword}
        try:
            resp = requests.get(url, params=params, timeout=self.timeout)
        except requests.exceptions.RequestException:
            return []

        if resp.status_code != 200:
            return []

        results = []
        try:
            data = resp.json()
            for law in data.get("laws", []):
                info = law.get("law_info", {})
                rev = law.get("revision_info", {})
                results.append(LawSearchResult(
                    law_id=info.get("law_id", ""),
                    law_name=rev.get("law_title", ""),
                    law_num=info.get("law_num", ""),
                    category=rev.get("category", ""),
                ))
        except (ValueError, KeyError):
            pass
        return results

    def get_registered_laws(self) -> dict[str, str]:
        """登録済み法令の一覧を返す。"""
        return dict(LAW_REGISTRY)

    # --- 内部メソッド ---

    def _find_articles(
        self, root: ET.Element, target_num: str
    ) -> list[ET.Element]:
        """XML から指定条番号の Article を検索する。"""
        return [
            a for a in root.iter("Article")
            if a.get("Num", "") == target_num
        ]

    def _extract_article_text(self, article: ET.Element) -> str:
        """Article 要素からテキストを抽出する。"""
        lines: list[str] = []

        title = article.find("ArticleTitle")
        if title is not None and title.text:
            lines.append(title.text.strip())

        caption = article.find("ArticleCaption")
        if caption is not None and caption.text:
            lines.append(caption.text.strip())

        for para in article.findall("Paragraph"):
            lines.extend(self._extract_paragraph(para, 0))

        return "\n".join(lines)

    def _extract_paragraph(
        self, para: ET.Element, depth: int
    ) -> list[str]:
        """Paragraph からテキスト抽出。"""
        lines: list[str] = []
        indent = "  " * depth

        pnum = para.find("ParagraphNum")
        pnum_text = ""
        if pnum is not None and pnum.text and pnum.text.strip():
            pnum_text = pnum.text.strip() + "\u3000"

        psent = para.find("ParagraphSentence")
        if psent is not None:
            s = self._collect_sentences(psent)
            if s:
                lines.append(f"{indent}{pnum_text}{s}")

        for item in para.findall("Item"):
            lines.extend(self._extract_item(item, depth + 1))

        return lines

    def _extract_item(self, item: ET.Element, depth: int) -> list[str]:
        """Item からテキスト抽出。"""
        lines: list[str] = []
        indent = "  " * depth

        ititle = item.find("ItemTitle")
        ititle_text = ""
        if ititle is not None and ititle.text:
            ititle_text = ititle.text.strip() + "\u3000"

        isent = item.find("ItemSentence")
        if isent is not None:
            s = self._collect_sentences(isent)
            if s:
                lines.append(f"{indent}{ititle_text}{s}")

        for level in range(1, 6):
            tag = f"Subitem{level}"
            for sub in item.findall(tag):
                lines.extend(self._extract_subitem(sub, tag, depth + 1))

        return lines

    def _extract_subitem(
        self, sub: ET.Element, tag: str, depth: int
    ) -> list[str]:
        """Subitem からテキスト抽出。"""
        lines: list[str] = []
        indent = "  " * depth

        stitle = sub.find(f"{tag}Title")
        stitle_text = ""
        if stitle is not None and stitle.text:
            stitle_text = stitle.text.strip() + "\u3000"

        ssent = sub.find(f"{tag}Sentence")
        if ssent is not None:
            s = self._collect_sentences(ssent)
            if s:
                lines.append(f"{indent}{stitle_text}{s}")

        m = re.search(r'(\d+)', tag)
        if m:
            next_tag = f"Subitem{int(m.group(1)) + 1}"
            for child in sub.findall(next_tag):
                lines.extend(self._extract_subitem(child, next_tag, depth + 1))

        return lines

    def _collect_sentences(self, parent: ET.Element) -> str:
        """全 Sentence テキストを結合する。"""
        return "".join(
            s.text.strip() for s in parent.iter("Sentence")
            if s.text
        )
