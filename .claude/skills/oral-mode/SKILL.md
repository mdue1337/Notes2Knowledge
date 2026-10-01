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
