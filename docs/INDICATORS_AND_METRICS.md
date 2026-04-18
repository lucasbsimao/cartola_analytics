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

         ↓  fill_data_frame_with_round_players_info()  [PlayerMetrics.py]

Layer 3 — Player Indicators (per athlete, predictive for next round)
  ├── PlayerMetrics.calculate_player_rate_metrics() → players_metrics.csv
  └── PlayerIndicators.calculate_player_indicators() → players.csv
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

#### Scout Aggregates (per game)

Eight Cartola scouts are persisted at the team level with the same structure used for shots: team totals at home / away, and opponent totals conceded at home / away. All values are divided by the respective `MATCHES H`/`MATCHES A` inside `calculate_games_info_metrics()`, yielding per-game rates. They feed the clash-averaged `exp<X>_H/A` indicators in Layer 2 and the per-player share allocation in Layer 3.

For each scout `X ∈ {A, FT, FD, FF, FS, PS, DS, CA}`:

| Column | Formula | Rationale |
|--------|---------|-----------|
| `X H` | `Σ team X scored at home / MATCHES H` | Per-home-game production rate for scout X. |
| `X A` | `Σ team X scored away / MATCHES A` | Per-away-game production rate for scout X. |
| `X AGA H` | `Σ opponents' X against this team at home / MATCHES H` | Per-home-game rate opponents achieve against this team. Defensive exposure. |
| `X AGA A` | `Σ opponents' X against this team away / MATCHES A` | Per-away-game rate opponents achieve against this team. |

Scouts covered: `A` (assist), `FT` (post), `FD` (on target saved), `FF` (off target), `FS` (foul suffered), `PS` (penalty won), `DS` (tackle), `CA` (yellow card).

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

### Clash-Averaged Expected Scouts

For each scout `X ∈ {A, FT, FD, FF, FS, PS, DS, CA}`, the expected per-fixture team value follows the identical averaging pattern as `goalsMultiH/A`:

| Column | Formula | Rationale |
|--------|---------|-----------|
| `expX_H` | `(home "X H" + away "X AGA A") / 2` | Home team's home production rate for X, blended with away team's conceding-away rate for X. |
| `expX_A` | `(away "X A" + home "X AGA H") / 2` | Mirror for away team. |

Full set: `expA_H/A`, `expFT_H/A`, `expFD_H/A`, `expFF_H/A`, `expFS_H/A`, `expPS_H/A`, `expDS_H/A`, `expCA_H/A`.

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
| `expA_H/A` | ATK, MEI | A (+5.0) |
| `expFT_H/A` | ATK, MEI | FT (+3.0) |
| `expFD_H/A` | ATK, MEI | FD (+1.2) |
| `expFF_H/A` | ATK, MEI | FF (+0.8) |
| `expFS_H/A` | ALL | FS (+0.5) |
| `expPS_H/A` | ATK, MEI | PS (+1.0) |
| `expDS_H/A` | ALL (esp. ZAG, LAT, MEI) | DS (+1.5) |
| `expCA_H/A` | ALL (negative) | CA (−1.0) |
| `xCPA` | ALL | G, A, FT, FD, FF |
| `xCPD` | ZAG, LAT, MEI | DS, SG, FS, CA |
| `gkDefenseValue` | GK | SG, DE, GS |
| `expA` | ATK, MEI | A |
| `expDS` | ALL | DS |
| `expSG` | GK, ZAG, LAT | SG |
| `expDE` | GK | DE |
| `expGS` | GK | GS |
| `expCartolaTotal` | ALL | Net expected Cartola points |
| `costEfficiency` | ALL | Expected points per Cartola price unit |
| `floorCartola` | ALL | expCartolaTotal − points_std (safe/bench pick ordering) |
| `ceilingCartola` | ALL | expCartolaTotal + points_std (upside) |
| `captainValue` | ALL | (expCartolaTotal + 0.35 × points_std) × 1.5 (dobra ordering) |
| `consistency` | ALL | expCartolaTotal / (points_std + 1) |
| `valueVsReplacement` | ALL | expCartolaTotal − median(expCartolaTotal | position, eligible) |
| `formMultiplier` | ALL | last-3-played mean pontuação / overall mean (diagnostic) |

---

## Layer 3 — Player Indicators (`PlayerIndicators.py`)

One row per athlete (`players.csv`). The model allocates team-level clash indicators to players via share-of-team × availability. Rare scouts (`PP`, `PC`, `GC`, `DP`, `CV`, `I`, `FC`) are not projected; `xCPA` and `expCartolaTotal` capture the high-signal ones only.

### Allocation Model

```
side             = H if player's team plays at home in the predict round, else A
team_total_X     = X_{side}_rate × MATCHES_{side}                (G uses GF {side} directly)
X_share_player   = safe_divide(player.X_{side}, team_total_X)
effective_avail  = availability × sample_weight                  (sample_weight shrinks low-data players)
player_expX      = team_expX_{side} × X_share_player × effective_avail
expCartolaTotal  = Σ(exp<X> × points_X) × status_weight          (mercado gate)
```

Where `availability = played / games` across the window (from `entrou_em_campo` counts, not season `jogos_num`).

### Player Metrics (`PlayerMetrics.py`)

Per-athlete aggregation over the look-back window, written to `players_metrics.csv` (csv write lives in `main.py`).

- Identity (last seen from payloads, overridden by mercado snapshot where available): `apelido`, `clube_id`, `posicao_id`, `status_id`, `preco_num`.
- Summed scouts: `G, A, FT, FD, FF, FS, PS, DS, SG, DE, DP, GS, CA, CV, FC, GC, I, PP, PC` — plus side-split copies `<SCOUT>_H`, `<SCOUT>_A`.
- Counters: `games`, `played`, `games_H`, `games_A`, `played_H`, `played_A`.
- Per-game rates: `<SCOUT>_PG`, `<SCOUT>_PG_H`, `<SCOUT>_PG_A`.
- Availability: `availability = played / games`.
- Volatility (rounds with `played==1` only):
  - `points_PG`  = mean of per-round `pontuacao`
  - `points_std` = population stdev of per-round `pontuacao`
  - `points_PG_recent` = mean over the last `FORM_WINDOW=3` played rounds
  - `rounds_played` = number of rounds included
- `formMultiplier = points_PG_recent / points_PG` — recency diagnostic, not applied to `expCartolaTotal`.
- `shotQuality_share` = `(FD + FT) / (FD + FT + FF)`. Fraction of shots that land on frame. Separates efficient shooters from volume spammers. Range [0, 1]; players with zero shots get 0.0.
- Técnicos (`posicao_id == 6`), players with `scout is None`, and players whose club didn't play in the round are filtered.

### Mercado enrichment (`main.py`)

After aggregation, `main.py` fetches `https://api.cartola.globo.com/atletas/mercado` and overrides `status_id` / `preco_num` with the fresh values. This is the only place these fields come from reliably (the `/atletas/pontuados` endpoint does not expose them).

Cartola `status_id` values: `7 = Provável`, `2 = Dúvida`, `3 = Suspenso`, `5 = Contundido`, `6 = Nulo`.

### Identity & Fixture Context

| Column | Source |
|--------|--------|
| `atleta_id` | index |
| `apelido`, `position`, `status_id`, `preco`, `games`, `availability` | from `df_players_rates` |
| `club`, `opponent` | team abbreviations from the predict-round fixture |
| `is_home` | whether `club` plays at home in the predict round |

### Player Shares (side-aware)

Shares are now computed on the **same side** as the upcoming fixture. If the player's team plays at home next round, shares use the home split; if away, the away split.

| Column | Formula (side ∈ {H, A}, taken from fixture) |
|--------|----------------------------------------------|
| `G_share` | `safe_divide(player.G_{side}, GF {side})` |
| `A_share` ... `CA_share` | `safe_divide(player.X_{side}, X_{side}_rate × MATCHES_{side})` |

Covers `G, A, FT, FD, FF, FS, PS, DS, CA`. Home/away splits expose players who are dramatically more productive at home without needing manual partitioning.

### Sample-size shrinkage and status gating

- `sample_weight = min(1.0, games / MIN_GAMES)` with `MIN_GAMES = 3`. Low-data players (e.g. 1–2 games observed) have their shares down-weighted linearly.
- `effective_availability = availability × sample_weight` — all `exp<X>` values use this instead of raw `availability`.
- `status_weight` gate applied to **final** `expCartolaTotal` only (not to per-scout `exp<X>`, so those remain readable):
  - `7 → 1.0`, `2 → 0.5`, `3/5/6 → 0.0`, missing → `1.0`.
- `points_std` also scaled by `status_weight` so `floor`/`ceiling`/`captainValue` respect availability.

### Expected Events

All `exp<X>` use `effective_availability = availability × sample_weight` in place of raw `availability`.

| Column | Formula | Position gate |
|--------|---------|---------------|
| `expG`  | `goalsMulti{side} × G_share × effective_availability` | all |
| `expA`  | `expA_{side} × A_share × effective_availability` | all |
| `expFT` | `expFT_{side} × FT_share × effective_availability` | all |
| `expFD` | `expFD_{side} × FD_share × effective_availability` | all |
| `expFF` | `expFF_{side} × FF_share × effective_availability` | all |
| `expFS` | `expFS_{side} × FS_share × effective_availability` | all |
| `expPS` | `expPS_{side} × PS_share × effective_availability` | all |
| `expDS` | `expDS_{side} × DS_share × effective_availability` | all |
| `expCA` | `expCA_{side} × CA_share × effective_availability` | all |
| `expSG` | `cleanSheetProb{side} × effective_availability` | `position ∈ {1 GK, 2 LAT, 3 ZAG}`, else `0` |
| `expDE` | `expectedSaves{side} × effective_availability` | `position == 1` (GK), else `0` |
| `expGS` | `goalsMulti{opposite side} × effective_availability` | `position == 1` (GK), else `0` |

Only three scouts are truly position-gated (`SG`, `DE`, `GS`). All others are computed uniformly; shares naturally zero out irrelevant positions (a striker's `DS_share` is small, a defender's `G_share` is small).

### Headline / Derived Indicators

| Column | Formula | Rationale |
|--------|---------|-----------|
| `xCPA` | `(expG·8 + expFT·3 + expFD·1.2 + expFF·0.8) × quality_multiplier + expA·5` | Expected attacking Cartola points. Shot-derived terms scaled by quality_multiplier (clamped [0.7, 1.3]) — rewards efficient shooters over volume spammers. |
| `xCPD` | `expDS·1.5 + expSG·5 + expFS·0.5 − expCA·1` | Expected **defensive** Cartola points. Rank ZAG/LAT on actual defensive contribution. |
| `gkDefenseValue` | `expSG·5 + expDE·1.3 − expGS·1` (GK only, else 0) | GK-specific headline. Use this to compare goalkeepers instead of `expCartolaTotal`. |
| `cardLiability` | `expCA × 1` | Reported positive; subtracted inside `expCartolaTotal`. Useful for filtering yellow-card-prone picks. |
| `expCartolaTotal` | `(expG·8 + expA·5 + expFT·3 + expFD·1.2 + expFF·0.8 + expFS·0.5 + expPS·1 + expDS·1.5 + expSG·5 + expDE·1.3 − expGS·1 − expCA·1) × status_weight` | Net expected Cartola points for the next round, gated by mercado availability. |
| `floorCartola` | `expCartolaTotal − points_std` | Downside estimate (~P16). Use for safe/bench picks. |
| `ceilingCartola` | `expCartolaTotal + points_std` | Upside estimate (~P84). Use as captain-pick input. |
| `captainValue` | `(expCartolaTotal + 0.35 × points_std) × 1.5` | Expected captain points under the standard 1.5× dobra. Upside-skewed mean — 0.35σ of upside rather than full ceiling × 1.5, which over-rewarded high-variance picks. |
| `consistency` | `expCartolaTotal / (points_std + 1)` | Sharpe-like score. High = stable producer; low = boom-or-bust. |
| `valueVsReplacement` | `expCartolaTotal − median(expCartolaTotal \| position)` over eligible players | Positional value-above-replacement. Normalises the different scoring scales of GK vs ATK. |
| `formMultiplier` | passthrough from `PlayerMetrics` | Last-3-played mean / overall mean. Diagnostic only. |
| `costEfficiency` | `safe_divide(expCartolaTotal, preco)` | Expected points per Cartola price unit; primary pick-ordering metric under budget. |

All columns are rounded to 2 decimal places.

### Why no xG column

Real xG requires per-shot location and body-part data the Cartola API does not expose. The `goalsMulti{H/A} × G_share` path carries the honest goal signal, and `xCPA`'s `G·8` term supplies the Cartola-scaled equivalent.

### Why rare negative scouts are omitted

`CV` (red), `GC` (own goal), `PP` (penalty missed), `PC` (penalty committed), `I` (offside), `FC` (foul committed) are summed in `PlayerMetrics.PLAYER_SCOUTS` but not projected in `PlayerIndicators`. These events are infrequent and highly situational; projecting them from 8-round means introduces more noise than signal. Filter manually via `status_id` and domain knowledge. Same reasoning for `expDP` (penalty save): penalty occurrence is not reliably predictable from team rates at this sample size.

---

## Tracked Source Files

The following files define all indicators and metrics. Any change to these files should trigger a review and update of this document.

- `Metrics.py` — Layer 1 team aggregation and metric computation
- `Indicators.py` — Layer 2 fixture-level indicator formulas and Poisson model
- `PlayerMetrics.py` — Layer 3 per-player scout aggregation across the look-back window
- `PlayerIndicators.py` — Layer 3 per-player expected scouts, `expCartolaTotal`, `costEfficiency`
- `main.py` — Pipeline orchestration, look-back window, API calls
- `docs/CARTOLA_SCOUTS.md` — Scout point values reference
