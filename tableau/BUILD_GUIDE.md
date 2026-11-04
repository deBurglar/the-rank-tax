# Tableau dashboard (3 views) — 30–45 min build
Connect to the CSVs in `tableau/data/` (Text file connector). No joins needed.

## View 1 — "Rank 1 earns 3x the clicks of rank 10, even when order is random"
Source: `decay.csv`. Columns `position`; Rows `ctr`; Colour `random_bool` (alias 0=Normal, 1=Random).
Add `ctr_lo` / `ctr_hi` as a band (Dual-axis area or Analytics > Distribution band). Navy `#1f3a5f` / orange `#e07a1f`.
Tooltip: `ctr_index_vs_pos1`. Add a second sheet from `window_elasticity.csv`: bar of `top5_premium` by `bw_bucket`.

## View 2 — Hidden-gem explorer
Source: `hidden_gems.csv`. Scatter: X `appeal`, Y `qarg`, colour `is_gem` (orange = gem, grey = rest), size `n_imps`.
Filters: `stars`, `review`, `avg_price` slider, `is_gem`. Table sheet on the right: `prop_id, stars, review, avg_price, avg_position, avg_expected_rank, qarg`. Use Dashboard Action "Filter" scatter -> table.

## View 3 — Revenue-impact simulator
Source: `revenue_sim.csv`. Create a Parameter `Positions moved up` (int 0–15). Calculated field:
`Selected net revenue = IF [positions_moved_up] = [Positions moved up] THEN [revenue_net] END`
Line: `revenue_gross` (dashed grey, "naive") vs `revenue_net` (orange). KPI tiles: `Selected net revenue`, and
`[net_pct_of_baseline_revenue]` filtered to the parameter.

## Design rules (put these in your README too)
Titles state the finding; one accent colour (orange = the thing to look at); grey for context; no 3D, no dual-axis tricks, no legends when direct labels work; every axis labelled with units.
