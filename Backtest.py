import pandas as pd
import requests

from main import run_pipeline

CARTOLA_PONTUADOS_URL = "https://api.cartola.globo.com/atletas/pontuados/"


def fetch_actuals(round_num):
    """Return a DataFrame indexed by atleta_id with the realized pontuacao."""
    resp = requests.get(f"{CARTOLA_PONTUADOS_URL}{round_num}")
    data = resp.json()
    rows = []
    for atleta_id, info in data.get("atletas", {}).items():
        rows.append({
            "atleta_id": int(atleta_id),
            "actual_pontuacao": float(info.get("pontuacao", 0) or 0),
            "entrou_em_campo": bool(info.get("entrou_em_campo", False)),
        })
    if not rows:
        return pd.DataFrame(columns=["actual_pontuacao", "entrou_em_campo"]).set_index(
            pd.Index([], name="atleta_id")
        )
    return pd.DataFrame(rows).set_index("atleta_id")


def run_backtest(start_round, end_round, window=8):
    """Replay rounds [start_round, end_round] and return per-round joined results."""
    frames = []
    for r in range(start_round, end_round + 1):
        print(f"[backtest] predicting round {r} using window={window}")
        _, df_players = run_pipeline(predict_round=r, window=window, write_csv=False)
        actuals = fetch_actuals(r)
        joined = df_players.join(actuals, how="inner")
        joined["predict_round"] = r
        frames.append(joined)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames)


def compute_errors(df, group_col=None):
    played = df[df["entrou_em_campo"]].copy()
    if played.empty:
        return pd.DataFrame()
    played["err"] = played["expCartolaTotal"] - played["actual_pontuacao"]

    def _metrics(group):
        err = group["err"]
        n = len(group)
        rmse = (err ** 2).mean() ** 0.5
        mae = err.abs().mean()
        return pd.Series({"n": n, "rmse": rmse, "mae": mae})

    if group_col is None:
        return _metrics(played).to_frame().T
    return played.groupby(group_col).apply(_metrics).reset_index()


def run_and_report(start_round, end_round, window=8, out_prefix="backtest"):
    df = run_backtest(start_round, end_round, window=window)
    if df.empty:
        print("[backtest] empty result set — aborting report")
        return
    df.to_csv(f"{out_prefix}_detail.csv")

    def _tag(frame, slice_name, key_col):
        frame = frame.copy()
        frame["slice"] = slice_name
        if key_col is None:
            frame["group_value"] = "all"
        else:
            frame["group_value"] = frame[key_col].astype(str)
            frame = frame.drop(columns=[key_col])
        return frame

    summary = pd.concat(
        [_tag(compute_errors(df), "overall", None),
         _tag(compute_errors(df, "position"), "position", "position"),
         _tag(compute_errors(df, "is_home"), "is_home", "is_home"),
         _tag(compute_errors(df, "predict_round"), "round", "predict_round")],
        ignore_index=True,
    )
    summary = summary[["slice", "group_value", "n", "rmse", "mae"]]
    summary.to_csv(f"{out_prefix}_summary.csv", index=False)
    print(summary.to_string(index=False))
    return summary


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Replay Cartola pipeline across rounds")
    parser.add_argument("--start", type=int, required=True, help="First round to predict")
    parser.add_argument("--end", type=int, required=True, help="Last round to predict (inclusive)")
    parser.add_argument("--window", type=int, default=8, help="Look-back window (default 8)")
    parser.add_argument("--prefix", default="backtest", help="Output file prefix")
    args = parser.parse_args()

    run_and_report(args.start, args.end, window=args.window, out_prefix=args.prefix)
