# Bikeshare demand capstone

Reference repository for the DSC 180A methodology lesson on agentic
programming. Forecasts daily Capital Bikeshare ridership (`cnt`) for
Washington, DC, 2011-2012, with a leakage trap in the data.

The agent is Claude Code. This repository was developed with **hosted Claude
(Opus 5.5) through a signed-in Claude subscription**: `.claude/settings.json`
sets `"model": "opus"` and has no endpoint overrides. Running a local
open-weight model through Ollama is still supported as an optional route,
described below.

## Setup (hosted Claude, as used for this repo)

    # 1. Claude Code, signed in to a Claude plan (run `claude`, then /login)
    curl -fsSL https://claude.ai/install.sh | bash

    # 2. This repo
    python3 -m venv .venv && source .venv/bin/activate   # fish: activate.fish
    pip install -r requirements.txt

    # 3. Pipeline and checks
    make all            # data -> features -> train; writes reports/metrics.json
    make test           # runs the verification suite

    # 4. Start the agent, from the repo root
    claude

Run `/status` inside Claude Code to confirm the model is Opus. No
`ANTHROPIC_*` environment variables are needed for this route; if any are
set in your shell, check they do not point at a local server.

## Commands used for the reported results

    make all                                            # official, untransformed metrics
    make test                                           # verification suite
    python -m src.train --validation-target-experiment  # Exercise 4, validation only
    python -m src.train --final-target-test             # Exercise 4, single final test look

    # SDK audit of this repo (separate terminal, not inside a Claude session)
    env AUDIT_MODEL=opus python agent/audit.py . --out reports/audit.jsonl

`make all` reproduces `reports/metrics.json`. The two `src.train` flags
write `reports/target_transform_validation.json` and
`reports/target_transform_final_test.json` and leave `metrics.json`
untouched. `agent/audit.py` drives the same Claude Code binary as the
interactive agent; `AUDIT_MODEL` selects the model, and its built-in default
is the local `bikeshare-coder`, so set `AUDIT_MODEL` for the hosted route.

## Optional: a local model through Ollama

The starter's original route. Claude Code drives an open-weight model on your
own machine, with no Anthropic account. It was **not** used for the results
in this repo.

    ollama serve                         # https://ollama.com/download; own terminal
    make model                           # pulls the base model, builds `bikeshare-coder` (64k context)
    make check-model                     # confirms Claude Code can reach it and tool calls work

Then point Claude Code at it in `.claude/settings.local.json` (git-ignored)
rather than editing `settings.json`:

    {
      "model": "bikeshare-coder",
      "env": {
        "ANTHROPIC_BASE_URL": "http://localhost:11434",
        "ANTHROPIC_AUTH_TOKEN": "ollama",
        "ANTHROPIC_API_KEY": ""
      }
    }

For the SDK auditor on this route, leave `AUDIT_MODEL` unset (it defaults to
`bikeshare-coder`).

### Which base model

`make model` builds from `qwen3.5:9b` by default. Pick by memory:

| Your machine | Base model | `make model` command |
|---|---|---|
| 16 GB RAM (any laptop) | `qwen3.5:9b` (~7 GB) | `make model` |
| 32 GB RAM, or 24 GB+ Apple Silicon | `qwen3.5:27b` (~18 GB) | `make model BASE=qwen3.5:27b` |
| 48 GB+ | `qwen3.5:35b` (~22 GB) | `make model BASE=qwen3.5:35b` |

The 64k context window adds several GB on top of the download size at run
time. If the model runs but is painfully slow, drop a size, not the context.
Ollama can also serve models from its cloud (`ANTHROPIC_BASE_URL`
`https://ollama.com` with an Ollama API key); model names and free-tier
limits change, so check `ollama.com/search?c=cloud`. Record which model you
used in `REPORT.md`.

## Data

Daily aggregation of the UCI Bike Sharing Dataset (Fanaee-T and Gama, 2013),
via the processed mirror used in Molnar's *Interpretable Machine Learning*:

    https://raw.githubusercontent.com/christophM/interpretable-ml-book/master/data/bike.csv

The mirror differs from the UCI file. See `src/config.py` for the list.
`data/raw/bike_daily.csv` is a checked-in copy so the pipeline runs offline.
Claude's `Edit`/`Write` tools are denied on `data/raw/` in
`.claude/settings.json`, but that does not stop a shell command (see fault 4
in `docs/SEEDED_FAULTS.md`). What protects the numbers is `load_raw()`,
which refuses any file whose SHA-256 differs from `RAW_SHA256` in
`src/config.py`.

`python -m src.leakage_demo` reproduces the R^2 = 1.000 result from the lesson.

## Layout

See `CLAUDE.md` for the standing rules and `src/config.py` for every constant.
`.claude/` holds the hook, permissions, reviewer subagent, the starter's
`new-feature` skill and our `seed-fault` skill. `model/` holds the Modelfile
and readiness check for the optional Ollama route. `agent/audit.py` is the
Agent SDK batch auditor. Results and their interpretation are in
`REPORT.md`; methodological decisions in `docs/DECISIONS.md`; fault
evidence in `docs/SEEDED_FAULTS.md`.
