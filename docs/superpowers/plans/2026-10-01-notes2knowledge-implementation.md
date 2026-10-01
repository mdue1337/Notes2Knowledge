# Notes2Knowledge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Notes2Knowledge, a read-only companion to Slides2Grades that quizzes you on your own vault notes (written-exam courses) or listens to you explain concepts back (oral-exam courses), tracking struggle/solid outcomes in its own local SQLite log instead of ever writing to the vault.

**Architecture:** Two Claude Code skills (`written-mode`, `oral-mode`) sit on top of two shared scripts — `vault.py` (read-only vault access, same `VAULT_PATH`/`config.env` resolution contract as Slides2Grades's `scripts/config.py`) and `progress.py` (narrow SQLite queries/writes against `data/progress.sqlite`, never a full-table dump). A one-line prerequisite documents the shared `.courseinfo.yaml` schema in the Slides2Grades repo, since both repos read that file but neither owns the other's code.

**Tech Stack:** Python 3.12+, stdlib only (`sqlite3`, `pathlib`, `datetime`) — no PyYAML, `.courseinfo.yaml` is parsed with the same simple `key: value` line parser style Slides2Grades's `config.py` already uses for `config.env`. pytest for tests.

**Spec:** `Notes2Knowledge/docs/superpowers/specs/2026-10-01-notes2knowledge-design.md`

## Global Constraints

- Read-only vault access: no script in this repo ever writes into `note-vault`. (spec: "Relationship to Slides2Grades")
- Narrow queries only: `get_weakest_topic` returns a single topic, never a full history dump — token cost must stay flat regardless of database size. (spec: "Data Flow")
- Hard errors, never silent fallback: missing `.courseinfo.yaml`, an exam-type mismatch, or a missing/empty topic note must raise/exit loudly, never guess or proceed quietly. (spec: "Error Handling")
- `VAULT_PATH` resolution order mirrors Slides2Grades's `scripts/config.py` exactly: explicit path arg → `CONFIG_PATH` env var → `<repo root>/config.env`. (spec: "Components")
- `written-mode` and `oral-mode` never state the answer / never explain the concept first — they only probe and flag gaps. No automated test covers this judgment; verify manually against fixture data, same rationale Slides2Grades already documents for its own skills. (spec: "Components", "Testing")

---

### Task 1: Document `.courseinfo.yaml` in Slides2Grades's STYLEGUIDE

**Files:**
- Modify: `Slides2Grades/STYLEGUIDE.md`

**Interfaces:**
- Produces: the `.courseinfo.yaml` schema (`exam_type: written|oral`) that Task 3's `vault.py` parses. No code produced by this task.

- [x] **Step 1: Add the schema section**

Add a new section to `Slides2Grades/STYLEGUIDE.md`, after the existing "Vault Structure" section:

```markdown
## Course Config (`.courseinfo.yaml`)

Each course folder may hold a `.courseinfo.yaml` file, one level up from
`Week N/` folders, alongside `Begreber.md`:

```yaml
exam_type: written   # or: oral
```

This file is the shared contract between this repo and `Notes2Knowledge`
(a separate, read-only companion tool): `exam_type` tells Notes2Knowledge
whether to run Socratic quizzing (`written`) or explain-back practice
(`oral`) for that course. Slides2Grades itself does not read this file —
it is documented here because this is the single source of truth for the
vault's structure, not because Slides2Grades consumes it.
```

- [x] **Step 2: Verify the file still renders as valid markdown**

Run: `python3 -c "import pathlib; print(len(pathlib.Path('Slides2Grades/STYLEGUIDE.md').read_text(encoding='utf-8')))"`
Expected: prints a number (non-zero), no traceback.

- [x] **Step 3: Commit**

```bash
cd Slides2Grades
git add STYLEGUIDE.md
git commit -m "docs: document .courseinfo.yaml schema for Notes2Knowledge"
```

---

### Task 2: Notes2Knowledge scaffolding

**Files:**
- Create: `Notes2Knowledge/config.example.env`
- Create: `Notes2Knowledge/.gitignore`
- Create: `Notes2Knowledge/requirements-dev.txt`
- Create: `Notes2Knowledge/conftest.py`

**Interfaces:**
- Produces: `sys.path` wired to `Notes2Knowledge/scripts/` for all later test files (Tasks 3–4 import `vault` and `progress` directly, unqualified).

- [x] **Step 1: Create `config.example.env`**

```
VAULT_PATH=/home/youruser/path/to/note-vault
```

- [x] **Step 2: Create `.gitignore`**

```
config.env
data/progress.sqlite
__pycache__/
*.pyc
.pytest_cache/
```

- [x] **Step 3: Create `requirements-dev.txt`**

```
pytest
```

- [x] **Step 4: Create `conftest.py`**

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))
```

- [x] **Step 5: Install dev dependencies and verify pytest runs with zero tests**

```bash
cd Notes2Knowledge
pip install -r requirements-dev.txt
python3 -m pytest -v
```
Expected: `no tests ran` (or equivalent), exit code 0 — confirms pytest and `conftest.py` are wired up before any test file exists.

- [x] **Step 6: Commit**

```bash
git add config.example.env .gitignore requirements-dev.txt conftest.py
git commit -m "chore: scaffold Notes2Knowledge project"
```

---

### Task 3: `vault.py` — read-only vault access

**Files:**
- Create: `Notes2Knowledge/scripts/vault.py`
- Test: `Notes2Knowledge/tests/test_vault.py`
- Create fixtures: `Notes2Knowledge/tests/fixtures/sample_course/.courseinfo.yaml`
- Create fixtures: `Notes2Knowledge/tests/fixtures/sample_course/Week 3/03 - Binary Search Trees.md`
- Create fixtures: `Notes2Knowledge/tests/fixtures/sample_course/Week 3/03 - Binary Search Trees/exercises.md`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces (used by Task 5 and Task 6's skills via Bash CLI calls):
  - `load_config(path: Path | None = None) -> dict[str, str]`
  - `read_courseinfo(vault_path: Path, course: str) -> dict[str, str]`
  - `find_topic_note(vault_path: Path, course: str, topic: str) -> Path`
  - `read_notes(vault_path: Path, course: str, topic: str) -> str`
  - `read_exercises(vault_path: Path, course: str, topic: str) -> str`
  - CLI: `python3 scripts/vault.py courseinfo <course> <key>`, `python3 scripts/vault.py notes <course> <topic>`, `python3 scripts/vault.py exercises <course> <topic>` — each prints the result to stdout and exits 0, or prints an error to stderr and exits 1.

- [x] **Step 1: Write failing tests for `load_config`**

```python
# Notes2Knowledge/tests/test_vault.py
import pytest

from vault import load_config


def test_load_config_parses_key_value_pairs(tmp_path):
    config_file = tmp_path / "config.env"
    config_file.write_text("VAULT_PATH=/tmp/note-vault\n")

    config = load_config(config_file)

    assert config == {"VAULT_PATH": "/tmp/note-vault"}


def test_load_config_missing_file_raises(tmp_path):
    missing_path = tmp_path / "does_not_exist.env"

    with pytest.raises(FileNotFoundError):
        load_config(missing_path)
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd Notes2Knowledge && python3 -m pytest tests/test_vault.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'vault'`

- [x] **Step 3: Implement `load_config`**

```python
# Notes2Knowledge/scripts/vault.py
import os
import sys
from pathlib import Path


def load_config(path: Path | None = None) -> dict[str, str]:
    if path is None:
        env_override = os.environ.get("CONFIG_PATH")
        path = Path(env_override) if env_override else Path(__file__).resolve().parent.parent / "config.env"

    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found at {path}. Copy config.example.env to config.env and fill in your values."
        )

    config: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        config[key.strip()] = value.strip()
    return config
```

- [x] **Step 4: Run tests to verify they pass**

Run: `cd Notes2Knowledge && python3 -m pytest tests/test_vault.py -v`
Expected: 2 passed

- [x] **Step 5: Write failing test for `read_courseinfo`, with fixture**

```yaml
# Notes2Knowledge/tests/fixtures/sample_course/.courseinfo.yaml
exam_type: written
```

```python
# append to Notes2Knowledge/tests/test_vault.py
from pathlib import Path

from vault import read_courseinfo

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_read_courseinfo_parses_exam_type():
    info = read_courseinfo(FIXTURES, "sample_course")

    assert info == {"exam_type": "written"}


def test_read_courseinfo_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        read_courseinfo(FIXTURES, "nonexistent_course")
```

- [x] **Step 6: Run tests to verify the new ones fail**

Run: `cd Notes2Knowledge && python3 -m pytest tests/test_vault.py -v`
Expected: the 2 new tests FAIL with `ImportError: cannot import name 'read_courseinfo'`

- [x] **Step 7: Implement `read_courseinfo`**

```python
# append to Notes2Knowledge/scripts/vault.py

def read_courseinfo(vault_path: Path, course: str) -> dict[str, str]:
    courseinfo_path = Path(vault_path) / course / ".courseinfo.yaml"
    if not courseinfo_path.exists():
        raise FileNotFoundError(
            f"No .courseinfo.yaml found for course '{course}' at {courseinfo_path}. "
            "See Slides2Grades/STYLEGUIDE.md for the schema."
        )

    info: dict[str, str] = {}
    for line in courseinfo_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition(":")
        info[key.strip()] = value.strip()
    return info
```

- [x] **Step 8: Run tests to verify they pass**

Run: `cd Notes2Knowledge && python3 -m pytest tests/test_vault.py -v`
Expected: 4 passed

- [x] **Step 9: Write failing tests for `find_topic_note` and `read_notes`, with fixtures**

```markdown
# Notes2Knowledge/tests/fixtures/sample_course/Week 3/03 - Binary Search Trees.md
# Binary Search Trees

A **binary search tree (BST)** is a binary tree where each node's left
subtree contains only values less than the node.
```

```python
# append to Notes2Knowledge/tests/test_vault.py
from vault import find_topic_note, read_notes


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
```

- [x] **Step 10: Run tests to verify the new ones fail**

Run: `cd Notes2Knowledge && python3 -m pytest tests/test_vault.py -v`
Expected: the 4 new tests FAIL with `ImportError: cannot import name 'find_topic_note'`

- [x] **Step 11: Implement `find_topic_note` and `read_notes`**

```python
# append to Notes2Knowledge/scripts/vault.py

def find_topic_note(vault_path: Path, course: str, topic: str) -> Path:
    course_dir = Path(vault_path) / course
    matches = list(course_dir.glob(f"Week */{topic}.md"))
    if not matches:
        raise FileNotFoundError(
            f"No topic note found for '{topic}' in course '{course}' under {course_dir}. "
            "Run Slides2Grades first to create it."
        )
    return matches[0]


def read_notes(vault_path: Path, course: str, topic: str) -> str:
    note_path = find_topic_note(vault_path, course, topic)
    content = note_path.read_text(encoding="utf-8")
    if not content.strip():
        raise ValueError(f"Topic note at {note_path} is empty. Run Slides2Grades first to add content.")
    return content
```

- [x] **Step 12: Run tests to verify they pass**

Run: `cd Notes2Knowledge && python3 -m pytest tests/test_vault.py -v`
Expected: 8 passed

- [x] **Step 13: Write failing tests for `read_exercises`, with fixture**

```markdown
# Notes2Knowledge/tests/fixtures/sample_course/Week 3/03 - Binary Search Trees/exercises.md
## Exercise 1
Insert 5, 3, 8, 1 into an empty BST. Draw the result.
```

```python
# append to Notes2Knowledge/tests/test_vault.py
from vault import read_exercises


def test_read_exercises_returns_content():
    content = read_exercises(FIXTURES, "sample_course", "03 - Binary Search Trees")

    assert "Insert 5, 3, 8, 1" in content


def test_read_exercises_missing_raises(tmp_path):
    course_dir = tmp_path / "sample_course" / "Week 1"
    course_dir.mkdir(parents=True)
    (course_dir / "01 - No Exercises.md").write_text("# No Exercises\n")

    with pytest.raises(FileNotFoundError):
        read_exercises(tmp_path, "sample_course", "01 - No Exercises")
```

- [x] **Step 14: Run tests to verify the new ones fail**

Run: `cd Notes2Knowledge && python3 -m pytest tests/test_vault.py -v`
Expected: the 2 new tests FAIL with `ImportError: cannot import name 'read_exercises'`

- [x] **Step 15: Implement `read_exercises`**

```python
# append to Notes2Knowledge/scripts/vault.py

def read_exercises(vault_path: Path, course: str, topic: str) -> str:
    note_path = find_topic_note(vault_path, course, topic)
    exercises_path = note_path.parent / note_path.stem / "exercises.md"
    if not exercises_path.exists():
        raise FileNotFoundError(
            f"No exercises.md found for topic '{topic}' at {exercises_path}. "
            "Run Slides2Grades's review-notes skill or add exercises manually first."
        )
    return exercises_path.read_text(encoding="utf-8")
```

- [x] **Step 16: Run tests to verify they pass**

Run: `cd Notes2Knowledge && python3 -m pytest tests/test_vault.py -v`
Expected: 10 passed

- [x] **Step 17: Write failing CLI smoke test**

```python
# append to Notes2Knowledge/tests/test_vault.py
import os
import subprocess
import sys

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "vault.py"


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
```

Note: the CLI resolves `vault_path` the same way it resolves everything
else — via `load_config()`'s `VAULT_PATH` key — except these two tests
shortcut that with a `VAULT_FIXTURE_PATH` env var the CLI checks first,
so the test suite never needs a real `config.env`. This is test-only
plumbing; `VAULT_FIXTURE_PATH` is not part of the public interface.

- [x] **Step 18: Run test to verify it fails**

Run: `cd Notes2Knowledge && python3 -m pytest tests/test_vault.py -v`
Expected: the 2 new tests FAIL (no `__main__` dispatch exists yet in `vault.py`, so the subprocess exits with a traceback or nonzero for the wrong reason)

- [x] **Step 19: Implement the CLI dispatch**

```python
# append to Notes2Knowledge/scripts/vault.py

def _resolve_vault_path() -> Path:
    fixture_override = os.environ.get("VAULT_FIXTURE_PATH")
    if fixture_override:
        return Path(fixture_override)
    return Path(load_config()["VAULT_PATH"])


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: vault.py (courseinfo|notes|exercises) ...", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]
    try:
        vault_path = _resolve_vault_path()
        if command == "courseinfo":
            _, course, key = sys.argv[1:4]
            info = read_courseinfo(vault_path, course)
            if key not in info:
                print(f"Missing courseinfo key: {key}", file=sys.stderr)
                sys.exit(1)
            print(info[key])
        elif command == "notes":
            _, course, topic = sys.argv[1:4]
            print(read_notes(vault_path, course, topic))
        elif command == "exercises":
            _, course, topic = sys.argv[1:4]
            print(read_exercises(vault_path, course, topic))
        else:
            print(f"Unknown command: {command}", file=sys.stderr)
            sys.exit(1)
    except (FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [x] **Step 20: Run full test file to verify everything passes**

Run: `cd Notes2Knowledge && python3 -m pytest tests/test_vault.py -v`
Expected: 12 passed

- [x] **Step 21: Commit**

```bash
git add scripts/vault.py tests/test_vault.py tests/fixtures/sample_course
git commit -m "feat: add read-only vault access module"
```

---

### Task 4: `progress.py` — local struggle-tracking log

**Files:**
- Create: `Notes2Knowledge/scripts/progress.py`
- Test: `Notes2Knowledge/tests/test_progress.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (independent of `vault.py`).
- Produces (used by Task 5 and Task 6's skills via Bash CLI calls):
  - `record_outcome(db_path: Path, course: str, topic: str, concept: str, outcome: str) -> None` — `outcome` must be `"struggled"` or `"solid"`, else raises `ValueError`.
  - `get_weakest_topic(db_path: Path, course: str) -> str | None` — returns the topic with the most `"struggled"` rows for that course (ties broken by least-recently-seen), or `None` if the course has no rows yet.
  - CLI: `python3 scripts/progress.py record <course> <topic> <concept> <struggled|solid>`, `python3 scripts/progress.py weakest <course>` — prints the topic (or nothing + exit 1 if `None`) to stdout and exits 0, or prints an error to stderr and exits 1.

- [x] **Step 1: Write failing test for `record_outcome`**

```python
# Notes2Knowledge/tests/test_progress.py
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
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd Notes2Knowledge && python3 -m pytest tests/test_progress.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'progress'`

- [x] **Step 3: Implement schema creation and `record_outcome`**

```python
# Notes2Knowledge/scripts/progress.py
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

VALID_OUTCOMES = ("struggled", "solid")


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course TEXT NOT NULL,
            topic TEXT NOT NULL,
            concept TEXT NOT NULL,
            outcome TEXT NOT NULL CHECK (outcome IN ('struggled', 'solid')),
            recorded_at TEXT NOT NULL
        )
        """
    )
    return conn


def record_outcome(db_path: Path, course: str, topic: str, concept: str, outcome: str) -> None:
    if outcome not in VALID_OUTCOMES:
        raise ValueError(f"outcome must be one of {VALID_OUTCOMES}, got {outcome!r}")

    conn = _connect(db_path)
    try:
        conn.execute(
            "INSERT INTO outcomes (course, topic, concept, outcome, recorded_at) VALUES (?, ?, ?, ?, ?)",
            (course, topic, concept, outcome, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()
```

- [x] **Step 4: Run tests to verify they pass**

Run: `cd Notes2Knowledge && python3 -m pytest tests/test_progress.py -v`
Expected: 2 passed

- [x] **Step 5: Write failing tests for `get_weakest_topic`**

```python
# append to Notes2Knowledge/tests/test_progress.py
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
```

- [x] **Step 6: Run tests to verify the new ones fail**

Run: `cd Notes2Knowledge && python3 -m pytest tests/test_progress.py -v`
Expected: the 3 new tests FAIL with `ImportError: cannot import name 'get_weakest_topic'`

- [x] **Step 7: Implement `get_weakest_topic`**

```python
# append to Notes2Knowledge/scripts/progress.py

def get_weakest_topic(db_path: Path, course: str) -> str | None:
    conn = _connect(db_path)
    try:
        row = conn.execute(
            """
            SELECT topic,
                   SUM(CASE WHEN outcome = 'struggled' THEN 1 ELSE 0 END) AS struggles,
                   MAX(recorded_at) AS last_seen
            FROM outcomes
            WHERE course = ?
            GROUP BY topic
            ORDER BY struggles DESC, last_seen ASC
            LIMIT 1
            """,
            (course,),
        ).fetchone()
    finally:
        conn.close()
    return row[0] if row else None
```

- [x] **Step 8: Run tests to verify they pass**

Run: `cd Notes2Knowledge && python3 -m pytest tests/test_progress.py -v`
Expected: 5 passed

- [x] **Step 9: Write failing CLI smoke tests**

```python
# append to Notes2Knowledge/tests/test_progress.py
import os
import subprocess
import sys

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
```

- [x] **Step 10: Run tests to verify they fail**

Run: `cd Notes2Knowledge && python3 -m pytest tests/test_progress.py -v`
Expected: the 2 new tests FAIL (no `__main__` dispatch exists yet)

- [x] **Step 11: Implement the CLI dispatch**

```python
# append to Notes2Knowledge/scripts/progress.py
import os


def _resolve_db_path() -> Path:
    override = os.environ.get("PROGRESS_DB_PATH")
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent / "data" / "progress.sqlite"


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: progress.py (record|weakest) ...", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]
    db_path = _resolve_db_path()

    if command == "record":
        if len(sys.argv) != 6:
            print("Usage: progress.py record <course> <topic> <concept> <struggled|solid>", file=sys.stderr)
            sys.exit(1)
        _, _, course, topic, concept, outcome = sys.argv
        try:
            record_outcome(db_path, course, topic, concept, outcome)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
    elif command == "weakest":
        if len(sys.argv) != 3:
            print("Usage: progress.py weakest <course>", file=sys.stderr)
            sys.exit(1)
        course = sys.argv[2]
        topic = get_weakest_topic(db_path, course)
        if topic is None:
            print(f"No progress history yet for course: {course}", file=sys.stderr)
            sys.exit(1)
        print(topic)
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

Move the `import os` to the top of the file with the other imports rather
than leaving it inline.

- [x] **Step 12: Run full test file to verify everything passes**

Run: `cd Notes2Knowledge && python3 -m pytest tests/test_progress.py -v`
Expected: 7 passed

- [x] **Step 13: Commit**

```bash
git add scripts/progress.py tests/test_progress.py
git commit -m "feat: add local progress-tracking module"
```

---

### Task 5: `written-mode` skill

**Files:**
- Create: `Notes2Knowledge/.claude/skills/written-mode/SKILL.md`

**Interfaces:**
- Consumes: `python3 scripts/vault.py courseinfo <course> exam_type`, `python3 scripts/vault.py notes <course> <topic>`, `python3 scripts/vault.py exercises <course> <topic>`, `python3 scripts/progress.py weakest <course>`, `python3 scripts/progress.py record <course> <topic> <concept> <struggled|solid>` (all from Tasks 3–4).
- Produces: nothing consumed by later tasks — this is a leaf skill, verified manually.

- [x] **Step 1: Write the skill file**

```markdown
---
name: written-mode
description: Socratic quiz session for written-exam courses, drawn from your own notes and exercises. Never states the answer. Use for active recall practice before a written exam.
---

# Written-Mode

Runs a Socratic quiz session against a topic's notes and exercises for a
written-exam course. Never generates or states an answer — only asks,
challenges, and judges.

## Inputs

Course comes from the skill argument; if not supplied, ask.

1. Resolve `exam_type` via `python3 scripts/vault.py courseinfo <course> exam_type`
   from the repo root. If it is not `written`, stop and tell the user to
   use `oral-mode` instead — do not proceed.
2. If a topic was not supplied as an argument, find one via
   `python3 scripts/progress.py weakest <course>`. If that exits nonzero
   (no history yet), ask the user which topic to practice.
3. Read the topic's notes: `python3 scripts/vault.py notes <course> <topic>`.
4. Read the topic's exercises: `python3 scripts/vault.py exercises <course> <topic>`.
   If this exits nonzero (no exercises.md yet), proceed using only the notes.

## What to do

1. Ask one question at a time, drawn from concepts in the notes (and
   exercises, if available). Vary format: definition, application,
   synthesis — same spread `Slides2Grades`'s `review-notes` skill uses.
2. Wait for the user's answer before moving on.
3. Judge the answer against the notes:
   - If correct and complete: say so briefly, move to the next question.
   - If wrong, shallow, or partially correct: push back with a follow-up
     question that narrows toward the gap. **Never state the correct
     answer yourself** — if the user asks for it outright, redirect them
     back to the relevant section of their own notes instead.
4. After each question is resolved (correct or the user gives up), record
   the outcome: `python3 scripts/progress.py record <course> <topic> <concept> <struggled|solid>`
   — `struggled` if they needed more than one follow-up or gave up,
   `solid` if they got it on the first answer.
5. Continue until the user says to stop.

## Output

Nothing is written to any file. The only durable output is the
`progress.py record` calls made during the session.
```

- [x] **Step 2: Manually verify against fixture data**

Using the fixture topic from Task 3
(`Notes2Knowledge/tests/fixtures/sample_course/Week 3/03 - Binary Search Trees.md`),
walk through the skill's own instructions by hand: confirm it would read
the fixture note and exercises via the exact CLI commands above, ask a
question about BSTs, and correctly refuse to state the answer if asked
directly. This mirrors how Slides2Grades's own skills are verified (see
its `CLAUDE.md`: Claude Code's Skill tool can fail to discover
project skills created or modified mid-session, so skill changes are
checked by walking the SKILL.md's instructions against fixture data
rather than a live Skill tool invocation).

- [x] **Step 3: Commit**

```bash
git add .claude/skills/written-mode/SKILL.md
git commit -m "feat: add written-mode skill"
```

---

### Task 6: `oral-mode` skill

**Files:**
- Create: `Notes2Knowledge/.claude/skills/oral-mode/SKILL.md`

**Interfaces:**
- Consumes: `python3 scripts/vault.py courseinfo <course> exam_type`, `python3 scripts/vault.py notes <course> <topic>`, `python3 scripts/progress.py weakest <course>`, `python3 scripts/progress.py record <course> <topic> <concept> <struggled|solid>` (all from Tasks 3–4). Does not use `vault.py exercises` — explain-back practice works from notes alone.
- Produces: nothing consumed by later tasks — this is a leaf skill, verified manually.

- [x] **Step 1: Write the skill file**

```markdown
---
name: oral-mode
description: Feynman-style explain-back session for oral-exam courses, drawn from your own notes. You explain first; the skill only flags gaps. Use for oral exam practice.
---

# Oral-Mode

Runs a Feynman-technique explain-back session against a topic's notes for
an oral-exam course. You explain the concept first; this skill only
points out gaps or errors — it never explains the concept for you.

## Inputs

Course comes from the skill argument; if not supplied, ask.

1. Resolve `exam_type` via `python3 scripts/vault.py courseinfo <course> exam_type`
   from the repo root. If it is not `oral`, stop and tell the user to use
   `written-mode` instead — do not proceed.
2. If a topic was not supplied as an argument, find one via
   `python3 scripts/progress.py weakest <course>`. If that exits nonzero
   (no history yet), ask the user which topic to practice.
3. Read the topic's notes: `python3 scripts/vault.py notes <course> <topic>`.

## What to do

1. Name a concept from the notes and ask the user to explain it out loud,
   in their own words, as if to an examiner.
2. Wait for their explanation in full before responding.
3. Compare it against the notes:
   - Complete and correct: confirm briefly, move to the next concept.
   - Gaps, vague hand-waving, or errors: point out specifically what was
     missed or wrong, and ask them to try explaining that part again.
     **Never supply the missing explanation yourself** — redirect them
     to try again or to re-read the relevant section of their own notes.
4. After each concept is resolved, record the outcome:
   `python3 scripts/progress.py record <course> <topic> <concept> <struggled|solid>`
   — `struggled` if it took more than one attempt, `solid` if their first
   explanation was complete and correct.
5. Continue until the user says to stop.

## Output

Nothing is written to any file. The only durable output is the
`progress.py record` calls made during the session.
```

- [x] **Step 2: Manually verify against fixture data**

Using the same fixture topic as Task 5, walk through the skill's own
instructions by hand: confirm it would read the fixture note via the
exact CLI command above, prompt for an explanation of BSTs, and correctly
withhold the explanation itself if the user asks for it outright instead
of attempting one.

- [x] **Step 3: Commit**

```bash
git add .claude/skills/oral-mode/SKILL.md
git commit -m "feat: add oral-mode skill"
```
