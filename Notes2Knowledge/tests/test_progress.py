import os
import subprocess
import sys
from pathlib import Path

import pytest

from progress import record_outcome, get_weakest_topic


def test_record_outcome_writes_a_row(tmp_path):
    db_path = tmp_path / "progress.sqlite"

    record_outcome(db_path, "Algorithms", "03 - Binary Search Trees", "rotation", "struggled")

    assert db_path.exists()


def test_record_outcome_rejects_invalid_outcome(tmp_path):
    db_path = tmp_path / "progress.sqlite"

    with pytest.raises(ValueError):
        record_outcome(db_path, "Algorithms", "03 - Binary Search Trees", "rotation", "unsure")


def test_get_weakest_topic_picks_most_struggled(tmp_path):
    db_path = tmp_path / "progress.sqlite"
    record_outcome(db_path, "Algorithms", "01 - Sorting", "quicksort", "solid")
    record_outcome(db_path, "Algorithms", "02 - Trees", "rotation", "struggled")
    record_outcome(db_path, "Algorithms", "02 - Trees", "balance factor", "struggled")

    assert get_weakest_topic(db_path, "Algorithms") == "02 - Trees"


def test_get_weakest_topic_no_rows_returns_none(tmp_path):
    db_path = tmp_path / "progress.sqlite"

    assert get_weakest_topic(db_path, "Algorithms") is None


def test_get_weakest_topic_ignores_other_courses(tmp_path):
    db_path = tmp_path / "progress.sqlite"
    record_outcome(db_path, "Statistics", "01 - Probability", "bayes", "struggled")

    assert get_weakest_topic(db_path, "Algorithms") is None


SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "progress.py"


def test_cli_record_then_weakest(tmp_path):
    db_path = tmp_path / "progress.sqlite"
    env = {**os.environ, "PROGRESS_DB_PATH": str(db_path)}

    record_result = subprocess.run(
        [sys.executable, str(SCRIPT), "record", "Algorithms", "02 - Trees", "rotation", "struggled"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert record_result.returncode == 0

    weakest_result = subprocess.run(
        [sys.executable, str(SCRIPT), "weakest", "Algorithms"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert weakest_result.returncode == 0
    assert weakest_result.stdout.strip() == "02 - Trees"


def test_cli_weakest_no_history_exits_nonzero(tmp_path):
    db_path = tmp_path / "progress.sqlite"
    env = {**os.environ, "PROGRESS_DB_PATH": str(db_path)}

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "weakest", "Algorithms"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 1
