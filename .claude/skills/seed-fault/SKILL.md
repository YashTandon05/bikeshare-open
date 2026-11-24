---
name: seed-fault
description: Run one prescribed seeded-fault experiment end to end. Inject a single fault into src/ with Edit, capture the automatic hook feedback, a manual hook diagnostic, and the red test output before repairing, revert, re-verify, append evidence to docs/SEEDED_FAULTS.md, update the rubric tracker, and commit. Manual use only.
argument-hint: forbidden-column | rolling-leakage | weather-guard
disable-model-invocation: true
---

# Seeded fault: $ARGUMENTS

Run exactly one experiment, for the fault named `$ARGUMENTS`. If
`$ARGUMENTS` is empty or not one of the three names below, stop and say so.
Do not guess which fault was meant.

This skill never writes to `data/raw/`. Fault 4 (a `cp` into `data/raw/`
from Bash) is run by hand, outside this skill.

## The faults

Each fault is one `Edit` to `src/features.py` that still parses. Use
`old_string`/`new_string` exactly as given.

| `$ARGUMENTS` | old_string | new_string | Required diff | Test expected to go red |
|---|---|---|---|---|
| `forbidden-column` | `return [c for c in numeric if c not in FORBIDDEN]` | `return [c for c in numeric if c not in FORBIDDEN or c == "casual"]` | 1 line changed (1 `-`, 1 `+`) | `test_no_forbidden_features` |
| `rolling-leakage` | `out["cnt_roll_7"] = out[TARGET].shift(1).rolling(WEEK_DAYS).mean()` | `out["cnt_roll_7"] = out[TARGET].rolling(WEEK_DAYS).mean()` | 1 line changed (1 `-`, 1 `+`) | `test_rolling_mean_excludes_today` |
| `weather-guard` | `    if unknown:\n        raise ValueError(f"unmapped weather labels: {sorted(unknown)}")\n` | *(empty)* | 2 lines removed (2 `-`, 0 `+`) | `test_unknown_weather_label_is_rejected` |

The diff must be exactly the chosen fault's row: those lines, in
`src/features.py`, and nothing else. The "expected to go red" column is a
prediction. Record whatever actually goes red, and if it differs, say so.

## Evidence rules

- **Never invent output.** Paste only text that a command printed or that
  Claude Code showed. If something did not appear, write "did not appear".
- **Automatic hook feedback** is the message Claude Code shows right after
  an `Edit`, starting `PostToolUse:Edit hook blocking error from command:`.
  Copy it verbatim. Its exit code is never displayed. Record it as "exit 2,
  inferred from the blocking-error report", never as a measured code.
- **Manual hook diagnostic** is required while the code is broken. You run
  the hook script yourself and measure its exit code. Label it
  "Manual hook diagnostic (run by hand, not the automatic trigger)". It is
  never evidence that the automatic hook fired.
- **Evidence directory.** Each run gets a new directory. Shell variables do
  **not** carry between Bash tool calls, so start every Bash call with
  `EV=<absolute path from step 1>;`. Never delete or reuse an earlier run's
  directory.

## Counting convention (state it in every record)

We do not count conversational turns. We count two things, both starting
after step 3's capture is complete and ending at the first fully green
`make test`:

- **Repair tool calls**: every tool call in that span (reads, edits,
  diagnostics, test runs).
- **Repair cycles**: one attempted repair (an edit to `src/`) followed by
  one verification run (`make test`). A clean one-shot fix is 1 cycle.

The agent seeded the fault and knows the fix, so both are **lower bounds**,
not measures of diagnosing blind.

## Steps

### 1. Preconditions and evidence directory

```bash
EV=$(mktemp -d "/tmp/seed-fault-$ARGUMENTS-$(date +%Y%m%dT%H%M%S)-XXXX") && echo "EV=$EV"
git status --porcelain            # must print nothing
make test > "$EV/pre_test.txt" 2>&1; echo "exit=$?" >> "$EV/pre_test.txt"
tail -2 "$EV/pre_test.txt"        # must show all passing and exit=0
git rev-parse --short HEAD > "$EV/start_commit.txt"
sha256sum data/raw/bike_daily.csv > "$EV/raw_sha_before.txt"
```

Note the printed `EV=` path. Every later Bash call starts with
`EV=/tmp/seed-fault-...;`, using that literal path. If the tree is dirty
or a test fails, stop. Do not seed onto a broken base.

### 2. Seed the fault

Make **one** `Edit` call on `src/features.py` with the strings from the
table. Do not use Bash, sed, or Write. The point is that the real
`PostToolUse` hook fires.

Write the automatic hook feedback, verbatim, to `$EV/hook_auto.txt`
(through a quoted heredoc in a Bash call that sets `EV`). If no feedback
appeared, write `did not appear`.

### 3. Capture everything before repairing

Nothing in `src/` changes until all of these exist. Run them as one Bash
call, starting with the literal `EV=` path:

```bash
EV=/tmp/seed-fault-...   # literal path from step 1
git diff -- src/ > "$EV/diff.txt"; cat "$EV/diff.txt"
git diff --numstat -- src/ | tee "$EV/numstat.txt"   # must match the "Required diff" column
make test > "$EV/red_test.txt" 2>&1; echo "exit=$?" >> "$EV/red_test.txt"
cat "$EV/red_test.txt"
printf '{"tool_input":{"file_path":"%s"}}' "$PWD/src/features.py" \
  | CLAUDE_PROJECT_DIR="$PWD" .claude/hooks/check_leakage.sh \
  > "$EV/hook_manual.txt" 2>&1; echo "exit=$?" >> "$EV/hook_manual.txt"
cat "$EV/hook_manual.txt"
```

If the numstat is not exactly the chosen fault's row, stop. Repair, and
report that the seed was wrong. If the suite stays green, record that as
the finding (a fault the suite misses), then still repair and commit.

### 4. Repair

Repair with one `Edit` that swaps `new_string` and `old_string`, changing
nothing else. That makes one cycle once `make test` has run. The hook fires
again; record whether it was silent. Then, in one Bash call:

```bash
EV=/tmp/seed-fault-...   # literal path from step 1
git diff --quiet -- src/ && echo "src/ identical to HEAD"
make test > "$EV/green_test.txt" 2>&1; echo "exit=$?" >> "$EV/green_test.txt"
tail -2 "$EV/green_test.txt"
sha256sum -c "$EV/raw_sha_before.txt"
```

If `src/` is not identical to HEAD, or any test fails, run another cycle
and keep counting.

### 5. Append evidence

Append to `docs/SEEDED_FAULTS.md` with `cat >>` or `printf >>`. Never use
Write, and never truncate the file. Add one section:

```
## Fault: $ARGUMENTS
Date, starting commit, evidence directory, raw CSV sha256 before/after.
### Change                                  (diff.txt and numstat.txt)
### Automatic hook feedback (PostToolUse)   (hook_auto.txt verbatim, with the "inferred" exit-code note)
### Manual hook diagnostic (run by hand, not the automatic trigger)   (hook_manual.txt, with measured exit=)
### Red test output                         (red_test.txt, including exit=)
### Repair   (counting convention, repair tool calls, repair cycles, repair-hook result, green summary + exit=)
```

Then confirm nothing was overwritten. This must show zero deleted lines:

```bash
git diff --numstat -- docs/SEEDED_FAULTS.md
```

### 6. Update the tracker

In `docs/RUBRIC_CHECKLIST.md`, tick **Impl** for a fault's row only when
its evidence actually appeared:

- **Red test output row (section 3):** tick only if `make test` exited
  non-zero with a failing test. If the suite stayed green, leave it
  pending and note "suite stayed green".
- **Hook stderr row (section 5):** tick only if *automatic* hook feedback
  appeared. The manual diagnostic alone does not satisfy it. If feedback
  did not appear, leave it pending and say so.

Cite the `docs/SEEDED_FAULTS.md` section heading, and leave **Verified**
unticked. Update the Exercise 2 line. Leave commit-history row 4 pending
until **all four** prescribed experiments (including the manual fault 4)
are recorded and committed.

### 7. Commit

One commit per experiment. Commit only the docs; `src/` is back to HEAD.

```bash
git add docs/SEEDED_FAULTS.md docs/RUBRIC_CHECKLIST.md
git commit -m "Seed and fix <fault>: <what the fault did>; reverted <what>"
```

For example: `Seed and fix forbidden-column: casual admitted via
feature_columns(); reverted to FORBIDDEN filter`. Do not push. Report the
red test names, the automatic hook result, the manual hook exit code, the
repair tool calls and cycles, and the commit hash.
