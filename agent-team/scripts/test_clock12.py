import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clock12 import clock12  # noqa: E402


@pytest.mark.parametrize(
    "hour, minute, want",
    [
        (0, 0, "12:00 am"),
        (0, 30, "12:30 am"),
        (9, 5, "9:05 am"),
        (12, 0, "12:00 pm"),
        (23, 59, "11:59 pm"),
    ],
)
def test_clock12(hour, minute, want):
    assert clock12(datetime(2026, 1, 2, hour, minute)) == want
