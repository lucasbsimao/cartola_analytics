# CartolaFC Analytics — Indicators & Metrics Reference

This document is the single source of truth for every metric and indicator computed by this pipeline. It is intended to be read by both human contributors and AI agents operating on this codebase. Keep it up to date whenever `Metrics.py` or `Indicators.py` change.

---

## Pipeline Overview

```
Cartola API
  ├── /partidas/{round}       → match schedule (team IDs, home/away)
  └── /atletas/pontuados/{round} → player scouts per round

         ↓  fill_data_frame_with_round_games_info()  [Metrics.py]

Layer 1 — Raw Metrics (per team, accumulated over N rounds)
  └── calculate_games_info_metrics()  →  metrics (CSV)

         ↓  calculate_indicators_with_games_info()  [Indicators.py]

Layer 2 — Match Indicators (per fixture, predictive)
  └── indicators.csv
```

Default look-back window: **8 previous rounds** (configurable in `main.py`).

---

## Layer 1 — Raw Metrics (`Metrics.py`)

### Input: Cartola Scout Codes

Scouts are aggregated per team per round. Every column below is the **sum across all players in that team** for a given match.

| Code | Event | Cartola Points |
|------|-------|----------------|
| G    | Goal | +8.0 |
| A    | Assist | +5.0 |
| FT   | Shot on post | +3.0 |
| FD   | Shot on target (saved) | +1.2 |
| FF   | Shot off target | +0.8 |
| FS   | Foul suffered | +0.5 |
| PS   | Penalty won | +1.0 |
| DE   | Save (GK) | +1.3 |
| DP   | Penalty save (GK) | +7.0 |
| DS   | Tackle | +1.5 |
| SG   | Clean sheet bonus (GK/DEF/LAT) | +5.0 |
| GS   | Goal conceded (GK) | −1.0 |
| CA   | Yellow card | −1.0 |
| CV   | Red card | −3.0 |
| FC   | Foul committed | −0.3 |
| GC   | Own goal | −3.0 |
| I    | Offside | −0.1 |
| PP   | Penalty missed | −4.0 |
| PC   | Penalty committed | −1.0 |

---

### Computed Columns (one row per team, indexed by team ID)

All per-game columns are **normalised per match played** (home or away separately) inside `calculate_games_info_metrics()`.

#### Shot Volume

| Column | Formula | Rationale |
|--------|---------|-----------|
| `SHOTS OT PG H` | `(FD + FT + G) / MATCHES H` | Home on-target shots per game. FD (saved) + FT (post) + G (scored) = every shot that hit the frame. |
| `SHOTS OT PG A` | `(FD + FT + G) / MATCHES A` | Same, away games. |
| `SHOTS OT PG` | `(SHOTS OT PG H + SHOTS OT PG A) / 2` | Overall average on-target shots per game. |
| `TOTAL SHOTS H` | `SHOTS OT PG H + FF / MATCHES H` | Adds off-target shots; captures general offensive pressure at home. |
| `TOTAL SHOTS A` | `SHOTS OT PG A + FF / MATCHES A` | Same, away. |
| `TOTAL SHOTS` | `(TOTAL SHOTS H + TOTAL SHOTS A) / 2` | Overall shot volume average. |

#### Goals

| Column | Formula | Rationale |
|--------|---------|-----------|
| `GF H` | `G_home + GC_away` | Goals for, home games. Own goals by the opponent count as scored goals. |
| `GA H` | `G_away + GC_home` | Goals against, home games. Own goals by this team count as conceded. |
| `GF A` | `G_away + GC_home` | Goals for, away games. |
| `GA A` | `G_home + GC_away` | Goals against, away games. |
| `MGF H` | `GF H / MATCHES H` | Mean goals scored per home game. Core offensive strength proxy. |
| `MGA H` | `GA H / MATCHES H` | Mean goals conceded per home game. Core defensive vulnerability proxy. |
| `MGF A` | `GF A / MATCHES A` | Mean goals scored per away game. |
| `MGA A` | `GA A / MATCHES A` | Mean goals conceded per away game. |

#### Opponent Shot Volume (defensive exposure)

| Column | Formula | Rationale |
|--------|---------|-----------|
| `SHOTS OT AGA H` | `opponent (FD+FT+G) / MATCHES H` | On-target shots conceded per home game. Measures defensive solidity. |
| `SHOTS OT AGA A` | `opponent (FD+FT+G) / MATCHES A` | Same, away. |
| `SHOTS OT AGA TOTAL` | `(SHOTS OT AGA H + SHOTS OT AGA A) / 2` | Overall on-target shots conceded. |
| `TOTAL SHOTS AGA H` | `opponent total shots / MATCHES H` | Total shots conceded per home game. |
| `TOTAL SHOTS AGA A` | `opponent total shots / MATCHES A` | Same, away. |
| `TOTAL SHOTS AGA` | `(TOTAL SHOTS AGA H + TOTAL SHOTS AGA A) / 2` | Overall. |

#### Shot-to-Goal Efficiency Ratios

| Column | Formula | Rationale |
|--------|---------|-----------|
| `FIN P GOL F H` | `SHOTS OT PG H / MGF H` | On-target shots needed per goal scored at home. Lower = more clinical. |
| `FIN P GOL F A` | `SHOTS OT PG A / MGF A` | Same, away. |
| `FIN POR GOL FEITO` | `SHOTS OT PG / mean(MGF H, MGF A)` | Overall shots-per-goal for attack. |
| `FIN P GOL T H` | `SHOTS OT AGA H / MGA H` | On-target shots the opponent needs per goal conceded at home. Lower = weaker defence. |
| `FIN P GOL T A` | `SHOTS OT AGA A / MGA A` | Same, away. |
| `FIN POR GOL TOM` | `SHOTS OT AGA TOTAL / mean(MGA H, MGA A)` | Overall opponent shots-per-goal against this team's defence. |

---

## Layer 2 — Match Indicators (`Indicators.py`)

One row per fixture. Columns come in home (`H`) and away (`A`) pairs. All values are rounded to 2 decimal places and written to `indicators.csv`.

### Shot Interaction Indicators

| Column | Formula | Rationale |
|--------|---------|-----------|
| `shotsMultiOTH` | `SHOTS OT PG H(home_team) × SHOTS OT AGA A(away_team)` | Cross-multiplies home attack output with away defensive exposure. High value = home team likely to create many dangerous chances. |
| `shotsMultiOTA` | `SHOTS OT PG A(away_team) × SHOTS OT AGA H(home_team)` | Same for the away side. |
| `shotsMultiTotH` | `(TOTAL SHOTS H(home) × TOTAL SHOTS AGA A(away)) / 10` | Total shot pressure interaction, scaled by /10 to normalise magnitude. |
| `shotsMultiTotA` | `(TOTAL SHOTS A(away) × TOTAL SHOTS AGA H(home)) / 10` | Same for away. |

### Expected Goals (xG proxy)

| Column | Formula | Rationale |
|--------|---------|-----------|
| `goalsMultiH` | `(MGF H(home) + MGA A(away)) / 2` | Blends home team's scoring rate with away team's conceding rate. Simple xG estimate without Poisson. |
| `goalsMultiA` | `(MGF A(away) + MGA H(home)) / 2` | Same for the away team. |

### Conversion Rate Indicators

These invert the "shots-per-goal" ratios so that **higher = more efficient**.

| Column | Formula | Rationale |
|--------|---------|-----------|
| `onTargetConvRateH` | `(1/FIN P GOL F H(home) + 1/FIN P GOL T A(away)) / 2` | Combines home attack precision with away defensive leakiness, on-target shots only. |
| `onTargetConvRateA` | `(1/FIN P GOL F A(away) + 1/FIN P GOL T H(home)) / 2` | Same for away team. |
| `totalShotConvRateH` | `(1/FIN POR GOL FEITO(home) + 1/FIN POR GOL TOM(away)) / 2` | Same concept but using total shots (on/off target). Broader offensive pressure view. |
| `totalShotConvRateA` | `(1/FIN POR GOL FEITO(away) + 1/FIN POR GOL TOM(home)) / 2` | Same for away. |

### Goalkeeper Expected Saves

| Column | Formula | Rationale |
|--------|---------|-----------|
| `expectedSavesH` | `save_rate_H × SHOTS OT PG A(away)` where `save_rate_H = 1 − (MGA H / SHOTS OT AGA H)` | Projects how many saves the home goalkeeper is expected to make. Directly maps to `DE` scout points (+1.3 each) and `DP` (+7.0). |
| `expectedSavesA` | `save_rate_A × SHOTS OT PG H(home)` where `save_rate_A = 1 − (MGA A / SHOTS OT AGA A)` | Same for the away keeper. |

### Score Probability (Poisson-based)

| Column | Formula | Rationale |
|--------|---------|-----------|
| `scoreProbH` | `1 − exp(−MGF H(home))` | Probability home team scores at least one goal, using Poisson with λ = MGF H. |
| `scoreProbA` | `1 − exp(−MGF A(away))` | Same for away. |
| `cleanSheetProbH` | `1 − scoreProbA` | Probability home team keeps a clean sheet. Directly tied to `SG` scout (+5.0 for GK/DEF/LAT). |
| `cleanSheetProbA` | `1 − scoreProbH` | Same for away. |

---

## CartolaFC Score Relevance Summary

| Indicator | Primary Beneficiary Positions | Key Scouts Predicted |
|-----------|------------------------------|---------------------|
| `scoreProbH/A` | ATK, MEI | G (+8.0), A (+5.0) |
| `cleanSheetProbH/A` | GK, ZAG, LAT | SG (+5.0) |
| `expectedSavesH/A` | GK | DE (+1.3), DP (+7.0) |
| `onTargetConvRateH/A` | ATK | G, FT, FD |
| `shotsMultiOTH/A` | ATK, MEI | FT (+3.0), FD (+1.2), FF (+0.8) |
| `goalsMultiH/A` | ATK, MEI | G (+8.0), A (+5.0) |

---

## Tracked Source Files

The following files define all indicators and metrics. Any change to these files should trigger a review and update of this document.

- `Metrics.py` — Layer 1 aggregation and metric computation
- `Indicators.py` — Layer 2 indicator formulas and Poisson model
- `main.py` — Pipeline orchestration, look-back window, API calls
- `docs/CARTOLA_SCOUTS.md` — Scout point values reference
