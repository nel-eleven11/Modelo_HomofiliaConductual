# Gemini full-cohort pilot implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Run one 80-student, ten-semester homophily-medium simulation with seed 1, Gemini language, and local sentiment, preserving complete outputs and a $10 usage guard.

**Architecture:** A dedicated runner uses the existing model and providers. A per-week SQLite checkpoint stores completed state and all directed evaluations and opportunities. On resume, the model clock is fast-forwarded without simulation, then agent state and current section membership are restored. Final outputs use the existing run persistence and mechanism exports.

**Tech Stack:** Python, Mesa, SQLite, Google GenAI, Transformers, Parquet, NetworkX.

**Spec:** User's single-real-run request and `AGENTS.md` methodology.

## Global constraints

- One scenario: `homophily_medium`, `h=0.50`; seed 1; full 80-student 10-semester horizon.
- Keep all social equations and exposure updates unchanged.
- Never expose the API key or run API calls in unit tests.
- Stop before estimated paid token cost exceeds $10; record usage and cache hits.
- Save real model and sentiment versions, prompt version, code commit, full config, and every derived output.

## Review focus

- A midweek interruption must not lose completed weeks or cause charged requests to repeat when cached.
- Restored section order and model clock must match uninterrupted execution.
- Final interaction count must equal exposure count plus response count.
- Cost estimates must include output and reasoning tokens where usage metadata reports them.
- A missing sentiment model or API quota must fail visibly, leaving a resumable checkpoint.

## Tasks

- [ ] Add a dedicated real-run CLI and weekly checkpoint with resume checks.
- [ ] Add cost guard and per-week usage recording.
- [ ] Add offline checkpoint/resume tests with mocks and a short smoke run.
- [ ] Complete a small live API and local sentiment preflight.
- [ ] Execute the full run, export mechanism tables and graphs, and verify all outputs.
