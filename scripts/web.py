"""Web page data: docs/data/<system>.json (overwritten each run)."""

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import config


def _write(system, d):
    out = config.DOCS_DIR / "data"
    out.mkdir(parents=True, exist_ok=True)
    with open(out / f"{system}.json", "w") as f:
        json.dump(d, f, separators=(",", ":"))


def _num(v, nd):
    return None if pd.isna(v) else round(float(v), nd)


def write(system, start, end, picks=None, stations=None, error=None):
    """picks: DataFrame from picks.parse; stations: DataFrame from picks.stations."""
    s, e = pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC")
    hours = (e - s) / pd.Timedelta(hours=1)
    d = {"system": system, "start": start, "end": end, "hours": hours, "phase": config.PHASE,
         "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    if error:
        d["error"] = error
        _write(system, d)
        return d

    pipes = list(config.PIPELINES)
    author2pipe = {v: k for k, v in config.PIPELINES.items()}
    p = picks[(picks.time >= s) & (picks.time < e) & (picks.phase == config.PHASE)
              & picks.author.isin(author2pipe)].copy()
    p["pl"] = p["author"].map(author2pipe)      # pipeline name ("pipe" would clash with DataFrame.pipe)

    # hourly counts per network group + pipeline
    n_bins = int(np.ceil(hours))
    p["bin"] = ((p["time"] - s) / pd.Timedelta(hours=1)).astype(int)
    hourly = {}
    for grp, nets in config.NETWORK_GROUPS.items():
        for k in pipes:
            sel = p[p["net"].isin(nets) & (p["pl"] == k)]
            hourly[f"{grp}|{k}"] = np.bincount(sel["bin"], minlength=n_bins)[:n_bins].tolist()
    d["hourly"] = {"t0": s.strftime("%Y-%m-%dT%H:%M:%SZ"), "series": hourly}

    # per-station average picks/hour: all inventory stations plus any picked station not in inventory
    cnt = p.groupby(["net", "sta", "pl"]).size().unstack("pl", fill_value=0).reindex(columns=pipes, fill_value=0)
    st = stations.set_index(["net", "sta"]).join(cnt, how="outer").reset_index()
    st[pipes] = st[pipes].fillna(0)
    d["stations"] = [{"net": r["net"], "sta": r["sta"], "lat": _num(r["lat"], 4), "lon": _num(r["lon"], 4),
                      **{k: round(float(r[k]) / hours, 4) for k in pipes}}
                     for r in st.to_dict("records")]
    d["n_picks"] = {k: int((p["pl"] == k).sum()) for k in pipes}
    _write(system, d)
    return d
