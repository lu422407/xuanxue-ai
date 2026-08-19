"""历法与时间处理统一层单元测试。"""

from datetime import timedelta

import pytest

from engines import calendar_utils as cu
from engines.base import EngineError


def test_hour_index():
    assert cu.hour_index_from_datetime(cu._parse_datetime_string("2024-01-01 00:30:00")) == 0
    assert cu.hour_index_from_datetime(cu._parse_datetime_string("2024-01-01 23:30:00")) == 0
    assert cu.hour_index_from_datetime(cu._parse_datetime_string("2024-01-01 08:30:00")) == 4
    assert cu.hour_index_from_datetime(cu._parse_datetime_string("2024-01-01 12:00:00")) == 6


def test_true_solar_time_longitude():
    # 经度 91.5E vs 标准 120E：时差 = (91.5-120)*4 = -114 分钟
    dt = cu._parse_datetime_string("2024-06-01 12:00:00")
    corr = cu.true_solar_time_correction(dt, 91.5)
    # 均时差在 -15~+17 分钟内，因此总时差应在 [-129, -97] 分钟区间
    assert timedelta(minutes=-129) <= corr <= timedelta(minutes=-97)


def test_lunar_conversion():
    solar = cu.lunar_to_solar(1990, 4, 7)
    assert (solar.year, solar.month, solar.day) == (1990, 5, 1)


def test_lunar_info():
    info = cu.get_lunar_info(cu._parse_datetime_string("2024-02-10 00:00:00"))  # 2024 春节
    assert info["lunar_month"] == 1
    assert info["lunar_day"] == 1


@pytest.mark.parametrize(
    "bad",
    [
        {},
        {"birth_datetime": "1990-01-01 12:00:00"},
        {"birth_datetime": "1990-01-01 12:00:00", "timezone_offset": 8, "calendar": "solar",
         "true_solar_time": True},
    ],
)
def test_validation_errors(bad):
    with pytest.raises(EngineError):
        cu.validate_birth_input(bad)