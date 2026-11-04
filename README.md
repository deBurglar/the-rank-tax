# The Rank Tax: What Is Position #1 Actually Worth on a Travel Site?

> **Headline:** When hotels are shown in *random* order, the top 5 slots (25% of the page) still capture **54% of bookings**. Pure position  explains roughly **60% of the top-5 advantage** Expedia sees in normally ranked searches. Moving 68 "hidden gem" properties up 10 slots is worth about **+2.7% net booking revenue** — about half of what a naive estimate claims.

> ⚠️ **Data note.** Figures above come from the included *synthetic* dataset (same schema as Kaggle's *Personalize Expedia Hotel Searches*, with known ground truth so the method can be validated). **Re-run on the real file for real numbers:** `./run_all.sh /path/to/train.csv`. Nothing else changes.
>
> ## Dashboard

**Tableau dashboard:** [View The Rank Tax — Executive Dashboard](PASTE_YOUR_TABLEAU_PUBLIC_LINK_HERE)

The dashboard explores:
- Click-through rate decay by search position
- Booking lead time and position sensitivity
- Hidden-gem hotel candidates

## Reproducing the analysis

### Requirements
- Python 3
- SQLite
- R and `ggplot2` for the optional R analysis
- Bash to run `run_all.sh`

### Run with synthetic data

From the project root, generate the synthetic dataset, build the database, and run the analysis:

```bash
python python/01_generate_synthetic.py
python python/02_load_db.py
python python/03_analysis.py
python run_sql.py
```

The scripts generate local data and analysis outputs. Large generated files and the local database are excluded from version control.

**Important:** All reported findings in this repository are based on synthetic Expedia-style data. The revenue results are simulation outputs, not measured Expedia business outcomes.

### Project structure

- `python/` — data generation, database loading, and analysis
- `sql/` — position-decay, booking-window, and hidden-gem queries
- `r/` — logistic regression analysis
- `tableau/` — dashboard build guide and supporting CSV files
- `reports/` — executive summary, metrics, and charts
- `outputs/sql/` — exported SQL analysis results

## Why this question
The ICDM-2013 Expedia dataset has a `random_bool` flag: searches where hotels were shown in random order. That is a built-in randomised experiment. In random searches position is independent of quality, so the click/booking gap between slots is the **causal effect of position** (the "rank tax"). Normal searches mix position and quality; comparing the two separates them.

## Results (synthetic data, 500k impressions)
| Question | Finding |
|---|---|
| Position decay | CTR at rank 1 is 3.1x rank 10 under random order; log-log elasticity −0.61 (random) vs −1.10 (normal) |
| Rank tax | Top-5 captures 54% of bookings when random, 72% when ranked. ~61% of the ranked advantage is position alone |
| Booking window | Rank sensitivity grows with lead time: top-5 click premium 2.2x for 0–1 day bookers vs 5.6x for 90+ days. Last-minute bookers ignore rank more |
| Hidden gems | 68 properties (4★+, review ≥4, below-average price) are ~26 percentile points lower than their position-free appeal deserves; their random-order CTR is 1.4x the average |
| Revenue | Moving gems up 5 / 10 slots: +1.4% / +2.7% net revenue (naive: ~3x larger, because it ignores displaced hotels) |
| Model | GBM trained on random searches only, position excluded: holdout AUC 0.68; its appeal score correlates 0.74 with each property's raw random-search CTR (independent validation) |

Figures: `reports/figures/`.

## Method (and why it's defensible)
1. **SQL (`/sql`, SQLite, window functions + CTEs):** cleaning view, position-decay table with smoothing/LAG/FIRST_VALUE, lead-time × stay × price cohorts, SQL-only gem screen with NTILE deciles.
2. **Python (`/python`):** cluster bootstrap CIs (resampling whole searches, not rows, to respect within-search correlation); a gradient-boosted model trained **only on random searches** so "appeal" is position-free, then applied to normal searches to get each hotel's *expected rank*. **Quality-Adjusted Rank Gap** = actual − expected position, as a percentile of the results list, averaged per property.
3. **R (`/r`):** logistic regression with position × random interaction, and position × lead-time/stay on random searches; odds ratios with Wald CIs; ggplot2 chart.
4. **Tableau (`/tableau`):** 3 views, CSVs pre-built, build steps in `BUILD_GUIDE.md`.
5. **Revenue simulator:** a power-law booking curve fitted on random searches; promoting a gem by N slots pushes N average hotels down one slot each, which telescopes to `net = (appeal_multiplier − 1) × curve change`. A hotel only creates value if it's better than the one it displaces.

## Limitations (read before quoting numbers)
- 2013 data, one marketplace; mobile, today's ranking models, and review ecosystems differ. With modern data I'd use ongoing randomisation or interleaving experiments on a small traffic slice.
- `random_bool` searches may differ from normal ones (users who saw junk may behave differently). The log-position functional form is an assumption.
- Appeal comes from observed features; unobserved quality is not captured. Booking-level effects are noisier than click-level ones.
- Net revenue ignores cannibalisation across searches, price changes, and long-run satisfaction.
- Synthetic numbers show the method works, not what Expedia's true values are.

## Repo
```
sql/      01_position_decay · 02_booking_window · 03_hidden_gems_screen
python/   01_generate_synthetic · 02_load_db · 03_analysis
r/        04_position_model.R
tableau/  data/*.csv · BUILD_GUIDE.md
reports/  figures · results.json · executive_summary.md
run_all.sh
```

## Recommendation (memo to PM)
1. Run a 1–2% traffic interleaving test promoting QARG-flagged properties by 3–5 slots; success metric is net bookings per search, not CTR.
2. Add QARG as a ranking-audit metric; properties with persistent gaps indicate feature gaps in the ranker.
3. Don't spend position-promotion budget on last-minute searches; they respond least to rank.
