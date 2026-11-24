# Decisions

One line per methodological decision: what you chose, why, and what it changed.
Agents append here via the `/new-feature` skill; you append here by hand.

- Exclude `casual`, `registered`: they sum to `cnt` exactly. Leaky model R^2 1.000 -> honest ridge 0.583.
- Exclude `cnt_2d_bfr`: a shipped 2-day lag we cannot test the alignment of. Build our own lags instead.
- Exclude `instant`, `yr`, `days_since_2011`: time indexes let a tree predict a flat constant past 2011 and a linear model extrapolate a trend we have no grounds for.
- Split 2011 / H1 2012 / H2 2012 by date. Test set touched once, after all feature work.
- Report mean and persistence baselines with every score. Persistence (test R^2 0.510, MAE 840) is within 0.07 R^2 of ridge and beats it on MAE; that caveat goes in the report.
- 2026-11-24: Agent backend is our existing paid Claude subscription (Claude Sonnet 5.5), not local Ollama `bikeshare-coder`. Why: we already pay for it, and it avoids local RAM/latency limits. Changed `.claude/settings.json`: `model` -> `sonnet`; removed the localhost `ANTHROPIC_*` env overrides; hooks and permissions unchanged. Baseline metrics frozen in `reports/metrics_before_feature.json` (ridge test R^2 0.583) before any feature work.
- 2026-11-24 (correction): The setup checkpoint d85aa8a actually ran on Claude Opus 5.5, not Sonnet 5.5; the earlier Sonnet entry described the intended configuration. We have chosen Opus 5.5 for the remaining assignment work. Changed `.claude/settings.json`: `model` -> `opus`; hooks and permissions unchanged.
- 2026-11-24: Added `cnt_std_7`, the population std (ddof=0, not pandas' default ddof=1) of `cnt` over the 7 calendar days before d. Hypothesis: a jumpy week predicts tomorrow differently from a steady week with the same mean. Availability: uses only `cnt` on d-7..d-1, all observed before d; built after `reindex_to_calendar` with `.shift(1)` before `.rolling(7)`; LAG_WARMUP stays 7 (714 rows, 15 features). Validation R^2: ridge 0.6475 -> 0.7224 (+0.075, MAE 833 -> 700); hgb 0.2185 -> 0.0977 (-0.121, MAE 1297 -> 1382). Ridge clears the 0.01 bar; hgb gets worse, and the 2011-to-2012 range shift does not explain it (only 10% of validation values exceed the 2011 max). Keep/drop decision awaits our review; recommendation is keep for ridge.
