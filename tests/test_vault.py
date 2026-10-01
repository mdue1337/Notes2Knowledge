import os
import subprocess
import sys
import pytest
from pathlib import Path

from vault import load_config, read_courseinfo, find_topic_note, read_notes, read_exercises

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "vault.py"


def test_load_config_parses_key_value_pairs(tmp_path):
    config_file = tmp_path / "config.env"
    config_file.write_text("VAULT_PATH=/tmp/note-vault\n")

    config = load_config(config_file)

    assert config == {"VAULT_PATH": "/tmp/note-vault"}


def test_load_config_missing_file_raises(tmp_path):
    missing_path = tmp_path / "does_not_exist.env"

    with pytest.raises(FileNotFoundError):
        load_config(missing_path)


def test_load_config_uses_config_path_env_var(tmp_path, monkeypatch):
    config_file = tmp_path / "env_config.env"
    config_file.write_text("VAULT_PATH=/env/note-vault\n")
    monkeypatch.setenv("CONFIG_PATH", str(config_file))

    config = load_config()

    assert config == {"VAULT_PATH": "/env/note-vault"}


def test_load_config_defaults_to_repo_root_config_env(monkeypatch):
    monkeypatch.delenv("CONFIG_PATH", raising=False)
    # Force the "not found" branch regardless of whether a real config.env
    # happens to exist in this checkout — we only care which path was computed.
    monkeypatch.setattr(Path, "exists", lambda self: False)
    expected_default = Path(__file__).resolve().parent.parent / "config.env"

    with pytest.raises(FileNotFoundError) as exc_info:
        load_config()

    assert str(expected_default) in str(exc_info.value)


def test_read_courseinfo_parses_exam_type():
    info = read_courseinfo(FIXTURES, "sample_course")

    assert info == {"exam_type": "written"}


def test_read_courseinfo_strips_inline_comment(tmp_path):
    course_dir = tmp_path / "commented_course"
    course_dir.mkdir()
    (course_dir / ".courseinfo.yaml").write_text("exam_type: written   # or: oral\n")

    info = read_courseinfo(tmp_path, "commented_course")

    assert info == {"exam_type": "written"}


def test_read_courseinfo_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        read_courseinfo(FIXTURES, "nonexistent_course")


def test_find_topic_note_locates_file():
    path = find_topic_note(FIXTURES, "sample_course", "03 - Binary Search Trees")

    assert path.name == "03 - Binary Search Trees.md"


def test_find_topic_note_missing_raises():
    with pytest.raises(FileNotFoundError):
        find_topic_note(FIXTURES, "sample_course", "99 - Does Not Exist")


def test_read_notes_returns_content():
    content = read_notes(FIXTURES, "sample_course", "03 - Binary Search Trees")

    assert "binary search tree" in content


def test_read_notes_empty_file_raises(tmp_path):
    course_dir = tmp_path / "empty_course" / "Week 1"
    course_dir.mkdir(parents=True)
    (course_dir / "01 - Empty Topic.md").write_text("")

    with pytest.raises(ValueError):
        read_notes(tmp_path, "empty_course", "01 - Empty Topic")


def test_read_exercises_returns_content():
    content = read_exercises(FIXTURES, "sample_course", "03 - Binary Search Trees")

    assert "Insert 5, 3, 8, 1" in content


def test_read_exercises_missing_raises(tmp_path):
    course_dir = tmp_path / "sample_course" / "Week 1"
    course_dir.mkdir(parents=True)
    (course_dir / "01 - No Exercises.md").write_text("# No Exercises\n")

    with pytest.raises(FileNotFoundError):
        read_exercises(tmp_path, "sample_course", "01 - No Exercises")


def test_cli_courseinfo_prints_value():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "courseinfo", "sample_course", "exam_type"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parent.parent),
        env={**os.environ, "VAULT_FIXTURE_PATH": str(FIXTURES)},
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "written"


def test_cli_courseinfo_missing_course_exits_nonzero():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "courseinfo", "nonexistent_course", "exam_type"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parent.parent),
        env={**os.environ, "VAULT_FIXTURE_PATH": str(FIXTURES)},
    )

    assert result.returncode == 1
    assert "Traceback" not in result.stderr
