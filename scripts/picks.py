"""Pick extraction (dump_picks) and parsing, plus the station inventory (SQL)."""

import subprocess
import xml.etree.ElementTree as ET

import pandas as pd
from sqlalchemy import create_engine, text

from . import config

STATIONS = """
SELECT Network.code AS net, Station.code AS sta, Station.latitude AS lat, Station.longitude AS lon,
       Station.start AS start, Station.end AS end
FROM Station, Network
WHERE Station._parent_oid = Network._oid
"""

COLS = ["time", "net", "sta", "loc", "cha", "phase", "author"]


def dump(system, start, end, outfile):
    """Dump automatic picks (no amplitudes) in [start, end) to SCML with dump_picks. Tries FQDN, then IP."""
    c, hosts = config.hosts(system)
    errors = []
    tw = f"{start.replace('T', ' ')}~{end.replace('T', ' ')}"
    for host in hosts:
        db = f"mysql://{c['user']}:{c['password']}@{host}:{c['port']}/{c['database']}"
        cmd = config.SEISCOMP + ["dump_picks", "-d", db, "-t", tw, "-a", "-n", "-o", str(outfile)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0 and outfile.exists():
            return outfile
        errors.append(f"{host}: dump_picks exit {r.returncode}: {r.stderr.replace(c['password'], '***')[-300:]}")
    raise RuntimeError(f"{system} dump_picks failed (check VPN).\n" + "\n".join(errors))


def parse(xmlfile):
    """DataFrame (time, net, sta, loc, cha, phase, author) of all picks in an SCML file, streamed."""
    rows = []
    for _, el in ET.iterparse(xmlfile, events=("end",)):
        if el.tag.rsplit("}", 1)[-1] != "pick":
            continue
        rec = dict.fromkeys(COLS)
        for ch in el.iter():
            tag = ch.tag.rsplit("}", 1)[-1]
            if tag == "time":
                v = ch.find("{*}value")
                rec["time"] = v.text if v is not None else None
            elif tag == "waveformID":
                rec["net"], rec["sta"] = ch.get("networkCode"), ch.get("stationCode")
                rec["loc"], rec["cha"] = ch.get("locationCode", ""), ch.get("channelCode")
            elif tag == "phaseHint":
                rec["phase"] = ch.text
            elif tag == "author":
                rec["author"] = ch.text
        rows.append(rec)
        el.clear()
    df = pd.DataFrame(rows, columns=COLS)
    df["time"] = pd.to_datetime(df.time, utc=True, format="ISO8601")
    df["loc"] = df["loc"].fillna("")
    return df


def stations(system, start, end):
    """One row per NET.STA with an epoch overlapping the window (latest epoch wins)."""
    c, hosts = config.hosts(system)
    errors = []
    for host in hosts:
        url = f"mysql+pymysql://{c['user']}:{c['password']}@{host}:{c['port']}/{c['database']}"
        try:
            with create_engine(url).connect() as conn:
                df = pd.read_sql(text(STATIONS), conn)
            break
        except Exception as e:  # noqa: BLE001
            errors.append(f"{host}: {str(e).replace(c['password'], '***')[:300]}")
    else:
        raise RuntimeError(f"{system} inventory query failed.\n" + "\n".join(errors))
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    df = df[(df.start < e) & (df.end.isna() | (df.end > s))]
    return df.sort_values("start").groupby(["net", "sta"], as_index=False).last()[["net", "sta", "lat", "lon"]]
