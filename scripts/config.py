"""Fixed settings."""

import json
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent
ROOT_DIR = PKG_DIR.parent

SYSTEMS = ["onsite", "offsite", "dev"]
PIPELINES = {"state": "scautopick_state:AEC", "global": "scautopick_global:AEC"}
PHASES = ["P", "S"]                           # picks counted, by phaseHint
NETWORK_GROUPS = {"AK": ["AK"], "AV": ["AV"], "AT": ["AT"], "II/IU": ["II", "IU"]}   # hourly plot lines

CONNECT_FILE = ROOT_DIR.parent / "connect.json"   # ~/play/connect.json, shared with system_comparisons
SEISCOMP = ["/home/sysop/seiscomp/bin/seiscomp", "exec"]
OUTPUT_DIR = ROOT_DIR / "output"
DOCS_DIR = ROOT_DIR / "docs"                  # GitHub Pages site


def load_connect(system):
    """Return the connect.json block for one system."""
    with open(CONNECT_FILE) as f:
        return json.load(f)[system]


def hosts(system):
    """(connect block, [hosts to try in order])."""
    c = load_connect(system)
    return c, [c["assess_fqdn"], c["assess_ip"]]
