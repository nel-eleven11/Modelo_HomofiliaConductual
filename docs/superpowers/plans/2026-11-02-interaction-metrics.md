# Interaction mechanisms and network exports implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Persist participation opportunities and derive reproducible semester summaries, complementary active-response networks, graph exports, and figures without changing the evaluation network's existing metrics.

**Architecture:** Keep the simulation's directed evaluation records and relationship updates. Record each Bernoulli opportunity before the initial message is evaluated; use the saved opportunities and directed evaluations to derive all new summaries after a run. Treat response edges as a separate network and use previous-semester evaluation communities for mixing.

**Tech Stack:** Python, Pydantic, pandas/Parquet, NetworkX, Matplotlib, pytest, Ruff.

**Spec:** `docs/experiments/mechanism_metrics.md`, reflecting the user's approved extension; project methodology in `AGENTS.md`.

## Review focus

- Nonresponders must still produce an initial directed evaluation.
- Participation must use the relationship before that evaluation.
- Saved opportunities and evaluations must satisfy exposure plus response accounting.
- Historical evaluation-network metric names and definitions must remain stable.
- Missing denominators must remain undefined rather than being treated as zero.

## Global constraints

- No branches or push.
- No real API requests in tests or fast simulations.
- Preserve old metric names and definitions.
- Seeded simulation; all summaries rebuild from saved records without Gemini.
- Strong tie threshold defaults to 0.70 and is recorded.

## Tasks

- [x] Add a typed participation opportunity record before evaluation; persist it and test the prior, response direction, and nonresponse update.
- [x] Derive semester interaction, topic, relationship, student, active-response, and prior-community summaries from saved records.
- [x] Integrate scenario and sensitivity tables, aggregate summaries, and paired differences; test mock runs and reconstruction.
- [x] Export evaluation and active-response GraphML and plot mechanism trajectories and selected snapshots.
- [x] Document definitions and verify focused tests, all tests, lint, and short mock simulations.
