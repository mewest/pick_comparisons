# pick_comparisons

Raw automatic phase-pick rates from the AEC SeisComP systems (onsite, offsite, dev).

Site: https://mewest.github.io/pick_comparisons/

## Run

    python run.py --start 2026-10-11 --end 2026-10-12

For each system, `dump_picks` extracts automatic picks for the window (end exclusive) into
`output/<start>_<end>/picks_<system>.xml` (git-ignored). P picks from the two scautopick pipelines are counted:

- state = `scautopick_state:AEC` (high-frequency bandpass)
- global = `scautopick_global:AEC` (lower bandpass)

Results go to `docs/data/<system>.json`, overwritten each run. `--reuse` skips `dump_picks` when the XML for the
window already exists. Database connections come from `~/play/connect.json` (not in the repo).

## Page (docs/, GitHub Pages)

- onsite / offsite / dev toggle
- hourly P picks for AK, AV, AT and II/IU (state solid, global dashed)
- station map coloured by average picks/hour (log scale 0.01–1000), state/global switch; all inventory stations
- sortable station table, cells coloured like the map

Publish: commit and push `docs/`; Pages serves `main` /docs.

Requirements: SeisComP (`dump_picks`), Python with pandas, numpy, SQLAlchemy, PyMySQL.
