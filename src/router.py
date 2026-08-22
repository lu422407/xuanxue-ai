"""术数统一路由。

整合 8 个 GitHub 开源项目（见 third_party/）的引擎入口：
- iztro / py-iztro（紫微）
- ziwei-doushu（紫微样本库，备用引擎）
- DeepSeek-Oracle（Prompt 参考）
- chinese-metaphysics-skills（六壬 SKILL.md 知识库）
- ZhouYiLab（C++ 多术数验证层）
- dalurenpython / daliuren-web-engine（六壬 Python/可视化）

路由器基于关键词打分识别术数类型，再交由对应引擎的
`calculate(input_data)` 执行（遵循 BaseEngine 接口）。
"""

import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# 术数 → (模块路径, 类名)
_ENGINE_LOCATIONS = {
    "紫微斗数": ("engines.ziwei_engine", "ZiWeiEngine"),
    "大六壬": ("engines.liuren_engine", "LiuRenEngine"),
    "八字": ("engines.bazi_engine", "BaziEngine"),
    "铁板神数": ("engines.tieban_engine", "TieBanEngine"),
    "奇门遁甲": ("engines.qimen_engine", "QiMenEngine"),
    "六爻": ("engines.liuyao_engine", "LiuYaoEngine"),
    "风水": (None, None),
    "太乙神数": (None, None),
}

# 术数 → 识别关键词（来自蓝图附录 B 选型 + 各术数术语）
_KEYWORDS = {
    "紫微斗数": ["紫微", "命盘", "命宫", "主星", "四化", "格局", "飞星", "身宫", "十二宫"],
    "大六壬": ["六壬", "四课", "三传", "天将", "月将", "贵人", "占课", "课体", "毕法赋"],
    "八字": ["八字", "四柱", "十神", "大运", "流年", "日主", "用神", "喜忌", "排八字"],
    "铁板神数": ["铁板", "条文", "考刻", "刻分", "六亲", "条文数", "太玄数"],
    "奇门遁甲": ["奇门", "遁甲", "八门", "九星", "九宫", "值符", "阴遁", "阳遁", "排盘"],
    "六爻": ["六爻", "纳甲", "装卦", "动爻", "世应", "六亲", "六神", "本卦", "变卦"],
    "风水": ["风水", "罗盘", "峦头", "理气", "八宅", "玄空", "三元", "九星"],
    "太乙神数": ["太乙", "神数", "太乙局", "计神", "客参", "主参"],
}

# 时辰名 → 起始小时
_HOUR_MAP = {
    "子时": 0, "丑时": 2, "寅时": 4, "卯时": 6, "辰时": 8, "巳时": 10,
    "午时": 12, "未时": 14, "申时": 16, "酉时": 18, "戌时": 20, "亥时": 22,
}


class XuanXueRouter:
    """术数统一路由器。"""

    def __init__(self) -> None:
        self.engines: Dict[str, Optional[Any]] = {}
        self.available_engines: Dict[str, bool] = {}
        for method in _KEYWORDS:
            self.available_engines[method] = False
            self.engines[method] = None

        for method, (module, class_name) in _ENGINE_LOCATIONS.items():
            self._load_engine(method, module, class_name)

        logger.info(
            "路由器: 已加载 %d/%d 种术数",
            sum(self.available_engines.values()), len(_KEYWORDS),
        )

    def _load_engine(self, name: str, module: Optional[str], class_name: Optional[str]) -> None:
        if not module or not class_name:
            return
        try:
            mod = __import__(module, fromlist=[class_name])
            cls = getattr(mod, class_name)
            self.engines[name] = cls()
            self.available_engines[name] = True
            logger.info("%s 引擎加载成功", name)
        except Exception as exc:
            logger.warning("%s 引擎加载失败: %s", name, exc)
            self.engines[name] = None
            self.available_engines[name] = False

    def route(self, user_input: str) -> Dict[str, Any]:
        """识别用户意图，返回 (术数, 置信度, 可用性, 参数, 引擎)。"""
        scores = {
            method: sum(1 for kw in kws if kw in user_input) / len(kws)
            for method, kws in _KEYWORDS.items()
        }
        params = self._extract_params(user_input)
        best_method = max(scores, key=scores.get)
        confidence = scores[best_method]

        if confidence < 0.1:
            return {
                "method": "unknown", "confidence": 0,
                "message": "无法确定术数类型，请说明：紫微斗数/大六壬/八字/铁板神数/奇门遁甲/六爻/风水/太乙",
                "parsed_params": params, "available": False,
            }

        engine = self.engines.get(best_method)
        is_available = self.available_engines.get(best_method, False)
        if not is_available:
            return {
                "method": best_method, "confidence": confidence,
                "message": f"{best_method}引擎未初始化",
                "parsed_params": params, "available": False,
                "setup_hint": self._get_setup_hint(best_method),
            }

        return {
            "method": best_method, "confidence": confidence,
            "engine": engine, "parsed_params": params, "available": True,
        }

    def _extract_params(self, text: str) -> Dict[str, Any]:
        """从自然语言中提取出生时间 / 性别 / 已知事实。"""
        params: Dict[str, Any] = {}

        for pattern, date_type in [
            (r"农历(\d{4})年(\d{1,2})月(\d{1,2})日", "lunar"),
            (r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", "solar"),
            (r"(\d{4})年(\d{1,2})月(\d{1,2})日", "solar"),
        ]:
            match = re.search(pattern, text)
            if match:
                params["year"] = int(match.group(1))
                params["month"] = int(match.group(2))
                params["day"] = int(match.group(3))
                params["date_type"] = date_type
                break

        for name, hour in _HOUR_MAP.items():
            if name in text:
                params["hour"] = hour
                break

        hour_match = re.search(r"(\d{1,2})[点时]", text)
        if hour_match and "hour" not in params:
            params["hour"] = int(hour_match.group(1))
        else:
            time_match = re.search(r"(\d{1,2}):(\d{2})", text)
            if time_match and "hour" not in params:
                params["hour"] = int(time_match.group(1))

        if "男" in text:
            params["gender"] = "男"
        elif "女" in text:
            params["gender"] = "女"

        if "父属" in text or "母属" in text:
            params["known_facts"] = self._extract_known_facts(text)

        return params

    def _extract_known_facts(self, text: str) -> Dict[str, str]:
        facts = {}
        for match in re.finditer(r"(父|母|妻|夫|兄|弟|姐|妹)属(\w)", text):
            key = {"父": "father_zodiac", "母": "mother_zodiac"}.get(
                match.group(1), match.group(1)
            )
            facts[key] = match.group(2)
        return facts

    def build_input(self, params: Dict[str, Any], timezone_offset: float = 8.0) -> Dict[str, Any]:
        """把路由解析出的参数转成 BaseEngine 兼容的 input_data。"""
        date_type = params.get("date_type", "solar")
        year = params.get("year")
        month = params.get("month")
        day = params.get("day")
        hour = params.get("hour", 12)
        if not (year and month and day):
            raise ValueError("缺少出生日期参数")

        birth_datetime = f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:00:00"
        return {
            "birth_datetime": birth_datetime,
            "timezone_offset": timezone_offset,
            "calendar": date_type,
            "gender": params.get("gender", "男"),
        }

    def _get_setup_hint(self, method: str) -> str:
        hints = {
            "紫微斗数": "pip install py-iztro pythonmonkey（见 requirements.txt）",
            "大六壬": "pip install -r requirements.txt（eacal/astropy 等）",
            "八字": "pip install -r requirements.txt（sxtwl/ganzhiwuxin，见 README）",
            "铁板神数": "准备条文库: knowledge/tieban/tiaowen/",
            "奇门遁甲": "编译 ZhouYiLab CLI（bash scripts/setup_submodules.sh 或 docs/ZHOUEYILAB_BUILD_GUIDE.md）",
            "六爻": "编译 ZhouYiLab CLI（bash scripts/setup_submodules.sh 或 docs/ZHOUEYILAB_BUILD_GUIDE.md）",
        }
        return hints.get(method, "请检查子模块")