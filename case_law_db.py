"""
判例検索データベース (case_law_db.py)

TF-IDF ベースの検索エンジンで、収集した判例データをキーワード検索する。
外部 LLM / ベクトルDB不使用。標準ライブラリのみで実装。
"""

import json
import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from typing import Optional

from case_law_scraper import CaseLaw, CaseLawScraper, DEFAULT_JSON_FILE
from checklists import CASE_LAW_CATEGORIES


# ---------------------------------------------------------------------------
# トークナイザー
# ---------------------------------------------------------------------------

def tokenize(text: str) -> list[str]:
    """
    簡易日本語トークナイザー。

    バイグラム（連続2文字）を基本単位とし、
    漢字・カタカナ・英字の連続もトークンとする。
    MeCab等の外部依存なしで動作する。

    Args:
        text: 入力テキスト

    Returns:
        トークンのリスト
    """
    if not text:
        return []

    tokens: list[str] = []

    # 1. 漢字の連続
    for m in re.finditer(r'[\u4e00-\u9fff\u3400-\u4dbf]+', text):
        word = m.group()
        if len(word) >= 2:
            tokens.append(word)
            # バイグラムも追加
            for i in range(len(word) - 1):
                tokens.append(word[i:i+2])

    # 2. カタカナの連続
    for m in re.finditer(r'[\u30a1-\u30f6\u30fc]+', text):
        word = m.group()
        if len(word) >= 2:
            tokens.append(word)

    # 3. 英字の連続
    for m in re.finditer(r'[a-zA-Z]+', text):
        word = m.group().lower()
        if len(word) >= 2:
            tokens.append(word)

    # 4. 数字+漢字の組み合わせ（「第52条」等）
    for m in re.finditer(r'[\u7b2c条項号][0-9一二三四五六七八九十百]+[\u6761項号]?', text):
        tokens.append(m.group())

    return tokens


# ---------------------------------------------------------------------------
# TF-IDF 検索エンジン
# ---------------------------------------------------------------------------

class TfIdfSearchEngine:
    """
    シンプルなTF-IDF検索エンジン。

    外部依存なしで動作する。インデックスの構築とコサイン類似度による検索を行う。
    """

    def __init__(self):
        """TF-IDFインデックスを初期化する。"""
        self.documents: list[dict] = []    # {"id": str, "tokens": list[str], "tf": dict}
        self.idf: dict[str, float] = {}
        self.doc_count = 0

    def build_index(self, docs: list[dict[str, str]]) -> None:
        """
        ドキュメント群からTF-IDFインデックスを構築する。

        Args:
            docs: [{"id": ..., "text": ...}] 形式のドキュメントリスト
        """
        self.documents = []
        self.doc_count = len(docs)

        df: dict[str, int] = Counter()  # Document Frequency

        for doc in docs:
            tokens = tokenize(doc["text"])
            tf = Counter(tokens)

            # 正規化 TF
            max_tf = max(tf.values()) if tf else 1
            norm_tf = {t: c / max_tf for t, c in tf.items()}

            self.documents.append({
                "id": doc["id"],
                "tokens": tokens,
                "tf": norm_tf,
            })

            for token in set(tokens):
                df[token] += 1

        # IDFの計算
        self.idf = {
            token: math.log((self.doc_count + 1) / (count + 1)) + 1
            for token, count in df.items()
        }

    def search(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        """
        クエリで検索して関連度の高いドキュメントを返す。

        Args:
            query: 検索クエリ
            top_k: 返す件数

        Returns:
            [(doc_id, score)] のリスト（スコア降順）
        """
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        query_tf = Counter(query_tokens)
        max_qtf = max(query_tf.values())
        query_vec = {
            t: (c / max_qtf) * self.idf.get(t, 1.0)
            for t, c in query_tf.items()
        }

        scores: list[tuple[str, float]] = []

        for doc in self.documents:
            score = self._cosine_similarity(query_vec, doc["tf"])
            if score > 0:
                scores.append((doc["id"], score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def _cosine_similarity(
        self, vec_a: dict[str, float], vec_b: dict[str, float]
    ) -> float:
        """コサイン類似度を計算する。"""
        common = set(vec_a.keys()) & set(vec_b.keys())
        if not common:
            return 0.0

        dot = sum(
            vec_a[t] * vec_b[t] * self.idf.get(t, 1.0) ** 2
            for t in common
        )
        norm_a = math.sqrt(sum(
            (vec_a[t] * self.idf.get(t, 1.0)) ** 2 for t in vec_a
        ))
        norm_b = math.sqrt(sum(
            (vec_b[t] * self.idf.get(t, 1.0)) ** 2 for t in vec_b
        ))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (norm_a * norm_b)


# ---------------------------------------------------------------------------
# CaseLawDB クラス
# ---------------------------------------------------------------------------

class CaseLawDB:
    """
    判例データベース。

    JSONファイルを読み込み、TF-IDFで検索可能にする。

    Usage:
        db = CaseLawDB()
        results = db.search("設計瑕疵 損害賠償", top_k=5)
    """

    def __init__(self, json_path: str = DEFAULT_JSON_FILE):
        """
        Args:
            json_path: 判例JSONファイルのパス
        """
        self.json_path = json_path
        self.cases: list[CaseLaw] = []
        self.case_map: dict[str, CaseLaw] = {}
        self.engine = TfIdfSearchEngine()
        self._load_and_index()

    def _load_and_index(self) -> None:
        """データを読み込みインデックスを構築する。"""
        scraper = CaseLawScraper()
        self.cases = scraper.load_cases(self.json_path)
        self.case_map = {c.case_id: c for c in self.cases}

        if self.cases:
            docs = [
                {
                    "id": c.case_id,
                    "text": f"{c.case_name} {c.court} {c.case_number} "
                            f"{c.summary} {c.full_text} {c.category}",
                }
                for c in self.cases
            ]
            self.engine.build_index(docs)

    def search(
        self,
        query: str,
        top_k: int = 10,
        category: Optional[str] = None,
    ) -> list[tuple[CaseLaw, float]]:
        """
        判例を検索する。

        Args:
            query: 検索クエリ
            top_k: 返す件数
            category: カテゴリフィルタ（Noneなら全カテゴリ）

        Returns:
            [(CaseLaw, score)] のリスト
        """
        results = self.engine.search(query, top_k=top_k * 3)  # フィルタがあるので多めに取得

        filtered: list[tuple[CaseLaw, float]] = []
        for case_id, score in results:
            case = self.case_map.get(case_id)
            if not case:
                continue
            if category and case.category != category:
                continue
            filtered.append((case, score))
            if len(filtered) >= top_k:
                break

        return filtered

    def get_stats(self) -> dict:
        """データベースの統計情報を返す。"""
        cats: dict[str, int] = {}
        for c in self.cases:
            cats[c.category] = cats.get(c.category, 0) + 1
        return {
            "total": len(self.cases),
            "categories": cats,
            "json_path": self.json_path,
        }

    def reload(self) -> None:
        """データを再読み込みする。"""
        self._load_and_index()
