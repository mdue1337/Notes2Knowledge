# Notes2Knowledge Design

## Problem

A 2026-09-30 AI-in-education workshop (NordAI Future Workshop, group DK-01)
surfaced a concrete worry from building an AI-coded prototype: using GenAI
tools shifts a student from *learning* to *producing*, loses control over
what's actually understood, and the gap between ambition and laziness is
easy to paper over. The group's own vision for a fix: GenAI as a study buddy
that "knows as much as you but can challenge you" — able to assist in
problem-solving, but **unable to generate solutions**.

The existing `Slides2Grades` project turns lecture material into polished
notes, questions, and flashcards — all producing skills. That's valuable,
but it's entirely one-directional: material in, artifacts out. Nothing in
that pipeline checks whether the artifacts it produced actually got learned.
Notes2Knowledge is the other half: a tool whose only output is pressure on
you to demonstrate understanding, never content.

## Relationship to Slides2Grades

Two separate repos, intentionally not merged — same reasoning Slides2Grades
already uses for its own vault split, pushed one level further:

- **`Slides2Grades`**: material → artifacts (notes, exercises, flashcards,
  exam questions). Read/write against `note-vault`.
- **`Notes2Knowledge`** (this repo): material → internalized understanding.
  **Read-only** against `note-vault`. No script in this repo ever writes
  into the vault — that boundary is the guardrail against sliding back into
  "just produce the answer," not just a style choice.

The separation is deliberate friction. A challenge skill living next to
`flashcards-make` is one lazy evening away from "just give me the answer."
A separate repo means deliberately switching tools to ask for a shortcut.

**Shared contract, not shared code:** both repos read the same per-course
config file (`.courseinfo.yaml`, in each course folder in `note-vault`),
which must therefore be documented once, in `Slides2Grades/STYLEGUIDE.md`,
as the single source of truth for its schema. `Notes2Knowledge` depends on
that doc but does not duplicate or own it.

**Prerequisite change to `Slides2Grades` (out of scope for this repo's
implementation, tracked here as a dependency):** `STYLEGUIDE.md` gains a
section defining `.courseinfo.yaml`:

```yaml
exam_type: written   # or: oral
```

(This also absorbs the old note-vault TODO about a per-course lecture-
language config — same file, same mechanism, if/when that's added.)

## Architecture

```
Notes2Knowledge/
  .claude/skills/
    written-mode/SKILL.md
    oral-mode/SKILL.md
  scripts/
    vault.py       # read-only vault access, same VAULT_PATH contract as Slides2Grades's config.py
    progress.py    # narrow queries/writes against data/progress.sqlite
  data/
    progress.sqlite
  config.example.env   # VAULT_PATH, same shape as Slides2Grades
  tests/
    test_vault.py
    test_progress.py
```

## Components

| Skill | Targets | Behavior |
|---|---|---|
| `written-mode` | courses with `exam_type: written` | Socratic Q&A: asks questions drawn from the topic's `notes.md` / `exercises.md`, pushes back on wrong or shallow answers, **never states the answer itself** |
| `oral-mode` | courses with `exam_type: oral` | Feynman-style: you explain the concept first; the skill only flags gaps or errors in your explanation |

Both skills are thin prompts over two shared scripts:

- **`vault.py`**: resolves `VAULT_PATH` from `config.env` (same resolution
  order as Slides2Grades's `scripts/config.py`: explicit arg → `CONFIG_PATH`
  env var → `<repo root>/config.env`), reads a topic's `notes.md` /
  `exercises.md` / course's `.courseinfo.yaml`. No write methods exist in
  this module at all — not just unused, absent, so there's nothing to
  accidentally call.
- **`progress.py`**: narrow, purpose-built queries against
  `data/progress.sqlite` — e.g. `get_weakest_topic(course)` returning one
  (or a handful of) rows, and `record_outcome(course, topic, concept,
  outcome)` appending one row. No method returns a full table dump.

## Data Flow

1. You invoke `written-mode` or `oral-mode` for a course (optionally naming
   a specific topic).
2. The skill reads that course's `.courseinfo.yaml` via `vault.py`. A
   mismatch — e.g. invoking `oral-mode` on a course marked `written` —
   is a hard error, not a silent override, matching Slides2Grades's
   no-silent-fallback precedent (its transcription script's CUDA check).
3. If no topic was named, the skill calls
   `progress.get_weakest_topic(course)` to pick the least-solid or
   least-recently-reviewed topic.
4. `vault.py` pulls that topic's `notes.md` (+ `exercises.md` for
   written-mode) from `note-vault`. Read only.
5. The skill runs the Q&A / explain-back loop entirely in conversation —
   no file is written during the session.
6. At session end, the skill calls `progress.record_outcome(...)` once per
   concept probed: course, topic, concept, outcome (struggled/solid),
   timestamp.

**Token cost stays flat regardless of database size**, because every query
is narrow by construction (`get_weakest_topic` returns one row, not
history) — the same reason Slides2Grades's skills shell out to
`config.py VAULT_PATH` instead of reading `config.env` inline: a script
boundary that returns a small, specific answer instead of raw data dumped
into context.

## Error Handling

- No `.courseinfo.yaml` for a course → hard error, pointing at
  `Slides2Grades/STYLEGUIDE.md`'s schema doc. No guessing an exam type.
- Topic has no vault content yet → hard error telling you to run
  Slides2Grades first. This tool never originates content, only probes
  what already exists — that boundary is load-bearing, not incidental.

## Testing

- `vault.py`: path resolution test, mirroring Slides2Grades's
  `test_config.py`.
- `progress.py`: smoke tests for the read/write round trip of
  `get_weakest_topic` / `record_outcome` against a scratch SQLite file.
- The Q&A / explain-back judgment itself: no automated suite — same
  "generative, not deterministic correctness" rationale Slides2Grades
  already documents for its own skills. Verified manually against fixture
  notes.

## Out of Scope (for this design)

- The `Slides2Grades/STYLEGUIDE.md` edit itself (tracked above as a
  prerequisite, implemented separately in that repo).
- Any UI beyond Claude Code's chat interface.
- Cross-course analytics or dashboards over `progress.sqlite` — the only
  consumer of that data is `get_weakest_topic`, nothing else yet.
- Packaging/distribution beyond personal use.

## Implementation Phases

1. `Slides2Grades/STYLEGUIDE.md`: document `.courseinfo.yaml` schema
   (prerequisite, separate repo).
2. `Notes2Knowledge` scaffolding: `config.example.env`, `vault.py`,
   `progress.sqlite` schema + `progress.py`.
3. `written-mode` skill.
4. `oral-mode` skill.
