import os
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
