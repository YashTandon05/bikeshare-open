---
name: seed-fault
description: Run one prescribed seeded-fault experiment end to end. Inject a single fault into src/ with Edit, capture the automatic hook feedback and the red test output before repairing, revert, re-verify, append evidence to docs/SEEDED_FAULTS.md, update the rubric tracker, and commit. Manual use only.
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
`old_string`/`new_string` exactly as given, so the diff is one line and the
repair is exact.

| `$ARGUMENTS` | old_string | new_string | Test expected to go red |
|---|---|---|---|
| `forbidden-column` | `return [c for c in numeric if c not in FORBIDDEN]` | `return [c for c in numeric if c not in FORBIDDEN or c == "casual"]` | `test_no_forbidden_features` |
| `rolling-leakage` | `out["cnt_roll_7"] = out[TARGET].shift(1).rolling(WEEK_DAYS).mean()` | `out["cnt_roll_7"] = out[TARGET].rolling(WEEK_DAYS).mean()` | `test_rolling_mean_excludes_today` |
| `weather-guard` | `    if unknown:\n        raise ValueError(f"unmapped weather labels: {sorted(unknown)}")\n` | *(empty: delete both lines)* | `test_unknown_weather_label_is_rejected` |

The "expected" column is a prediction. Record whatever actually goes red,
and if it differs, say so.

## Evidence rules

- **Never invent output.** Paste only text that a command printed or that
  Claude Code showed. If something you expected did not appear, write
  "did not appear" and leave it at that.
- **Automatic hook feedback** is the message Claude Code shows right after
  the `Edit`, starting `PostToolUse:Edit hook blocking error from command:`.
  Copy it verbatim from that message. Claude Code only reports a *blocking*
  error when the hook exits 2. Record that as "exit 2, inferred from the
  blocking-error report", not as an exit code you saw.
- **Manual hook diagnostic** is optional and is a different thing: you run
  the hook script yourself to get its exit code. Label it
  "Manual hook diagnostic (run by hand, not the automatic trigger)". Never
  present it as the automatic run.
- Evidence files go in `/tmp/seed-fault/$ARGUMENTS/`, outside the repo.

## Steps

### 1. Preconditions

```bash
EV=/tmp/seed-fault/$ARGUMENTS; rm -f "$EV"/*; mkdir -p "$EV"
git status --porcelain            # must print nothing
make test > "$EV/pre_test.txt" 2>&1; echo "exit=$?" >> "$EV/pre_test.txt"
tail -2 "$EV/pre_test.txt"        # must show all passing and exit=0
git rev-parse --short HEAD > "$EV/start_commit.txt"
sha256sum data/raw/bike_daily.csv > "$EV/raw_sha_before.txt"
```

If the tree is dirty or a test fails, stop. Do not seed onto a broken base.

### 2. Seed the fault

Make **one** `Edit` call on `src/features.py` with the strings from the
table. Do not use Bash, sed, or Write. The point is that the real
`PostToolUse` hook fires.

Copy the automatic hook feedback verbatim into `$EV/hook_auto.txt`, or
write `did not appear` there.

### 3. Capture everything before repairing

Nothing in `src/` changes until all of these exist:

```bash
git diff -- src/ > "$EV/diff.txt"; cat "$EV/diff.txt"
make test > "$EV/red_test.txt" 2>&1; echo "exit=$?" >> "$EV/red_test.txt"
cat "$EV/red_test.txt"
```

The diff must be the one intended line, and `make test` must exit non-zero.
If the suite stays green, record that as the finding (a fault the suite
misses) and still repair and commit.

Optional manual diagnostic. Label it as such:

```bash
printf '{"tool_input":{"file_path":"%s"}}' "$PWD/src/features.py" \
  | CLAUDE_PROJECT_DIR="$PWD" .claude/hooks/check_leakage.sh \
  > "$EV/hook_manual.txt" 2>&1; echo "exit=$?" >> "$EV/hook_manual.txt"
```

### 4. Repair, counting turns

**Turn convention:** a repair turn is one tool call made after step 3
ends, up to and including the first `make test` that passes. Reads,
diagnostic runs, edits, and the final `make test` all count. Report it as
`N tool calls (E edits)`. The agent seeded the fault itself and knows the
fix, so this is a **lower bound**, not a measure of diagnosing blind. Say
that in the record.

Repair with one `Edit` that swaps `new_string` and `old_string`. Change
nothing else. The hook fires again; note whether it was silent. Then:

```bash
git diff --quiet -- src/ && echo "src/ identical to HEAD"
make test > "$EV/green_test.txt" 2>&1; echo "exit=$?" >> "$EV/green_test.txt"
tail -2 "$EV/green_test.txt"
sha256sum -c "$EV/raw_sha_before.txt"
```

If `src/` is not identical to HEAD, or any test fails, keep repairing and
keep counting.

### 5. Append evidence

Append to `docs/SEEDED_FAULTS.md` with `cat >>` or `printf >>`. Never use
Write, and never truncate the file. Add one section:

```
## Fault: $ARGUMENTS
Date, starting commit, raw CSV sha256 before/after.
### Change          (contents of diff.txt)
### Automatic hook feedback (PostToolUse)   (hook_auto.txt, verbatim, with exit-code note)
### Manual hook diagnostic                  (only if run, labelled)
### Red test output (contents of red_test.txt, including exit=)
### Repair          (turn count and convention, repair-hook result, green summary + exit=)
```

Check that nothing was overwritten. This should show zero deleted lines:

```bash
git diff --numstat -- docs/SEEDED_FAULTS.md
```

### 6. Update the tracker

In `docs/RUBRIC_CHECKLIST.md`, tick **Impl** for this fault's rows in
sections 3 and 5 (red output, hook stderr) and update the Exercise 2 line.
Cite the `docs/SEEDED_FAULTS.md` section heading. Leave **Verified**
unticked. Commit-history row 4 is ticked only once all three faults are
committed.

### 7. Commit

One commit per experiment. Commit only the docs; `src/` is back to HEAD.

```bash
git add docs/SEEDED_FAULTS.md docs/RUBRIC_CHECKLIST.md
git commit -m "Seed and fix <fault>: <what the fault did>; reverted <what>"
```

For example: `Seed and fix forbidden-column: casual admitted via
feature_columns(); reverted to FORBIDDEN filter`. Do not push. Report the
red test names, the hook result, the turn count, and the commit hash.
