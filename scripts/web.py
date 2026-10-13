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


def _channels(g):
    """Waveform-view streams for one station: most-picked location + 2-character band/instrument code,
    with the component letters seen in the picks, completed to three (Z12 if 1/2 were seen, else ZNE)."""
    g = g.assign(base=g["cha"].str[:2])
    loc, base = g.groupby(["loc", "base"]).size().idxmax()
    comps = sorted(set(g.loc[(g["loc"] == loc) & (g["base"] == base), "cha"].str[2:]))
    fill = "Z12" if {"1", "2"} & set(comps) else "ZNE"
    for c in fill:
        if len(comps) >= 3:
            break
        if c not in comps:
            comps.append(c)
    order = {c: i for i, c in enumerate("EN12Z")}
    return [f"{loc}.{base}{c}" for c in sorted(comps, key=lambda c: order.get(c, 9))]


def write(system, start, end, picks=None, stations=None, error=None):
    """picks: DataFrame from picks.parse; stations: DataFrame from picks.stations."""
    s, e = pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC")
    hours = (e - s) / pd.Timedelta(hours=1)
    d = {"system": system, "start": start, "end": end, "hours": hours, "phases": config.PHASES,
         "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    if error:
        d["error"] = error
        _write(system, d)
        return d

    pipes, phases = list(config.PIPELINES), config.PHASES
    author2pipe = {v: k for k, v in config.PIPELINES.items()}
    p = picks[(picks.time >= s) & (picks.time < e) & picks.phase.isin(phases)
              & picks.author.isin(author2pipe)].copy()
    p["pl"] = p["author"].map(author2pipe)      # pipeline name ("pipe" would clash with DataFrame.pipe)

    # hourly counts per network group + pipeline + phase
    n_bins = int(np.ceil(hours))
    p["bin"] = ((p["time"] - s) / pd.Timedelta(hours=1)).astype(int)
    hourly = {}
    for grp, nets in config.NETWORK_GROUPS.items():
        for k in pipes:
            sel = p[p["net"].isin(nets) & (p["pl"] == k)]
            hourly[f"{grp}|{k}"] = {ph: np.bincount(sel.loc[sel.phase == ph, "bin"], minlength=n_bins)[:n_bins].tolist()
                                    for ph in phases}
    d["hourly"] = {"t0": s.strftime("%Y-%m-%dT%H:%M:%SZ"), "series": hourly}

    # per-station average picks/hour by pipeline and phase: all inventory stations plus any picked station
    cols = [f"{k}_{ph}" for k in pipes for ph in phases]
    p["col"] = p["pl"] + "_" + p["phase"]
    cnt = p.groupby(["net", "sta", "col"]).size().unstack("col", fill_value=0).reindex(columns=cols, fill_value=0)
    st = stations.set_index(["net", "sta"]).join(cnt, how="outer").reset_index()
    st[cols] = st[cols].fillna(0)
    chans = {key: _channels(g) for key, g in p.groupby(["net", "sta"])}
    d["stations"] = [{"net": r["net"], "sta": r["sta"], "lat": _num(r["lat"], 4), "lon": _num(r["lon"], 4),
                      **{c: round(float(r[c]) / hours, 4) for c in cols},
                      "chans": chans.get((r["net"], r["sta"]), [])}
                     for r in st.to_dict("records")]
    d["n_picks"] = {c: int((p["col"] == c).sum()) for c in cols}
    _write(system, d)
    return d
