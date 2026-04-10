"""
建築法規チェックエンジン (regulation_checker.py)

プロジェクト情報を入力として、建築法規の適合性をルールベースで網羅的にチェックする。
LLM不使用。e-Gov API で条文を引用し、構造化された判定結果を返す。
"""

from dataclasses import dataclass, field
from typing import Optional

from law_tools import EgovClient, ArticleResult
from checklists import (
    REGULATION_RULES,
    RegulationRule,
    RESIDENTIAL_ZONES,
    LOW_RISE_ZONES,
    COMMERCIAL_ZONES,
    INDUSTRIAL_ZONES,
)


# ---------------------------------------------------------------------------
# データ構造
# ---------------------------------------------------------------------------

@dataclass
class ProjectInfo:
    """チェック対象プロジェクト情報"""
    project_name: str = ""
    use_type: str = ""                  # 用途（ホテル、事務所等）
    zone_type: str = ""                 # 用途地域
    fire_zone: str = ""                 # 防火地域/準防火地域/指定なし
    site_area: float = 0.0             # 敷地面積 (㎡)
    building_area: float = 0.0         # 建築面積 (㎡)
    total_floor_area: float = 0.0      # 延床面積 (㎡)
    floors_above: int = 0              # 地上階数
    floors_below: int = 0              # 地下階数
    height: float = 0.0                # 建物高さ (m)
    eave_height: float = 0.0           # 軒高 (m)
    road_width: float = 0.0            # 前面道路幅員 (m)
    designated_far: float = 0.0        # 指定容積率
    designated_bcr: float = 0.0        # 指定建蔽率
    structure: str = ""                # 構造種別（RC, S, W 等）
    is_corner_lot: bool = False        # 角地かどうか
    is_fireproof: bool = False         # 耐火建築物かどうか
    notes: str = ""                    # 自由記述


@dataclass
class CheckResult:
    """1チェック項目の結果"""
    category: str
    subcategory: str
    description: str
    status: str             # "適合" / "不適合" / "要確認" / "該当なし"
    law_reference: str      # 法令参照（例: "建築基準法 第52条"）
    article_text: str = ""  # 条文テキスト（取得できた場合）
    detail: str = ""        # 判定の詳細説明
    note: str = ""          # 補足情報


@dataclass
class RegulationReport:
    """法規チェックレポート全体"""
    project: ProjectInfo
    results: list[CheckResult] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)

    def count_by_status(self) -> dict[str, int]:
        """ステータス別の集計"""
        counts: dict[str, int] = {}
        for r in self.results:
            counts[r.status] = counts.get(r.status, 0) + 1
        return counts


# ---------------------------------------------------------------------------
# 法規チェックエンジン
# ---------------------------------------------------------------------------

class RegulationChecker:
    """
    建築法規の適合性を網羅的にチェックするエンジン。

    Usage:
        checker = RegulationChecker()
        project = ProjectInfo(use_type="ホテル", zone_type="商業地域", ...)
        report = checker.check(project)
    """

    def __init__(self, fetch_articles: bool = True):
        """
        Args:
            fetch_articles: e-Gov APIから条文テキストを取得するかどうか
        """
        self.egov = EgovClient()
        self.fetch_articles = fetch_articles

    def check(self, project: ProjectInfo) -> RegulationReport:
        """
        プロジェクト情報に基づき法規チェックを実行する。

        Args:
            project: チェック対象プロジェクト情報

        Returns:
            法規チェックレポート
        """
        report = RegulationReport(project=project)

        for rule in REGULATION_RULES:
            result = self._check_single_rule(rule, project)
            report.results.append(result)

        # 追加チェック: 容積率・建蔽率の数値計算
        report.results.extend(self._check_numeric_limits(project))

        report.summary = report.count_by_status()
        return report

    def _check_single_rule(
        self, rule: RegulationRule, project: ProjectInfo
    ) -> CheckResult:
        """
        1件のルールに対するチェックを実行する。

        Args:
            rule: チェックルール
            project: プロジェクト情報

        Returns:
            チェック結果
        """
        law_ref = f"{rule.law_name} 第{rule.article}条"

        # 適用可否の判定
        if not self._is_applicable(rule, project):
            return CheckResult(
                category=rule.category,
                subcategory=rule.subcategory,
                description=rule.description,
                status="該当なし",
                law_reference=law_ref,
                detail="用途・地域・規模の条件に該当しないため適用外",
                note=rule.note,
            )

        # 条文の取得
        article_text = ""
        if self.fetch_articles:
            article_result = self.egov.get_article(
                rule.law_name, rule.article
            )
            if article_result.success:
                article_text = article_result.text

        # 具体的な判定
        status, detail = self._evaluate_rule(rule, project)

        return CheckResult(
            category=rule.category,
            subcategory=rule.subcategory,
            description=rule.description,
            status=status,
            law_reference=law_ref,
            article_text=article_text,
            detail=detail,
            note=rule.note,
        )

    def _is_applicable(
        self, rule: RegulationRule, project: ProjectInfo
    ) -> bool:
        """ルールがプロジェクトに適用されるかどうかを判定する。"""
        # 適用地域のチェック
        if rule.applicable_zones and project.zone_type:
            if project.zone_type not in rule.applicable_zones:
                return False

        # 適用用途のチェック
        if rule.applicable_uses and project.use_type:
            if project.use_type not in rule.applicable_uses:
                return False

        # 最小面積のチェック
        if rule.min_area > 0 and project.total_floor_area > 0:
            if project.total_floor_area < rule.min_area:
                return False

        # 最小階数のチェック
        if rule.min_floors > 0 and project.floors_above > 0:
            if project.floors_above < rule.min_floors:
                return False

        # 最小高さのチェック
        if rule.min_height > 0 and project.height > 0:
            if project.height < rule.min_height:
                return False

        return True

    def _evaluate_rule(
        self, rule: RegulationRule, project: ProjectInfo
    ) -> tuple[str, str]:
        """
        ルールに基づいた具体的な判定を行う。

        Returns:
            (ステータス, 詳細説明) のタプル
        """
        # 特定の条文に対する計算ベースの判定
        key = f"{rule.law_name}_{rule.article}"

        evaluators = {
            "建築基準法_52": self._eval_far,
            "建築基準法_53": self._eval_bcr,
            "建築基準法_55": self._eval_absolute_height,
            "建築基準法_43": self._eval_road_access,
            "建築基準法_20": self._eval_structural,
        }

        evaluator = evaluators.get(key)
        if evaluator:
            return evaluator(project)

        # 汎用判定（数値計算が不要なもの）
        return "要確認", f"適用対象です。{rule.description}の確認が必要です。"

    def _eval_far(self, p: ProjectInfo) -> tuple[str, str]:
        """容積率の判定"""
        if p.site_area <= 0 or p.total_floor_area <= 0:
            return "要確認", "敷地面積・延床面積を入力してください"

        actual_far = p.total_floor_area / p.site_area

        # 道路幅員制限
        road_far = float("inf")
        if p.road_width > 0 and p.road_width < 12.0:
            if p.zone_type in RESIDENTIAL_ZONES:
                road_far = p.road_width * 0.4
            else:
                road_far = p.road_width * 0.6

        effective_far = min(p.designated_far, road_far) if p.designated_far > 0 else road_far

        if effective_far == float("inf"):
            return "要確認", "指定容積率を入力してください"

        if actual_far <= effective_far:
            return (
                "適合",
                f"容積率 {actual_far*100:.1f}% ≤ 制限 {effective_far*100:.1f}%"
                + (f"（道路幅員{p.road_width}mによる制限）"
                   if road_far < p.designated_far else ""),
            )
        else:
            return (
                "不適合",
                f"⚠️ 容積率超過: {actual_far*100:.1f}% > 制限 {effective_far*100:.1f}%",
            )

    def _eval_bcr(self, p: ProjectInfo) -> tuple[str, str]:
        """建蔽率の判定"""
        if p.site_area <= 0 or p.building_area <= 0:
            return "要確認", "敷地面積・建築面積を入力してください"

        actual_bcr = p.building_area / p.site_area

        # 緩和措置の計算
        bcr_limit = p.designated_bcr
        relaxation = []

        if p.is_corner_lot and bcr_limit > 0:
            bcr_limit += 0.1
            relaxation.append("角地緩和+10%")

        if p.fire_zone == "防火地域" and p.is_fireproof and bcr_limit > 0:
            bcr_limit += 0.1
            relaxation.append("防火地域内耐火建築物+10%")

        if bcr_limit <= 0:
            return "要確認", "指定建蔽率を入力してください"

        relax_str = f"（{', '.join(relaxation)}適用）" if relaxation else ""

        if actual_bcr <= bcr_limit:
            return (
                "適合",
                f"建蔽率 {actual_bcr*100:.1f}% ≤ 制限 {bcr_limit*100:.1f}%{relax_str}",
            )
        else:
            return (
                "不適合",
                f"⚠️ 建蔽率超過: {actual_bcr*100:.1f}% > 制限 {bcr_limit*100:.1f}%{relax_str}",
            )

    def _eval_absolute_height(self, p: ProjectInfo) -> tuple[str, str]:
        """絶対高さ制限の判定"""
        if p.zone_type not in LOW_RISE_ZONES:
            return "該当なし", "低層住居専用地域ではないため適用外"

        if p.height <= 0:
            return "要確認", "建物高さを入力してください"

        # 一般的に10m（都市計画で12mの場合もある）
        limit = 10.0
        if p.height <= limit:
            return "適合", f"高さ {p.height}m ≤ 制限 {limit}m"
        elif p.height <= 12.0:
            return "要確認", f"高さ {p.height}m — 都市計画で12m指定か要確認"
        else:
            return "不適合", f"⚠️ 高さ超過: {p.height}m > 12m"

    def _eval_road_access(self, p: ProjectInfo) -> tuple[str, str]:
        """接道義務の判定"""
        if p.road_width <= 0:
            return "要確認", "前面道路幅員を入力してください"

        if p.road_width >= 4.0:
            return "適合", f"前面道路幅員 {p.road_width}m ≥ 4m"
        elif p.road_width >= 2.0:
            setback = (4.0 - p.road_width) / 2
            return (
                "要確認",
                f"道路幅員 {p.road_width}m < 4m → セットバック {setback}m が必要（建基法42条２項）",
            )
        else:
            return "不適合", f"⚠️ 道路幅員 {p.road_width}m < 2m — 建築不可の可能性"

    def _eval_structural(self, p: ProjectInfo) -> tuple[str, str]:
        """構造計算のルート判定"""
        if p.height <= 0:
            return "要確認", "建物高さを入力してください"

        if p.height > 60:
            return "要確認", "高さ60m超 → 時刻歴応答解析が必要（大臣認定ルート）"
        elif p.height > 31 or p.floors_above > 9:
            return "要確認", "ルート3（保有水平耐力計算）相当の構造計算が必要"
        elif p.height > 13 or p.eave_height > 9:
            return "要確認", "ルート2以上の構造計算が必要"
        else:
            return "要確認", "ルート1（壁量計算等）で対応可能な可能性あり"

    def _check_numeric_limits(
        self, project: ProjectInfo
    ) -> list[CheckResult]:
        """追加の数値比較チェック"""
        results: list[CheckResult] = []

        # 防火地域の確認
        if project.fire_zone and project.fire_zone != "指定なし":
            status = "要確認"
            detail = f"当該敷地は{project.fire_zone}に指定されています。"
            if project.fire_zone == "防火地域":
                if project.floors_above >= 3 or project.total_floor_area > 100:
                    detail += "耐火建築物としなければなりません（建基法61条）"
                else:
                    detail += "耐火建築物又は準耐火建築物としなければなりません"
            elif project.fire_zone == "準防火地域":
                if project.floors_above >= 4:
                    detail += "耐火建築物としなければなりません"
                elif project.total_floor_area > 1500:
                    detail += "耐火建築物又は準耐火建築物としなければなりません"

            results.append(CheckResult(
                category="B. 単体規定",
                subcategory="防火地域指定",
                description="防火地域・準防火地域の建築制限",
                status=status,
                law_reference="建築基準法 第61条",
                detail=detail,
            ))

        return results
