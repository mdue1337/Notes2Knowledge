# Notes2Knowledge

A read-only companion to [Slides2Grades](https://github.com/mdue1337/Slides2Grades)
that checks whether you actually learned your notes, instead of producing more of
them. It never generates answers or explanations — it only quizzes you on your own
vault content and tracks where you struggle.

See `docs/superpowers/specs/2026-10-01-notes2knowledge-design.md` for the full design.

## Two modes

| Skill | For courses with | Behavior |
|---|---|---|
| `written-mode` | `exam_type: written` | Socratic quiz drawn from the topic's notes and exercises. Pushes back on wrong or shallow answers, never states the answer itself. |
| `oral-mode` | `exam_type: oral` | Feynman-style: you explain the concept first; the skill only flags gaps or errors in your explanation. |

Exam type is read per-course from `.courseinfo.yaml` in the vault (schema documented
in `Slides2Grades/STYLEGUIDE.md`). Invoking the wrong mode for a course is a hard
error, not a silent fallback.

## Setup

1. Copy the config template and point it at your vault:

   ```bash
   cp config.example.env config.env
   ```

   Edit `config.env`:

   ```
   VAULT_PATH=/path/to/your/note-vault
   ```

2. Install dev dependencies:

   ```bash
   pip install -r requirements-dev.txt     # pytest, for running the test suite
   ```

## Read-only, on purpose

No script in this repo ever writes into the vault — `scripts/vault.py` has no write
methods at all. The only durable output is a local `data/progress.sqlite` log of
`struggled`/`solid` outcomes per concept, written by `scripts/progress.py`, which
`get_weakest_topic` queries to pick what to practice next. This separation from
Slides2Grades (which does read/write the vault) is deliberate friction: a tool that
can only probe your understanding, never hand you the answer, has to live one
deliberate context-switch away from the tools that produce content.

## Running tests

```bash
python3 -m pytest -v
```
