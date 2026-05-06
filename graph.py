import io
from collections import defaultdict
from datetime import datetime, timedelta

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def _parse_ts(ts):
    return datetime.fromisoformat(ts.replace(' ', 'T'))


def build_price_graph(title, history, target_price):
    if not history:
        return None

    # Parse timestamps
    pairs = []
    for price, ts in history:
        try:
            pairs.append((price, _parse_ts(ts)))
        except (ValueError, AttributeError):
            continue

    if not pairs:
        return None

    # Aggregate to lowest price per day
    daily = defaultdict(list)
    for price, dt in pairs:
        daily[dt.date()].append(price)

    sorted_days = sorted(daily)
    dates  = [datetime(d.year, d.month, d.day) for d in sorted_days]
    prices = [min(daily[d]) for d in sorted_days]

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.plot(dates, prices, 'b-o', linewidth=2, markersize=5, label='Price')
    ax.axhline(y=target_price, color='r', linestyle='--', linewidth=1.5,
               label=f'Target: ${target_price:.2f}')
    ax.fill_between(dates, prices, target_price,
                    where=[p <= target_price for p in prices],
                    alpha=0.2, color='green', label='Below target')

    # Pad x-axis by 1 day on each side so edge points aren't clipped
    ax.set_xlim(min(dates) - timedelta(days=1), max(dates) + timedelta(days=1))

    # Ensure y-axis has visible range even when price is flat
    all_y = prices + [target_price]
    y_range = max(all_y) - min(all_y)
    y_pad = max(y_range * 0.15, 0.5)
    ax.set_ylim(min(all_y) - y_pad, max(all_y) + y_pad)

    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha='right')

    display_title = (title[:60] + '…') if len(title) > 60 else title
    ax.set_title(display_title, fontsize=13, fontweight='bold')
    ax.set_ylabel('Price (USD $)')
    ax.set_xlabel('Date (UTC)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=120)
    plt.close(fig)
    buf.seek(0)
    return buf
