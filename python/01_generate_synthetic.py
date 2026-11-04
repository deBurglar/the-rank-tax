"""Synthetic stand-in with the SAME columns as Kaggle 'Personalize Expedia Hotel Searches' train.csv.
Ground truth is known (position effect gamma by booking window, persistent ranker bias), so the
analysis can be validated before running on the real file. NOT real Expedia data."""
import numpy as np, pandas as pd
from pathlib import Path
rng = np.random.default_rng(7)
NP, NS, K = 3000, 25000, 20
star = rng.choice([1,2,3,4,5], NP, p=[.03,.12,.38,.34,.13])
review = np.clip(np.round(rng.normal(2.6+0.3*star, .5)*2)/2, 1, 5)
loc = np.clip(rng.normal(2.0, .9, NP), 0, 6)
lp = 3.7+0.3*star+rng.normal(0, .35, NP)
price_z = (lp-(3.7+0.3*star))/.35
base_price = np.exp(lp)
obs = .30*(star-3)+.45*(review-3.5)+.25*(loc-2)-.35*price_z
hidden = rng.normal(0, .5, NP)
appeal = obs+hidden
rank_bias = rng.normal(0, .5, NP)          # persistent ranker error -> "hidden gems" exist
rows = []
for s in range(NS):
    p = rng.choice(NP, K, replace=False)
    rnd = int(rng.random() < .30)
    bw = int(min(rng.exponential(35), 365)); los = 1+rng.poisson(2.2)
    score = rng.random(K) if rnd else obs[p]+.3*hidden[p]+rank_bias[p]+rng.normal(0, .6, K)
    pos = np.empty(K, int); pos[np.argsort(-score)] = np.arange(1, K+1)
    gamma = .55 if bw <= 1 else .7 if bw <= 7 else .85 if bw <= 30 else .95
    promo = (rng.random(K) < .2).astype(int)
    price = base_price[p]*rng.lognormal(0, .1, K)
    lc = -1.2+appeal[p]-.06*min(los, 7)*price_z[p]-gamma*np.log(pos)+.2*promo
    click = (rng.random(K) < 1/(1+np.exp(-lc))).astype(int)
    lb = -1.0+.6*appeal[p]-.2*np.log(pos)
    book = click*(rng.random(K) < 1/(1+np.exp(-lb))).astype(int)
    rows.append(pd.DataFrame(dict(srch_id=s, prop_id=p, prop_starrating=star[p], prop_review_score=review[p],
        prop_location_score1=loc[p], price_usd=price.round(2), promotion_flag=promo, srch_length_of_stay=los,
        srch_booking_window=bw, random_bool=rnd, position=pos, click_bool=click, booking_bool=book)))
pd.concat(rows).to_csv(Path(__file__).resolve().parents[1]/"data/sample_expedia.csv", index=False)
print("rows written")
