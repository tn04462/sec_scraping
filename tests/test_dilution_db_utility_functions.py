import pytest
from boot import bootstrap_dilution_db
from datetime import timedelta, datetime
from pathlib import Path
from dilution_db import (
    get_folder_mtime,
    is_outdated
    )


def test_get_folder_mtime(tmp_path):
    root_path = tmp_path
    folder_time = get_folder_mtime(root_path)
    assert folder_time.date() == datetime.now().date() 

@pytest.mark.parametrize(
    ["comparison_time", "max_age", "now", "expected"],
    [
        (datetime(2000, 1, 1, 0, 0, 0), timedelta(hours=22), datetime(2000, 1, 1, 23, 0, 0), True),
        (datetime(2000, 1, 1, 0, 0, 0), timedelta(hours=22), datetime(2000, 1, 1, 21, 0, 0), False),
    ])
def test_is_outdated(comparison_time, max_age, now, expected):
    assert is_outdated(comparison_time, max_age, now) == expected
    
