#!/usr/bin/env python3
"""Raw phase-pick rates for onsite, offsite and dev.

    python run.py --start 2026-10-11 --end 2026-10-12

For each system: dump automatic picks with dump_picks (output/picks_<system>.xml, git-ignored, overwritten each run),
count P and S picks from the state and global scautopick pipelines, and write docs/data/<system>.json for the web
page (hourly counts per network, average picks/hour per inventory station). End time is exclusive.
--reuse skips dump_picks and parses the existing output/picks_<system>.xml (make sure it covers the window).
"""

import argparse
import sys
import time
from datetime import datetime

from scripts import config, picks, web


def timestamp(s):
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            datetime.strptime(s, fmt)
            return s
        except ValueError:
            pass
    raise argparse.ArgumentTypeError(f"invalid time {s!r}; use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--start", required=True, type=timestamp, help="YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS (UTC)")
    p.add_argument("--end", required=True, type=timestamp, help="YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS (UTC)")
    p.add_argument("--reuse", action="store_true", help="reuse existing output/picks_<system>.xml")
    p.add_argument("--systems", nargs="+", default=config.SYSTEMS, choices=config.SYSTEMS,
                   help="subset of systems (default: all)")
    a = p.parse_args()

    out = config.OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    for system in a.systems:
        t = time.time()
        xml = out / f"picks_{system}.xml"
        try:
            if not (a.reuse and xml.exists()):
                print(f"{system}: dump_picks", flush=True)
                picks.dump(system, a.start, a.end, xml)
            df = picks.parse(xml)
            st = picks.stations(system, a.start, a.end)
            d = web.write(system, a.start, a.end, df, st)
            print(f"{system}: {len(df)} picks in dump, used {d['n_picks']}, "
                  f"{len(d['stations'])} stations, {time.time() - t:.0f} s", flush=True)
        except RuntimeError as e:
            print(e)
            web.write(system, a.start, a.end, error=str(e).splitlines()[0])
    print(f"Web data in {config.DOCS_DIR / 'data'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
