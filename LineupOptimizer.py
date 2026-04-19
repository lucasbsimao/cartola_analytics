"""Lineup optimiser: pick the best 11 + captain from `players.csv`.

Solves a 0/1 ILP per allowed formation (maximise `Σ expCartolaTotal`)
subject to formation position counts and a cash budget. Captain is
selected post-solve as the starter with the highest `captainValue`,
keeping the ILP linear.

Extension points (see `optimize`): swap the objective to `floorCartola`
for risk-averse lineups, or to `captainValue` to bias toward
dobra-friendly squads.
"""

import pandas as pd
import pulp

# Cartola position IDs
GK, LAT, ZAG, MEI, ATK = 1, 2, 3, 4, 5

# Formations map: (formation_name, {position_id: count}). GK is always 1.
FORMATIONS = {
    "3-4-3": {GK: 1, ZAG: 3, LAT: 0, MEI: 4, ATK: 3},
    "3-5-2": {GK: 1, ZAG: 3, LAT: 0, MEI: 5, ATK: 2},
    "4-3-3": {GK: 1, ZAG: 2, LAT: 2, MEI: 3, ATK: 3},
    "4-4-2": {GK: 1, ZAG: 2, LAT: 2, MEI: 4, ATK: 2},
    "4-5-1": {GK: 1, ZAG: 2, LAT: 2, MEI: 5, ATK: 1},
    "5-3-2": {GK: 1, ZAG: 3, LAT: 2, MEI: 3, ATK: 2},
    "5-4-1": {GK: 1, ZAG: 3, LAT: 2, MEI: 4, ATK: 1},
}


def load_players(path="players.csv"):
    """Load `players.csv` and gate to eligible, finite-valued rows."""
    df = pd.read_csv(path).set_index("atleta_id")
    df = df[df["status_weight"] > 0]
    df = df[
        df["expCartolaTotal"].notna()
        & df["preco"].notna()
        & (df["preco"] > 0)
    ]
    return df


def solve_formation(df, formation, budget):
    """Solve the ILP for one formation. Returns the chosen 11 rows or None."""
    counts = FORMATIONS[formation]
    prob = pulp.LpProblem(f"lineup_{formation}", pulp.LpMaximize)
    x = {aid: pulp.LpVariable(f"x_{aid}", cat="Binary") for aid in df.index}

    prob += pulp.lpSum(
        float(df.loc[aid, "expCartolaTotal"]) * x[aid] for aid in df.index
    )

    # Position constraints (exact counts per formation).
    for pos_id, n in counts.items():
        if n == 0:
            # Forbid any player in a position the formation doesn't use.
            pool = df.index[df["position"] == pos_id]
            if len(pool) > 0:
                prob += pulp.lpSum(x[aid] for aid in pool) == 0, f"pos_{pos_id}_zero"
            continue
        pool = df.index[df["position"] == pos_id]
        prob += pulp.lpSum(x[aid] for aid in pool) == n, f"pos_{pos_id}"

    # Budget constraint.
    prob += (
        pulp.lpSum(float(df.loc[aid, "preco"]) * x[aid] for aid in df.index)
        <= budget,
        "budget",
    )

    status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[status] != "Optimal":
        return None

    picks = [aid for aid in df.index if x[aid].value() == 1]
    return df.loc[picks].copy()


def _best_across_formations(df, budget, formations):
    """Run every formation on `df` and return the single best result, or None."""
    best = None
    for f in formations:
        lineup = solve_formation(df, f, budget)
        if lineup is None:
            continue
        total = float(lineup["expCartolaTotal"].sum())
        if best is None or total > best["total_expected"]:
            captain_aid = lineup["captainValue"].idxmax()
            lineup = lineup.copy()
            lineup["is_captain"] = lineup.index == captain_aid
            # Order rows by pitch position: GK, LAT, ZAG, MEI, ATK.
            lineup = lineup.sort_values(
                ["position", "expCartolaTotal"], ascending=[True, False]
            )
            best = {
                "formation": f,
                "total_expected": total,
                "total_cost": float(lineup["preco"].sum()),
                "captain": lineup.loc[captain_aid, "apelido"],
                "lineup": lineup,
            }
    return best


def optimize(df, budget, formations=None, top_k=3):
    """Return up to `top_k` disjoint lineups.

    Tier 1 is the global best across formations. Tier 2 is the best
    lineup that excludes every player already picked in tier 1. Tier 3
    excludes the union of tiers 1 and 2. Each tier is free to pick its
    own best formation independently.
    """
    to_try = formations or list(FORMATIONS.keys())
    results = []
    used = set()
    pool = df
    for _ in range(top_k):
        if used:
            pool = df.drop(index=[aid for aid in used if aid in df.index])
        best = _best_across_formations(pool, budget, to_try)
        if best is None:
            break
        results.append(best)
        used.update(best["lineup"].index.tolist())
    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Optimise a Cartola lineup from players.csv"
    )
    parser.add_argument("--budget", type=float, required=True, help="Cash budget (C$)")
    parser.add_argument(
        "--formations",
        default=None,
        help="Comma-separated formations (default: all). Example: 4-3-3,4-4-2",
    )
    parser.add_argument("--input", default="players.csv")
    parser.add_argument("--top", type=int, default=3)
    parser.add_argument("--output", default="lineup.csv")
    args = parser.parse_args()

    df = load_players(args.input)
    formations = args.formations.split(",") if args.formations else None
    results = optimize(df, args.budget, formations=formations, top_k=args.top)

    if not results:
        print("No feasible lineup for the provided budget")
        raise SystemExit(1)

    best = results[0]
    best["lineup"].to_csv(args.output)
    print(f"Best formation: {best['formation']}")
    print(f"Expected total: {best['total_expected']:.2f}")
    print(f"Total cost:     {best['total_cost']:.2f}")
    print(f"Captain:        {best['captain']}")
    print(
        best["lineup"][
            ["apelido", "position", "club", "preco", "expCartolaTotal", "is_captain"]
        ]
    )

    for i, r in enumerate(results[1:], start=2):
        label = {2: "Second", 3: "Third"}.get(i, f"#{i}")
        print(f"\n{label} team (no overlap with previous): {r['formation']}")
        print(f"Expected total: {r['total_expected']:.2f}")
        print(f"Total cost:     {r['total_cost']:.2f}")
        print(f"Captain:        {r['captain']}")
        print(
            r["lineup"][
                ["apelido", "position", "club", "preco", "expCartolaTotal", "is_captain"]
            ]
        )
