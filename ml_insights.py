"""
ml_insights.py
==============
Gate 4 "Advanced Insights" — forecasting + clustering.

Design choice: scikit-learn (LinearRegression + KMeans) instead of
Prophet/statsmodels' ARIMA. Reasoning, for the record (and for the README):

  1. Prophet needs a C++ toolchain (cmdstanpy) to install — a real risk to
     hit late, on a Windows laptop, a few hours before a deadline.
  2. ARIMA can fail to converge (or throw convergence warnings) on short,
     noisy per-mandi-per-crop series — this dataset has many series with
     under 20 points. A model that can silently misbehave live in front of
     judges is worse than a simpler one that's guaranteed stable.
  3. scikit-learn is already a dependency (used for clustering either way),
     so this adds zero new install risk.

Both functions degrade gracefully on sparse data instead of crashing or
returning nonsense — consistent with agent.py's philosophy of never
returning an empty/broken result silently.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

MIN_POINTS_FOR_TREND = 10  # below this, trend+seasonality isn't reliable


def forecast_series(daily_df, value_col="value", horizon_days=7):
    """Forecast the next `horizon_days` for a daily time series.

    daily_df: DataFrame with columns ['date', value_col], one row per day
              (gaps are OK — missing days are just absent rows).
    Returns: (history_df, forecast_df, note) where forecast_df has
             ['date', value_col] for the forecast horizon, and `note`
             explains the method used / any caveat (e.g. sparse data).
    """
    daily_df = daily_df.dropna(subset=[value_col]).sort_values("date").reset_index(drop=True)
    n = len(daily_df)

    if n == 0:
        return daily_df, pd.DataFrame(columns=["date", value_col]), "No data available for this selection."

    last_date = daily_df["date"].max()
    future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=horizon_days)

    if n < MIN_POINTS_FOR_TREND:
        # Too little history for a trend line to mean anything — naive
        # forecast (repeat the recent average) beats a model fit on ~5 points.
        naive_value = daily_df[value_col].tail(min(n, 5)).mean()
        forecast_df = pd.DataFrame({"date": future_dates, value_col: naive_value})
        note = (f"Only {n} data point(s) available for this filter — showing a "
                f"flat average instead of a trend line (too little history to "
                f"fit one reliably).")
        return daily_df, forecast_df, note

    # Day-index as the regressor; day-of-week as a simple seasonal adjustment.
    daily_df["_t"] = (daily_df["date"] - daily_df["date"].min()).dt.days
    daily_df["_dow"] = daily_df["date"].dt.dayofweek

    X = daily_df[["_t"]].values
    y = daily_df[value_col].values
    model = LinearRegression().fit(X, y)

    daily_df["_trend"] = model.predict(X)
    daily_df["_resid"] = daily_df[value_col] - daily_df["_trend"]
    dow_effect = daily_df.groupby("_dow")["_resid"].mean()

    future_t = (future_dates - daily_df["date"].min()).days.values.reshape(-1, 1)
    future_trend = model.predict(future_t)
    future_dow = future_dates.dayofweek.map(lambda d: dow_effect.get(d, 0.0)).values
    future_values = future_trend + future_dow
    future_values = np.clip(future_values, a_min=0, a_max=None)  # arrivals/price can't be negative

    forecast_df = pd.DataFrame({"date": future_dates, value_col: future_values})
    slope_per_week = model.coef_[0] * 7
    direction = "rising" if slope_per_week > 0 else "falling"
    note = (f"Linear trend + day-of-week seasonality, fit on {n} days of history "
            f"({direction} ~{abs(slope_per_week):.1f} units/week).")
    return daily_df, forecast_df, note


def cluster_mandis(arrivals, prices, n_clusters=3):
    """Group mandis by price/volume behaviour using KMeans.

    Returns a DataFrame (one row per mandi_id) with the raw features, a
    numeric `cluster` label, and a human-readable `cluster_label` — plus
    a `note` string that's None on success or explains why clustering was
    skipped (e.g. too few mandis with enough data).
    """
    arr_daily = arrivals.groupby(["mandi_id", "date"], as_index=False)["arrival_qty_qtl"].sum()

    feat = arr_daily.groupby("mandi_id").agg(
        avg_arrival=("arrival_qty_qtl", "mean"),
        arrival_volatility=("arrival_qty_qtl", "std"),
    ).reset_index()

    price_feat = prices.groupby("mandi_id").agg(
        avg_price=("modal_price", "mean"),
        price_volatility=("modal_price", "std"),
        crash_rate=("below_msp", "mean"),
    ).reset_index()

    feat = feat.merge(price_feat, on="mandi_id", how="inner")
    feat = feat.dropna(subset=["avg_arrival", "avg_price"])
    feat["arrival_volatility"] = feat["arrival_volatility"].fillna(0)
    feat["price_volatility"] = feat["price_volatility"].fillna(0)
    feat["crash_rate"] = feat["crash_rate"].fillna(0) * 100

    if len(feat) < n_clusters + 1:
        return None, f"Only {len(feat)} mandis have enough data to cluster — need at least {n_clusters + 1}."

    feature_cols = ["avg_arrival", "arrival_volatility", "avg_price", "price_volatility"]
    X = StandardScaler().fit_transform(feat[feature_cols])

    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    feat["cluster"] = km.fit_predict(X)

    # Build a readable label per cluster from its centroid, rather than a
    # bare "Cluster 0/1/2" — volume tercile + stability, which is exactly
    # the kind of "hidden trend" this check is meant to surface.
    volume_rank = feat.groupby("cluster")["avg_arrival"].mean().rank()
    volatility_rank = feat.groupby("cluster")["price_volatility"].mean().rank()
    n = feat["cluster"].nunique()

    def volume_word(rank):
        if rank <= n / 3:
            return "Low-Volume"
        if rank <= 2 * n / 3:
            return "Mid-Volume"
        return "High-Volume"

    def stability_word(rank):
        return "Volatile" if rank > n / 2 else "Stable"

    label_map = {
        c: f"{volume_word(volume_rank[c])} \u00b7 {stability_word(volatility_rank[c])}"
        for c in feat["cluster"].unique()
    }
    feat["cluster_label"] = feat["cluster"].map(label_map)

    return feat, None
