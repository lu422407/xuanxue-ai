"""铁板神数引擎（考刻定分版）。

整合开源项目：ziwei-doushu（紫微样本库，考刻辅助）。

核心方法 verify_kefen：
1. 先排紫微命盘（借 ZiWeiEngine.calculate）
2. 遍历 8 刻 × 10 分，按命宫位推算六亲属相/兄弟姐妹
3. 与用户已知事实比对，选出置信度最高的刻分
4. 查条文（knowledge/tieban/tiaowen/*.json，可扩展）
5. 降级：直接条文检索

接口遵循 BaseEngine（calculate 为无考刻的简化排盘入口）。
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from engines.base import BaseEngine, EngineError
from engines import calendar_utils as cu

logger = logging.getLogger(__name__)

# 与蓝图中 ZiWeiEngine 输出兼容的抽取（现有 ZiWeiEngine 也输出 palaces.position）
_ZHI_ORDER = list(cu.ZHI)

_KE_NAMES = ["初", "一", "二", "三", "四", "五", "六", "七"]


@dataclass
class KeFenCandidate:
    ke: int
    fen: int
    score: float
    matched_facts: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)


class TieBanEngine(BaseEngine):
    name = "tieban"
    version = "0.2.0"
    system = "tieban"

    def __init__(self) -> None:
        self._ziwei = None
        self.tiaowen_path = (
            Path(__file__).resolve().parent.parent / "knowledge" / "tieban" / "tiaowen"
        )
        self.tiaowen_db = self._load_tiaowen()
        self.kefen_traits = self._load_kefen_traits()
        self.has_fallback = len(self.tiaowen_db) > 0
        logger.info(
            "铁板引擎: 条文%d条, 刻分特征%d条", len(self.tiaowen_db), len(self.kefen_traits)
        )

    # ---- BaseEngine 接口 ----

    def validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        return cu.validate_birth_input(input_data)

    def calculate(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """无考刻的简化排盘：返回紫微基础命盘 + 可用条文数。"""
        normalized = self.validate_input(input_data)
        chart = self._ziwei_calculate(normalized)
        return {
            "system": self.system,
            "engine_version": self.version,
            "input_echo": chart.get("input_echo"),
            "base_chart": chart,
            "tiaowen_count": len(self.tiaowen_db),
            "note": "如需考刻定分请调用 verify_kefen()",
        }

    # ---- 考刻核心 ----

    def verify_kefen(self, input_data: Dict[str, Any], known_facts: Dict[str, str]) -> Dict:
        """考刻验证：遍历刻分组合，匹配已知事实，确定刻分并查条文。"""
        normalized = self.validate_input(input_data)
        try:
            base_chart = self._ziwei_calculate(normalized)
        except Exception as exc:
            logger.error("紫微排盘失败，降级为直接条文检索: %s", exc)
            return self._fallback_direct_query(known_facts)

        candidates: List[KeFenCandidate] = []
        for ke in range(8):
            for fen in range(10):
                predicted = self._predict_by_kefen(ke, fen, base_chart)
                score, matched, contradictions = self._compare_facts(predicted, known_facts)
                candidates.append(KeFenCandidate(ke=ke, fen=fen, score=score,
                                                 matched_facts=matched,
                                                 contradictions=contradictions))

        candidates.sort(key=lambda x: x.score, reverse=True)
        best = candidates[0]
        tiaowen = self._query_tiaowen_by_kefen(best.ke, best.fen)

        return {
            "verified_ke": best.ke,
            "verified_fen": best.fen,
            "kefen_string": self._kefen_to_string(best.ke, best.fen),
            "confidence": best.score,
            "matched_facts": best.matched_facts,
            "contradictions": best.contradictions,
            "all_candidates": [{"ke": c.ke, "fen": c.fen, "score": round(c.score, 2)}
                               for c in candidates[:5]],
            "predicted_tiaowen": tiaowen,
            "base_chart": base_chart,
            "method": "考刻定分",
        }

    def interpret_life(self, verified_ke: int, verified_fen: int) -> Dict:
        """按确定的刻分，展开各分类条文。"""
        tiaowen_list = self._query_tiaowen_by_kefen(verified_ke, verified_fen)
        categories: Dict[str, List[Dict]] = {
            "父母": [], "兄弟": [], "夫妻": [], "子女": [], "自身": [], "流年": [], "其他": []
        }
        for tw in tiaowen_list:
            cat = tw.get("category", "其他")
            categories[cat if cat in categories else "其他"].append(tw)
        parts = [f"{cat}{len(items)}条" for cat, items in categories.items() if items]
        return {
            "kefen": self._kefen_to_string(verified_ke, verified_fen),
            "summary": "；".join(parts) if parts else "暂无条文",
            "details": categories,
            "total_tiaowen": len(tiaowen_list),
        }

    # ---- 内部实现 ----

    def _ziwei_calculate(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        if self._ziwei is None:
            from engines.ziwei_engine import ZiWeiEngine
            self._ziwei = ZiWeiEngine()
        return self._ziwei.calculate(input_data)

    def _load_tiaowen(self) -> List[Dict]:
        tiaowen: List[Dict] = []
        if self.tiaowen_path.exists():
            for f in self.tiaowen_path.glob("*.json"):
                try:
                    with open(f, "r", encoding="utf-8") as file:
                        data = json.load(file)
                        tiaowen.extend(data if isinstance(data, list) else [data])
                except Exception as exc:
                    logger.warning("条文解析失败 %s: %s", f, exc)
        return tiaowen

    def _load_kefen_traits(self) -> Dict:
        traits_file = self.tiaowen_path / "kefen_traits.json"
        if traits_file.exists():
            try:
                with open(traits_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as exc:
                logger.warning("刻分特征解析失败: %s", exc)
        return {}

    def _kefen_to_string(self, ke: int, fen: int) -> str:
        return f"{_KE_NAMES[ke]}刻{fen}分"

    def _predict_by_kefen(self, ke: int, fen: int, base_chart: Dict) -> Dict:
        key = f"{ke}_{fen}"
        if key in self.kefen_traits:
            return self.kefen_traits[key]

        ming_position = (
            base_chart.get("palaces", {}).get("命宫", {}).get("position", "子")
        )
        ming_idx = _ZHI_ORDER.index(ming_position) if ming_position in _ZHI_ORDER else 0

        father_offset = (ke + fen) % 12
        mother_offset = (ke * 2 + fen) % 12

        return {
            "father_zodiac": _ZHI_ORDER[(ming_idx + father_offset) % 12],
            "mother_zodiac": _ZHI_ORDER[(ming_idx + mother_offset) % 12],
            "siblings": str((ke % 5) + 1),
            "self_rank": str((fen % 3) + 1),
            "algorithm": "紫微命盘+刻分偏移推算",
        }

    def _compare_facts(self, predicted: Dict, known: Dict) -> Tuple[float, List[str], List[str]]:
        matched: List[str] = []
        contradictions: List[str] = []
        total = len(known)
        if total == 0:
            return 0.0, [], []

        for key, actual_value in known.items():
            predicted_value = predicted.get(key)
            if predicted_value is None:
                continue
            if str(predicted_value).strip() == str(actual_value).strip():
                matched.append(f"{key}={actual_value}")
            else:
                contradictions.append(f"{key}: 预测{predicted_value}≠实际{actual_value}")

        return len(matched) / total, matched, contradictions

    def _query_tiaowen_by_kefen(self, ke: int, fen: int) -> List[Dict]:
        return [tw for tw in self.tiaowen_db
                if tw.get("ke") == ke and tw.get("fen") == fen]

    def _fallback_direct_query(self, known_facts: Dict) -> Dict:
        matched: List[Dict] = []
        for tw in self.tiaowen_db:
            score = 0
            for key, value in known_facts.items():
                if key in tw and str(tw[key]) == str(value):
                    score += 1
            if score > 0:
                matched.append({"tiaowen": tw, "score": score})
        matched.sort(key=lambda x: x["score"], reverse=True)
        return {
            "method": "直接条文检索（考刻降级）",
            "confidence": matched[0]["score"] / len(known_facts) if matched else 0,
            "matched_tiaowen": [m["tiaowen"] for m in matched[:3]],
            "note": "紫微排盘失败，使用直接条文匹配",
        }

    def add_tiaowen(self, tiaowen: Dict) -> None:
        self.tiaowen_db.append(tiaowen)
        output_path = self.tiaowen_path / "tiaowen_db.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.tiaowen_db, f, ensure_ascii=False, indent=2)