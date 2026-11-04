import sqlite3, json, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
ROOT = Path(__file__).resolve().parents[1]; TD = ROOT/"tableau/data"; FG = ROOT/"reports/figures"
NAVY, ORANGE, GREY = "#1f3a5f", "#e07a1f", "#9aa5b1"
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "font.size": 10})
rng = np.random.default_rng(1); con = sqlite3.connect(ROOT/"data/expedia.db")
sql = lambda f: pd.read_sql_query((ROOT/"sql"/f).read_text(), con)
df = pd.read_sql_query("SELECT * FROM v_imp", con)
R = {}

# ---------- 1. POSITION DECAY + cluster bootstrap CIs (resample whole searches) ----------
def boot(d, col, B=300):
    c = d.pivot_table(index="srch_id", columns="position", values=col, aggfunc="sum", fill_value=0)
    i = d.pivot_table(index="srch_id", columns="position", values=col, aggfunc="count", fill_value=0)
    W = rng.multinomial(len(c), np.ones(len(c))/len(c), size=B)
    rates = (W@c.values)/np.maximum(W@i.values, 1)
    lo, hi = np.percentile(rates, [2.5, 97.5], axis=0)
    return pd.DataFrame({"position": c.columns, "ctr_lo": lo, "ctr_hi": hi})
decay = sql("01_position_decay.sql")
ci = pd.concat([boot(df[df.random_bool == f], "click_bool").assign(random_bool=f) for f in (0, 1)])
decay = decay.merge(ci, on=["random_bool", "position"]); decay.to_csv(TD/"decay.csv", index=False)
def lift_top5(d):
    g = d.groupby("position").agg(imp=("click_bool", "size"), bk=("booking_bool", "sum"))
    return (g.bk[g.index <= 5].sum()/g.bk.sum()), (g.imp[g.index <= 5].sum()/g.imp.sum())
(sr, slr), (sn, sln) = lift_top5(df[df.random_bool == 1]), lift_top5(df[df.random_bool == 0])
d1, d0 = decay[decay.random_bool == 1].set_index("position"), decay[decay.random_bool == 0].set_index("position")
el = lambda t: np.polyfit(np.log(t.index), np.log(t.ctr_smooth), 1)[0]
R.update(top5_booking_share_random=sr, top5_slot_share=slr, top5_booking_share_normal=sn,
         position_share_of_top5_advantage=(sr/slr-1)/(sn/sln-1), ctr_elasticity_random=el(d1), ctr_elasticity_normal=el(d0),
         ctr_pos1_vs_pos10_random=d1.ctr_smooth[1]/d1.ctr_smooth[10], overall_ctr=df.click_bool.mean(), overall_cvr=df.booking_bool.mean())
fig, ax = plt.subplots(figsize=(8, 4.5))
for f, col, lab in ((0, NAVY, "Normally ranked (position + quality)"), (1, ORANGE, "Randomly ordered (position only)")):
    t = decay[decay.random_bool == f]
    ax.plot(t.position, t.ctr*100, color=col, lw=2, label=lab); ax.fill_between(t.position, t.ctr_lo*100, t.ctr_hi*100, color=col, alpha=.15)
ax.set(xlabel="Position on results page", ylabel="Click-through rate (%)")
ax.set_title(f"Even when order is random, rank 1 gets {R['ctr_pos1_vs_pos10_random']:.1f}x the clicks of rank 10", loc="left", fontweight="bold")
ax.legend(frameon=False); fig.tight_layout(); fig.savefig(FG/"01_position_decay.png", dpi=160); plt.close()

# ---------- 2. BOOKING WINDOW / LENGTH OF STAY ----------
sql("02_booking_window.sql").to_csv(TD/"window_cohorts.csv", index=False)
df["bw_bucket"] = pd.cut(df.srch_booking_window, [-1, 1, 7, 30, 90, 1000], labels=["0-1d", "2-7d", "8-30d", "31-90d", "90d+"])
rows = []
for b, d in df[df.random_bool == 1].groupby("bw_bucket", observed=True):
    g = d.groupby("position").click_bool.mean().loc[1:20]
    top, rest = d[d.position <= 5].click_bool.mean(), d[d.position > 15].click_bool.mean()
    rows.append(dict(bw_bucket=b, rank_elasticity=np.polyfit(np.log(g.index), np.log(g.clip(lower=1e-4)), 1)[0],
                     ctr_top5=top, ctr_16plus=rest, top5_premium=top/rest, n=len(d)))
win = pd.DataFrame(rows); win.to_csv(TD/"window_elasticity.csv", index=False); R["window"] = win.round(3).to_dict("records")

# ---------- 3. GBM: position-free appeal -> expected rank -> Quality-Adjusted Rank Gap ----------
df["price_rel"] = df.price_usd/df.groupby("srch_id").price_usd.transform("mean")
F = ["prop_starrating", "prop_review_score", "prop_location_score1", "price_usd", "price_rel", "promotion_flag", "srch_length_of_stay", "srch_booking_window"]
rd = df[df.random_bool == 1]; ids = rd.srch_id.unique(); te_ids = set(rng.choice(ids, len(ids)//5, replace=False))
tr, te = rd[~rd.srch_id.isin(te_ids)], rd[rd.srch_id.isin(te_ids)]
gbm = HistGradientBoostingClassifier(max_depth=4, learning_rate=.05, max_iter=250, random_state=0).fit(tr[F], tr.click_bool)
R["gbm_holdout_auc"] = roc_auc_score(te.click_bool, gbm.predict_proba(te[F])[:, 1])   # position is NOT a feature
df["appeal"] = gbm.predict_proba(df[F])[:, 1]
nm = df[df.random_bool == 0].copy()
nm["n_in"] = nm.groupby("srch_id").position.transform("size")
nm["exp_rank"] = nm.groupby("srch_id").appeal.rank(ascending=False, method="first")
nm["gap_pct"] = (nm.position-nm.exp_rank)/nm.n_in*100            # + = ranked worse than appeal deserves
P = nm.groupby("prop_id").agg(n_imps=("position", "size"), avg_position=("position", "mean"), avg_expected_rank=("exp_rank", "mean"),
    qarg=("gap_pct", "mean"), stars=("prop_starrating", "first"), review=("prop_review_score", "mean"), avg_price=("price_usd", "mean"),
    price_rel=("price_rel", "mean"), appeal=("appeal", "mean")).reset_index()
P = P[P.n_imps >= 30]
rc = rd.groupby("prop_id").click_bool.agg(["sum", "size"]); p0 = rd.click_bool.mean()
P = P.merge(((rc["sum"]+50*p0)/(rc["size"]+50)).rename("random_ctr_shrunk").reset_index(), on="prop_id", how="left")
R["validation_corr_gbm_vs_random_ctr"] = P[["appeal", "random_ctr_shrunk"]].corr().iloc[0, 1]
elig = P[(P.stars >= 4) & (P.review >= 4) & (P.price_rel <= 1)]
P["is_gem"] = P.prop_id.isin(elig[elig.qarg >= elig.qarg.quantile(.75)].prop_id)
P["appeal_multiplier"] = P.appeal/P.appeal.mean()
P.round(4).to_csv(TD/"hidden_gems.csv", index=False)
R.update(n_properties=len(P), n_gems=int(P.is_gem.sum()), gem_median_qarg=P[P.is_gem].qarg.median(),
         gem_random_ctr_lift=P[P.is_gem].random_ctr_shrunk.mean()/P.random_ctr_shrunk.mean())
fig, ax = plt.subplots(figsize=(8, 4.8)); o = P[~P.is_gem]; g = P[P.is_gem]
ax.scatter(o.appeal*100, o.qarg, s=8, color=GREY, alpha=.5, label="Other properties"); ax.scatter(g.appeal*100, g.qarg, s=22, color=ORANGE, label=f"Hidden gems ({len(g)})")
ax.axhline(0, color="k", lw=.6); ax.set(xlabel="Position-free appeal (predicted CTR, %)", ylabel="Quality-Adjusted Rank Gap (pct. points, + = buried)")
ax.set_title(f"{len(g)} strong properties sit ~{g.qarg.median():.0f} percentile points lower than their appeal deserves", loc="left", fontweight="bold", fontsize=10)
ax.legend(frameon=False); fig.tight_layout(); fig.savefig(FG/"02_hidden_gems.png", dpi=160); plt.close()

# ---------- 4. REVENUE LEFT ON THE TABLE ----------
cv = rd.groupby("position").booking_bool.mean().loc[1:40]; s, a = np.polyfit(np.log(cv.index), np.log(cv.clip(lower=1e-5)), 1)
r = lambda p: np.exp(a)*np.power(np.maximum(p, 1), s)                                    # random-search booking-rate curve
gr = nm[nm.prop_id.isin(P[P.is_gem].prop_id)].merge(P[["prop_id", "appeal_multiplier"]], on="prop_id")
gr["val"] = gr.price_usd*gr.srch_length_of_stay; base = (nm.booking_bool*nm.price_usd*nm.srch_length_of_stay).sum(); sim = []
for N in range(0, 16):
    dr = r(np.maximum(gr.position-N, 1))-r(gr.position)
    gross, net = gr.appeal_multiplier*dr, (gr.appeal_multiplier-1)*dr    # net: displaced average hotel loses dr (telescoping)
    sim.append(dict(positions_moved_up=N, bookings_gross=gross.sum(), bookings_net=net.sum(), revenue_gross=(gross*gr.val).sum(),
                    revenue_net=(net*gr.val).sum(), net_pct_of_baseline_revenue=(net*gr.val).sum()/base*100))
sim = pd.DataFrame(sim); sim.round(4).to_csv(TD/"revenue_sim.csv", index=False); R["revenue_sim_N5"] = sim.iloc[5].round(3).to_dict()
R["revenue_sim_N10"] = sim.iloc[10].round(3).to_dict(); R["baseline_revenue"] = base
fig, ax = plt.subplots(figsize=(8, 4.5)); ax.plot(sim.positions_moved_up, sim.revenue_gross/1e3, color=GREY, lw=2, ls="--", label="Naive (ignores who gets displaced)")
ax.plot(sim.positions_moved_up, sim.revenue_net/1e3, color=ORANGE, lw=2.5, label="Net of displaced hotels")
ax.set(xlabel="Positions gems are moved up", ylabel="Incremental booking revenue ($k)"); ax.legend(frameon=False)
ax.set_title("Promoting hidden gems: the real prize is smaller than the naive one", loc="left", fontweight="bold"); fig.tight_layout(); fig.savefig(FG/"03_revenue_impact.png", dpi=160); plt.close()

# ---------- export for R ----------
df[df.srch_id % 2 == 0][["srch_id", "click_bool", "booking_bool", "position", "random_bool", "prop_starrating", "prop_review_score", "prop_location_score1", "price_usd", "promotion_flag", "srch_length_of_stay", "srch_booking_window"]].head(400_000).to_csv(ROOT/"r/model_input.csv", index=False)
sql("03_hidden_gems_screen.sql").to_csv(TD/"gems_sql_screen.csv", index=False)
json.dump(R, open(ROOT/"reports/results.json", "w"), indent=1, default=float); print(json.dumps(R, indent=1, default=float))
