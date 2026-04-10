"""
判例データスクレイピング (case_law_scraper.py)

裁判所ウェブサイト (courts.go.jp) から建築関連判例を収集する。
レートリミットとリトライ処理を実装。
"""

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

from checklists import CASE_LAW_SEARCH_KEYWORDS, CASE_LAW_CATEGORIES


# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------
COURTS_BASE_URL = "https://www.courts.go.jp"
SEARCH_URL = f"{COURTS_BASE_URL}/app/hanrei_jp/search"
DETAIL_URL = f"{COURTS_BASE_URL}/app/hanrei_jp/detail"
DEFAULT_DATA_DIR = os.path.join(os.path.dirname(__file__), "knowledge")
DEFAULT_JSON_FILE = os.path.join(DEFAULT_DATA_DIR, "cases.json")
REQUEST_TIMEOUT = 30
DEFAULT_DELAY = 2.0  # リクエスト間隔（秒）


# ---------------------------------------------------------------------------
# データクラス
# ---------------------------------------------------------------------------
@dataclass
class CaseLaw:
    """判例データ"""
    case_id: str = ""           # ハッシュベースのID
    case_name: str = ""         # 事件名
    case_number: str = ""       # 事件番号
    court: str = ""             # 裁判所
    date: str = ""              # 判決日
    summary: str = ""           # 要旨
    full_text: str = ""         # 全文（取得できた場合）
    url: str = ""               # 元URL
    category: str = ""          # カテゴリ
    search_keyword: str = ""    # 検索に使用したキーワード
    collected_at: str = ""      # 収集日時


# ---------------------------------------------------------------------------
# CaseLawScraper クラス
# ---------------------------------------------------------------------------
class CaseLawScraper:
    """
    裁判所サイトから建築関連判例を収集するスクレイパー。

    Usage:
        scraper = CaseLawScraper()
        cases = scraper.search_all(max_per_keyword=10)
        scraper.save_cases(cases)
    """

    def __init__(
        self,
        delay: float = DEFAULT_DELAY,
        data_dir: str = DEFAULT_DATA_DIR,
    ):
        """
        Args:
            delay: リクエスト間の待機秒数
            data_dir: データ保存ディレクトリ
        """
        self.delay = delay
        self.data_dir = data_dir
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (compatible; LegalAgentBot/1.0; "
                "+https://github.com/akihamada/legal-agent)"
            ),
        })
        os.makedirs(data_dir, exist_ok=True)

    def search_keyword(self, keyword: str, max_results: int = 10) -> list[CaseLaw]:
        """
        キーワードで判例を検索する。

        Args:
            keyword: 検索キーワード
            max_results: 最大取得件数

        Returns:
            判例リスト
        """
        cases: list[CaseLaw] = []

        try:
            params = {
                "action_id": "1",
                "hanreiSrchKbn": "02",
                "hanreiKanrenKw": keyword,
                "actionKbn": "01",
            }
            resp = self.session.get(
                SEARCH_URL, params=params, timeout=REQUEST_TIMEOUT
            )
            resp.encoding = "utf-8"

            if resp.status_code != 200:
                return cases

            soup = BeautifulSoup(resp.text, "html.parser")

            # 検索結果一覧から判例を抽出
            rows = soup.select("table.list tr")
            if not rows:
                rows = soup.select(".resultList tr, .result_list tr")

            for row in rows[:max_results]:
                case = self._parse_search_row(row, keyword)
                if case:
                    cases.append(case)
                    time.sleep(self.delay)

        except requests.exceptions.RequestException as e:
            print(f"[CaseLawScraper] 検索エラー ({keyword}): {e}")

        return cases

    def search_all(self, max_per_keyword: int = 5) -> list[CaseLaw]:
        """
        全キーワードで検索する。

        Args:
            max_per_keyword: キーワードあたりの最大取得件数

        Returns:
            重複除去済みの判例リスト
        """
        all_cases: list[CaseLaw] = []
        seen_ids: set[str] = set()

        for keyword in CASE_LAW_SEARCH_KEYWORDS:
            print(f"[CaseLawScraper] 検索中: {keyword}")
            cases = self.search_keyword(keyword, max_results=max_per_keyword)

            for case in cases:
                if case.case_id not in seen_ids:
                    seen_ids.add(case.case_id)
                    all_cases.append(case)

            time.sleep(self.delay * 2)  # キーワード間は長めに待機

        print(f"[CaseLawScraper] 合計 {len(all_cases)} 件収集")
        return all_cases

    def save_cases(self, cases: list[CaseLaw], file_path: str = "") -> str:
        """
        判例データをJSONファイルに保存する。

        Args:
            cases: 保存する判例リスト
            file_path: 保存先パス（空ならデフォルト）

        Returns:
            保存先のパス
        """
        path = file_path or DEFAULT_JSON_FILE

        # 既存データの読み込みとマージ
        existing = self.load_cases(path)
        existing_ids = {c.case_id for c in existing}

        new_cases = [c for c in cases if c.case_id not in existing_ids]
        merged = existing + new_cases

        # JSON保存
        data = [asdict(c) for c in merged]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[CaseLawScraper] {len(new_cases)} 件追加、合計 {len(merged)} 件保存 -> {path}")
        return path

    def load_cases(self, file_path: str = "") -> list[CaseLaw]:
        """
        保存済みの判例データを読み込む。

        Args:
            file_path: ファイルパス（空ならデフォルト）

        Returns:
            判例リスト
        """
        path = file_path or DEFAULT_JSON_FILE
        if not os.path.exists(path):
            return []

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [
                CaseLaw(**{k: v for k, v in item.items() if k in CaseLaw.__dataclass_fields__})
                for item in data
            ]
        except (json.JSONDecodeError, TypeError) as e:
            print(f"[CaseLawScraper] JSON読み込みエラー: {e}")
            return []

    # --- 内部メソッド ---

    def _parse_search_row(self, row, keyword: str) -> Optional[CaseLaw]:
        """検索結果の1行をパースする。"""
        try:
            cells = row.find_all("td")
            if len(cells) < 2:
                return None

            # リンクの取得
            link_tag = row.find("a")
            url = ""
            if link_tag and link_tag.get("href"):
                href = link_tag["href"]
                if not href.startswith("http"):
                    url = COURTS_BASE_URL + href
                else:
                    url = href

            # テキストの取得
            texts = [c.get_text(strip=True) for c in cells]

            case_name = texts[0] if texts else ""
            court = texts[1] if len(texts) > 1 else ""
            date = texts[2] if len(texts) > 2 else ""
            case_number = texts[3] if len(texts) > 3 else ""

            # ID = URLのハッシュ or テキストのハッシュ
            id_source = url or f"{case_name}_{case_number}"
            case_id = hashlib.md5(id_source.encode()).hexdigest()[:12]

            # カテゴリ分類
            category = self._classify_category(
                f"{case_name} {case_number}", keyword
            )

            # 詳細ページから要旨を取得
            summary = ""
            full_text = ""
            if url:
                summary, full_text = self._fetch_detail(url)

            return CaseLaw(
                case_id=case_id,
                case_name=case_name,
                case_number=case_number,
                court=court,
                date=date,
                summary=summary,
                full_text=full_text,
                url=url,
                category=category,
                search_keyword=keyword,
                collected_at=datetime.now().isoformat(),
            )

        except Exception as e:
            print(f"[CaseLawScraper] パースエラー: {e}")
            return None

    def _fetch_detail(self, url: str) -> tuple[str, str]:
        """判例詳細ページから要旨と全文を取得する。"""
        try:
            time.sleep(self.delay)
            resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
            resp.encoding = "utf-8"
            if resp.status_code != 200:
                return "", ""

            soup = BeautifulSoup(resp.text, "html.parser")

            # 要旨の取得
            summary = ""
            summary_el = soup.find("div", class_="dlist")
            if not summary_el:
                summary_el = soup.find(text=re.compile(r'裁判要旨|判示事項'))
                if summary_el:
                    summary_el = summary_el.find_parent("div") or summary_el.find_parent("td")

            if summary_el:
                summary = summary_el.get_text(strip=True)[:1000]

            # 全文PDFリンクの取得（テキストは取得しない）
            full_text = ""
            main_content = soup.find("div", class_="judgebox")
            if main_content:
                full_text = main_content.get_text(strip=True)[:5000]

            return summary, full_text

        except Exception as e:
            print(f"[CaseLawScraper] 詳細取得エラー: {e}")
            return "", ""

    def _classify_category(self, text: str, keyword: str) -> str:
        """テキストからカテゴリを判定する。"""
        for cat, keywords in CASE_LAW_CATEGORIES.items():
            for kw in keywords:
                if kw in text or kw in keyword:
                    return cat
        return "その他"
