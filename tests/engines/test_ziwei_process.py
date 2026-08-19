"""紫微进程代理引擎测试：结果与进程内引擎一致，且可在线程池调用。"""

import threading

from engines.ziwei_engine import ZiWeiEngine
from engines.ziwei_process import ZiWeiProcessEngine, calculate_ziwei

INPUT = {
    "birth_datetime": "1990-05-01 08:30:00",
    "timezone_offset": 8,
    "calendar": "solar",
    "gender": "男",
}


def test_process_engine_matches_inprocess():
    direct = ZiWeiEngine().calculate(dict(INPUT))
    via_process = calculate_ziwei(dict(INPUT))
    assert via_process == direct


def test_process_engine_interface():
    engine = ZiWeiProcessEngine()
    result = engine.calculate(dict(INPUT))
    assert result["system"] == "ziwei"
    assert len(result["palaces"]) == 12


def test_process_engine_from_worker_thread():
    holder = {}

    def worker():
        holder["result"] = calculate_ziwei(dict(INPUT))

    t = threading.Thread(target=worker)
    t.start()
    t.join(timeout=60)
    assert "result" in holder
    assert len(holder["result"]["palaces"]) == 12