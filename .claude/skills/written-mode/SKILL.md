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
