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
        value = value.partition("#")[0]
        info[key.strip()] = value.strip()
    return info


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


def read_exercises(vault_path: Path, course: str, topic: str) -> str:
    note_path = find_topic_note(vault_path, course, topic)
    exercises_path = note_path.parent / note_path.stem / "exercises.md"
    if not exercises_path.exists():
        raise FileNotFoundError(
            f"No exercises.md found for topic '{topic}' at {exercises_path}. "
            "Run Slides2Grades's review-notes skill or add exercises manually first."
        )
    return exercises_path.read_text(encoding="utf-8")


def _resolve_vault_path() -> Path:
    fixture_override = os.environ.get("VAULT_FIXTURE_PATH")
    if fixture_override:
        return Path(fixture_override)
    config = load_config()
    if "VAULT_PATH" not in config:
        raise ValueError("config.env is missing the VAULT_PATH key. See config.example.env for the expected format.")
    return Path(config["VAULT_PATH"])


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
