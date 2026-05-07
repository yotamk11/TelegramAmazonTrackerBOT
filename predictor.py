import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from database import get_all_price_history_for_training, get_all_products_with_history

# Minimum price observations required before a product can appear in training/prediction
MIN_WINDOW = 7
# How many future price checks define the prediction horizon
LOOKAHEAD = 10
# A price drop is ≥10%
DROP_THRESHOLD = 0.10


def _features(prices: list[float]) -> list[float]:
    """
    Compute a 7-element feature vector from a list of prices (oldest first).

    Features:
      current_price        – latest observed price
      avg_30               – mean of last 30 prices (or all available)
      std_30               – std dev of last 30 prices
      price_ratio          – current / avg_30  (>1 = above average, candidate for drop)
      trend                – normalised linear slope of last 7 prices (negative = falling)
      position_in_range    – (current - min_30) / (max_30 - min_30)  (1 = at top)
      n_observations       – total number of price records for this product
    """
    current = prices[-1]
    recent_30 = prices[-30:]

    avg_30 = float(np.mean(recent_30))
    std_30 = float(np.std(recent_30)) if len(recent_30) > 1 else 0.0
    min_30 = float(np.min(recent_30))
    max_30 = float(np.max(recent_30))

    price_ratio = current / avg_30 if avg_30 > 0 else 1.0

    range_30 = max_30 - min_30
    position_in_range = (current - min_30) / range_30 if range_30 > 0 else 0.5

    recent_7 = prices[-7:]
    if len(recent_7) >= 2:
        x = np.arange(len(recent_7), dtype=float)
        slope = float(np.polyfit(x, recent_7, 1)[0])
        trend = slope / current if current > 0 else 0.0
    else:
        trend = 0.0

    return [current, avg_30, std_30, price_ratio, trend, position_in_range, len(prices)]


def _build_dataset() -> tuple[np.ndarray, np.ndarray]:
    """
    Slide a window over every product's price history to produce labelled samples.
    Label = 1 if price drops ≥10% within the next LOOKAHEAD observations, else 0.
    """
    all_history = get_all_price_history_for_training()
    X, y = [], []

    for prices in all_history.values():
        if len(prices) < MIN_WINDOW + LOOKAHEAD:
            continue
        for i in range(MIN_WINDOW - 1, len(prices) - LOOKAHEAD):
            feats = _features(prices[:i + 1])
            future = prices[i + 1: i + 1 + LOOKAHEAD]
            drop_target = prices[i] * (1 - DROP_THRESHOLD)
            label = 1 if any(p <= drop_target for p in future) else 0
            X.append(feats)
            y.append(label)

    return np.array(X, dtype=float), np.array(y, dtype=int)


def _train_model():
    """
    Train logistic regression on all available price history.
    Returns (model, scaler) or (None, None) when there is not enough data.
    """
    X, y = _build_dataset()
    n_samples = len(X)
    classes = np.unique(y).tolist()

    if n_samples < 10 or len(classes) < 2:
        print(f"[!] ML predictor: insufficient training data "
              f"(samples={n_samples}, classes={classes}) — skipping daily predictions")
        return None, None

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    model = LogisticRegression(C=1.0, max_iter=1000, random_state=42)
    model.fit(X_scaled, y)
    print(f"[+] ML predictor: trained on {n_samples} samples")
    return model, scaler


def predict_price_drops() -> dict[int, list[tuple]]:
    """
    Train the model then score every currently-tracked product.

    Returns
    -------
    {user_id: [(product_id, title, current_price, probability), ...]}
    Only products with predicted drop probability ≥ 0.5 are included.
    """
    model, scaler = _train_model()
    if model is None:
        return {}

    results: dict[int, list] = {}

    for user_id, product_id, title, prices in get_all_products_with_history():
        if len(prices) < MIN_WINDOW:
            continue
        feats = np.array([_features(prices)], dtype=float)
        prob = float(model.predict_proba(scaler.transform(feats))[0][1])
        if prob >= 0.5:
            results.setdefault(user_id, []).append(
                (product_id, title, prices[-1], prob)
            )

    return results
