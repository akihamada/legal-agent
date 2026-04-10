"""
法規チェック・契約書レビュー用チェックリスト定義 (checklists.py)

建築法規のルール定義、契約書チェック項目、判例カテゴリなどの
構造化データを一元管理する。
"""

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# 用途地域定数
# ---------------------------------------------------------------------------
LOW_RISE_ZONES = [
    "第一種低層住居専用地域",
    "第二種低層住居専用地域",
]

MID_RISE_ZONES = [
    "第一種中高層住居専用地域",
    "第二種中高層住居専用地域",
]

RESIDENTIAL_ZONES = LOW_RISE_ZONES + MID_RISE_ZONES + [
    "第一種住居地域",
    "第二種住居地域",
    "準住居地域",
    "田園住居地域",
]

COMMERCIAL_ZONES = [
    "近隣商業地域",
    "商業地域",
]

INDUSTRIAL_ZONES = [
    "準工業地域",
    "工業地域",
    "工業専用地域",
]

ALL_ZONES = (
    LOW_RISE_ZONES
    + MID_RISE_ZONES
    + [
        "第一種住居地域",
        "第二種住居地域",
        "準住居地域",
        "田園住居地域",
    ]
    + COMMERCIAL_ZONES
    + INDUSTRIAL_ZONES
    + ["指定なし"]
)

ALL_USES = [
    "住宅",
    "共同住宅",
    "事務所",
    "店舗",
    "ホテル",
    "旅館",
    "病院",
    "診療所",
    "学校",
    "保育所",
    "老人ホーム",
    "倉庫",
    "工場",
    "危険物貯蔵施設",
    "集会場",
    "映画館",
    "飲食店",
    "その他",
]


# ---------------------------------------------------------------------------
# 法規チェックルール
# ---------------------------------------------------------------------------
@dataclass
class RegulationRule:
    """法規チェックの1ルール定義"""
    category: str
    subcategory: str
    description: str
    law_name: str
    article: str
    applicable_zones: list[str] = field(default_factory=list)
    applicable_uses: list[str] = field(default_factory=list)
    min_area: float = 0.0
    min_floors: int = 0
    min_height: float = 0.0
    note: str = ""


REGULATION_RULES: list[RegulationRule] = [
    # --- A. 集団規定 ---
    RegulationRule(
        category="A. 集団規定",
        subcategory="用途制限",
        description="用途地域における建築物の用途制限",
        law_name="建築基準法",
        article="48",
        note="別表第二に基づく用途制限の詳細確認が必要",
    ),
    RegulationRule(
        category="A. 集団規定",
        subcategory="容積率",
        description="容積率の制限",
        law_name="建築基準法",
        article="52",
        note="前面道路幅員による容積率制限を含む",
    ),
    RegulationRule(
        category="A. 集団規定",
        subcategory="建蔽率",
        description="建蔽率の制限",
        law_name="建築基準法",
        article="53",
        note="角地緩和・防火地域内耐火建築物の緩和あり",
    ),
    RegulationRule(
        category="A. 集団規定",
        subcategory="絶対高さ制限",
        description="低層住居専用地域における絶対高さ制限",
        law_name="建築基準法",
        article="55",
        applicable_zones=LOW_RISE_ZONES,
        note="10m（条例で12mの場合あり）",
    ),
    RegulationRule(
        category="A. 集団規定",
        subcategory="道路斜線制限",
        description="前面道路からの斜線制限",
        law_name="建築基準法",
        article="56",
        note="用途地域により適用距離・勾配が異なる",
    ),
    RegulationRule(
        category="A. 集団規定",
        subcategory="隣地斜線制限",
        description="隣地境界線からの斜線制限",
        law_name="建築基準法",
        article="56",
        note="20mまたは31mを超える部分に適用",
    ),
    RegulationRule(
        category="A. 集団規定",
        subcategory="北側斜線制限",
        description="北側隣地境界線からの斜線制限",
        law_name="建築基準法",
        article="56",
        applicable_zones=LOW_RISE_ZONES + MID_RISE_ZONES,
        note="低層住居：5m+1.25勾配 / 中高層住居：10m+1.25勾配",
    ),
    RegulationRule(
        category="A. 集団規定",
        subcategory="日影規制",
        description="日影による中高層建築物の高さ制限",
        law_name="建築基準法",
        article="56の2",
        applicable_zones=RESIDENTIAL_ZONES + ["近隣商業地域", "準工業地域"],
        note="対象区域・測定面・規制時間は自治体条例による",
    ),
    RegulationRule(
        category="A. 集団規定",
        subcategory="接道義務",
        description="建築物の敷地は道路に2m以上接しなければならない",
        law_name="建築基準法",
        article="43",
        note="特定行政庁の許可で例外あり",
    ),

    # --- B. 単体規定 ---
    RegulationRule(
        category="B. 単体規定",
        subcategory="構造耐力",
        description="構造耐力上主要な部分の安全性",
        law_name="建築基準法",
        article="20",
        note="高さ・規模に応じて構造計算のルートが異なる",
    ),
    RegulationRule(
        category="B. 単体規定",
        subcategory="防火・耐火",
        description="耐火建築物・準耐火建築物の要求",
        law_name="建築基準法",
        article="27",
        note="用途・規模・地域により耐火性能要求が異なる",
    ),
    RegulationRule(
        category="B. 単体規定",
        subcategory="採光",
        description="居室の採光に必要な開口部",
        law_name="建築基準法",
        article="28",
        note="居室の床面積の1/7以上（住宅）",
    ),
    RegulationRule(
        category="B. 単体規定",
        subcategory="換気",
        description="居室の換気に必要な開口部",
        law_name="建築基準法",
        article="28",
        note="床面積の1/20以上（機械換気の場合を除く）",
    ),
    RegulationRule(
        category="B. 単体規定",
        subcategory="天井高",
        description="居室の天井高さ",
        law_name="建築基準法施行令",
        article="21",
        note="2.1m以上（平均天井高さ）",
    ),
    RegulationRule(
        category="B. 単体規定",
        subcategory="階段寸法",
        description="階段の蹴上・踏面・幅の制限",
        law_name="建築基準法施行令",
        article="23",
        note="階段の種類（直通階段等）と用途により基準が異なる",
    ),
    RegulationRule(
        category="B. 単体規定",
        subcategory="避難階段",
        description="避難階段・特別避難階段の設置",
        law_name="建築基準法施行令",
        article="122",
        min_floors=3,
        note="5階以上の場合は特別避難階段が必要",
    ),
    RegulationRule(
        category="B. 単体規定",
        subcategory="排煙設備",
        description="排煙設備の設置",
        law_name="建築基準法施行令",
        article="126の2",
        min_area=500.0,
        note="延床面積500㎡超の特殊建築物等に必要",
    ),
    RegulationRule(
        category="B. 単体規定",
        subcategory="非常用照明",
        description="非常用照明装置の設置",
        law_name="建築基準法施行令",
        article="126の4",
        note="特殊建築物・3階以上の階等に必要",
    ),

    # --- C. 消防法 ---
    RegulationRule(
        category="C. 消防法",
        subcategory="消火器具",
        description="消火器具の設置義務",
        law_name="消防法施行令",
        article="10",
        note="延面積150㎡以上の特定防火対象物に設置",
    ),
    RegulationRule(
        category="C. 消防法",
        subcategory="自動火災報知設備",
        description="自動火災報知設備の設置義務",
        law_name="消防法施行令",
        article="21",
        note="用途・規模に応じて設置基準が異なる",
    ),
    RegulationRule(
        category="C. 消防法",
        subcategory="スプリンクラー",
        description="スプリンクラー設備の設置義務",
        law_name="消防法施行令",
        article="12",
        note="11階以上・規模一定以上の場合に設置",
    ),
    RegulationRule(
        category="C. 消防法",
        subcategory="非常用進入口",
        description="非常用進入口の設置",
        law_name="建築基準法施行令",
        article="126の6",
        min_floors=3,
        note="3階以上の階に設置（代替進入口で代替可）",
    ),

    # --- D. 省エネ・バリアフリー ---
    RegulationRule(
        category="D. 省エネ・環境",
        subcategory="省エネ適合義務",
        description="建築物省エネ法に基づく省エネ基準適合義務",
        law_name="建築物のエネルギー消費性能の向上等に関する法律",
        article="11",
        min_area=10.0,
        note="2025年以降は全ての新築に適合義務化",
    ),
    RegulationRule(
        category="D. 省エネ・環境",
        subcategory="バリアフリー義務",
        description="特別特定建築物のバリアフリー基準適合義務",
        law_name="高齢者、障害者等の移動等の円滑化の促進に関する法律",
        article="14",
        min_area=2000.0,
        note="特別特定建築物で2000㎡以上が義務対象",
    ),
]


# ---------------------------------------------------------------------------
# 契約書レビュー チェックリスト
# ---------------------------------------------------------------------------
@dataclass
class ContractCheckItem:
    """契約書チェック項目"""
    category: str
    item: str
    description: str
    risk_level: str  # "高" / "中" / "低"
    check_keywords: list[str] = field(default_factory=list)
    risk_keywords: list[str] = field(default_factory=list)
    advice: str = ""


# 建設業法19条 必須記載事項
CONSTRUCTION_LAW_REQUIRED_ITEMS = [
    "工事内容",
    "請負代金の額",
    "工事着手の時期及び工事完成の時期",
    "工事を施工しない日又は時間帯の定めをするときは、その内容",
    "請負代金の全部又は一部の前金払又は出来形部分に対する支払の定めをするときは、その支払の時期及び方法",
    "当事者の一方から設計変更又は工事着手の延期若しくは工事の全部若しくは一部の中止の申出があった場合における工期の変更、請負代金の額の変更又は損害の負担及びそれらの額の算定方法に関する定め",
    "天災その他不可抗力による工期の変更又は損害の負担及びその額の算定方法に関する定め",
    "価格等の変動若しくは変更に基づく請負代金の額又は工事内容の変更",
    "工事の施工により第三者が損害を受けた場合における賠償金の負担に関する定め",
    "注文者が工事の全部又は一部の完成を確認するための検査の時期及び方法並びに引渡しの時期",
    "工事完成後における請負代金の支払の時期及び方法",
    "工事の目的物の瑕疵を担保すべき責任又は当該責任の履行に関して講ずべき保証保険契約の締結その他の措置に関する定めをするときは、その内容",
    "各当事者の履行の遅滞その他債務の不履行の場合における遅延利息、違約金その他の損害金",
    "契約に関する紛争の解決方法",
]

# 後方互換エイリアス（contract_analyzer.py が使用）
CONSTRUCTION_LAW_REQUIRED = CONSTRUCTION_LAW_REQUIRED_ITEMS


CONTRACT_CHECK_ITEMS: list[ContractCheckItem] = [
    # --- 報酬・支払 ---
    ContractCheckItem(
        category="報酬・支払",
        item="報酬額の明記",
        description="報酬額が明確に記載されているか",
        risk_level="高",
        check_keywords=["報酬", "対価", "委託料", "設計料", "請負代金", "金額"],
        advice="報酬額は具体的な金額を明記し、消費税の取扱いも記載すること",
    ),
    ContractCheckItem(
        category="報酬・支払",
        item="支払条件",
        description="支払時期・方法が明確か",
        risk_level="高",
        check_keywords=["支払", "振込", "期日", "期限", "出来高", "前払"],
        advice="支払時期（着手時・中間・完了時）と方法を明確にすること",
    ),
    ContractCheckItem(
        category="報酬・支払",
        item="追加費用の取扱い",
        description="設計変更や追加業務の費用負担が明確か",
        risk_level="高",
        check_keywords=["追加", "変更", "増額", "精算", "実費"],
        risk_keywords=["追加費用は乙の負担", "追加報酬は生じない", "一切の追加費用"],
        advice="設計変更時の追加費用算定方法と承認プロセスを定めること",
    ),

    # --- 業務範囲 ---
    ContractCheckItem(
        category="業務範囲",
        item="業務内容の特定",
        description="業務範囲が具体的に定義されているか",
        risk_level="高",
        check_keywords=["業務内容", "業務範囲", "委託業務", "成果物", "別紙"],
        advice="業務内容は別紙で詳細に定義し、含まれるもの・含まれないものを明記",
    ),
    ContractCheckItem(
        category="業務範囲",
        item="工期・納期",
        description="工期・納期が明確に規定されているか",
        risk_level="高",
        check_keywords=["工期", "納期", "期間", "着手", "完了", "完成"],
        advice="工期延長の条件と手続きを明確にすること",
    ),

    # --- 責任・保証 ---
    ContractCheckItem(
        category="責任・保証",
        item="瑕疵担保責任",
        description="瑕疵担保期間と範囲が適切か",
        risk_level="高",
        check_keywords=["瑕疵", "担保", "契約不適合", "保証", "補修"],
        risk_keywords=["瑕疵担保期間を1年", "瑕疵担保責任を負わない", "一切の責任を負わない"],
        advice="民法の原則（知ってから1年・引渡しから10年）を下回る場合は要注意",
    ),
    ContractCheckItem(
        category="責任・保証",
        item="損害賠償",
        description="損害賠償の範囲と上限が適切か",
        risk_level="高",
        check_keywords=["損害賠償", "賠償", "損害", "免責", "上限"],
        risk_keywords=["損害賠償の上限を報酬額", "間接損害を除く", "一切の責任を負わない", "免責"],
        advice="損害賠償の上限は契約金額と同額以上が望ましい",
    ),
    ContractCheckItem(
        category="責任・保証",
        item="知的財産権",
        description="成果物の著作権・知的財産権の帰属が明確か",
        risk_level="中",
        check_keywords=["著作権", "知的財産", "権利", "帰属", "利用権"],
        risk_keywords=["著作権は甲に帰属", "一切の権利を譲渡"],
        advice="設計図書の著作権は設計者に帰属するのが原則（著作権法）",
    ),

    # --- 契約管理 ---
    ContractCheckItem(
        category="契約管理",
        item="解除条項",
        description="契約解除の条件と手続きが適切か",
        risk_level="高",
        check_keywords=["解除", "解約", "終了", "催告", "通知"],
        risk_keywords=["甲はいつでも解除できる", "催告なく解除", "即時解除"],
        advice="一方的な解除条項は避け、催告後一定期間での解除を定めること",
    ),
    ContractCheckItem(
        category="契約管理",
        item="不可抗力",
        description="不可抗力条項が適切に定められているか",
        risk_level="中",
        check_keywords=["不可抗力", "天災", "地震", "台風", "疫病", "パンデミック"],
        advice="不可抗力の定義と、発生時の費用負担・工期延長の取扱いを定めること",
    ),
    ContractCheckItem(
        category="契約管理",
        item="紛争解決",
        description="紛争解決方法が定められているか",
        risk_level="中",
        check_keywords=["紛争", "裁判", "仲裁", "調停", "管轄", "協議"],
        advice="建設工事紛争審査会の利用も検討すること",
    ),
    ContractCheckItem(
        category="契約管理",
        item="再委託・下請制限",
        description="再委託・下請けの条件が明確か",
        risk_level="中",
        check_keywords=["再委託", "下請", "外注", "第三者", "委託先"],
        risk_keywords=["再委託を禁ずる", "一切の再委託"],
        advice="再委託の可否、事前承認の要否、責任の所在を明確にすること",
    ),
    ContractCheckItem(
        category="契約管理",
        item="秘密保持",
        description="秘密保持義務が適切に定められているか",
        risk_level="中",
        check_keywords=["秘密", "機密", "守秘", "情報管理", "個人情報"],
        advice="秘密情報の定義と、契約終了後の義務存続期間を定めること",
    ),
    ContractCheckItem(
        category="契約管理",
        item="遅延損害金",
        description="遅延損害金の利率が適切か",
        risk_level="中",
        check_keywords=["遅延", "延滞", "利息", "年率", "日歩"],
        risk_keywords=["年率14.6%", "年率20%"],
        advice="遅延損害金は年率3〜6%程度が一般的（民法の法定利率は年3%）",
    ),
]


# ---------------------------------------------------------------------------
# 判例カテゴリ
# ---------------------------------------------------------------------------
CASE_LAW_CATEGORIES: dict[str, list[str]] = {
    "設計瑕疵": [
        "設計瑕疵", "設計ミス", "設計の誤り", "設計監理", "監理義務",
        "注意義務", "確認義務", "設計者の責任",
    ],
    "施工不良": [
        "施工不良", "手抜き工事", "施工瑕疵", "工事瑕疵",
        "施工者の責任", "下請関係", "品質管理",
    ],
    "契約紛争": [
        "請負代金", "追加工事", "設計変更", "工期遅延",
        "解除", "出来高", "損害賠償", "契約不適合",
    ],
    "近隣紛争": [
        "日照権", "日影", "眺望権", "プライバシー",
        "騒音", "振動", "境界", "越境",
    ],
    "建築確認": [
        "建築確認", "確認取消", "建築基準法違反",
        "用途地域", "容積率", "建蔽率", "高さ制限",
    ],
}

CASE_LAW_SEARCH_KEYWORDS = [
    "建築基準法", "設計瑕疵", "施工不良", "工事請負",
    "建築紛争", "請負代金", "瑕疵担保", "構造計算",
    "耐震", "日照権", "建築確認",
]
