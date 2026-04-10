# ⚖️ Legal AI Agent — 建築法務アシスタント

建築法規チェック・契約書レビュー・判例リサーチの統合Webアプリケーション。

LLM（大規模言語モデル）を一切使用せず、**ルールベース + パターンマッチング + e-Gov API** で動作します。

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.40+-red)
![License](https://img.shields.io/badge/License-MIT-green)

## 🎯 主な機能

### 1. 🏗️ 建築法規チェック
- プロジェクト情報（用途・面積・高さ等）を入力
- 容積率・建蔽率・高さ制限・防火規定等を自動判定
- 適合/不適合/要確認/該当なしの4段階で結果表示
- e-Gov API連携で条文テキストも取得可能
- Markdownレポートのダウンロード

### 2. 📝 契約書レビュー
- PDF/Word/テキストファイルに対応
- リスクキーワード自動検出（損害賠償上限なし、著作権放棄等）
- 建設業法第19条の必須記載事項チェック
- 条項単位のパース・分析

### 3. ⚖️ 判例リサーチ
- 裁判所ウェブサイト（courts.go.jp）から判例を自動収集
- TF-IDFベースの純Python検索エンジン（外部依存なし）
- カテゴリフィルタ・関連度スコア付き検索

### 4. 📖 条文検索
- e-Gov API経由で33法令を即時検索
- 建築基準法・建築基準法施行令・都市計画法・消防法 等

## 🚀 セットアップ

```bash
# クローン
git clone https://github.com/akihamada/legal-agent.git
cd legal-agent

# 仮想環境作成
python3 -m venv .venv
source .venv/bin/activate

# 依存関係インストール
pip install -r requirements.txt

# 起動
streamlit run app.py
```

## ☁️ Streamlit Cloud デプロイ

1. このリポジトリをForkまたはClone
2. [share.streamlit.io](https://share.streamlit.io) にアクセス
3. GitHubリポジトリを選択 → `app.py` を指定
4. デプロイ！

## 📁 プロジェクト構成

```
legal-agent/
├── app.py                  # Streamlit UI（メインアプリ）
├── regulation_checker.py   # 建築法規チェックエンジン
├── contract_analyzer.py    # 契約書レビューエンジン
├── case_law_scraper.py     # 判例スクレイパー
├── case_law_db.py          # 判例DB（TF-IDF検索）
├── law_tools.py            # e-Gov APIラッパー
├── checklists.py           # 法規・契約チェックルール定義
├── requirements.txt        # Python依存関係
├── knowledge/
│   └── case_law/
│       └── cases.json      # 収集済み判例データ
└── README.md
```

## ⚠️ 免責事項

本ツールは **法務事務の補助ツール** です。
- AIの出力は参考情報であり、最終判断は **専門家（弁護士・建築士等）** が行ってください
- 弁護士法第72条に基づき、法律上の判断・助言を行うものではありません
- 法令データはe-Gov APIからリアルタイム取得しますが、最新性を保証するものではありません

## 📜 ライセンス

MIT License
