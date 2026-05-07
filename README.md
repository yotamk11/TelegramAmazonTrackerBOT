# Amazon Price Tracker — Telegram Bot

A Telegram bot that monitors Amazon product prices, stores price history, notifies users when a tracked product hits their target price, and uses ML to predict upcoming price drops.

---

## Features

- Track any Amazon product by sending its URL to the bot
- Duplicate detection — re-sending a tracked URL offers to update the target price instead
- Automatic price checks every 30 minutes
- AI-powered deal analysis on each new product (Groq / LLaMA)
- Instant Telegram notification when a product hits its target price
- Full price history recorded per product
- Price history graph (lowest price per day) available on demand
- ML price-drop predictions using logistic regression (on demand)
- Delete a tracked product and its full history
- Handles multiple users concurrently via a thread pool
- All prices fetched in USD regardless of the user's region

---

## Usage

| Message      | Description                                                            |
|--------------|------------------------------------------------------------------------|
| `/start`     | Welcome message                                                        |
| `products`   | List all tracked products with inline buttons to view price graphs     |
| `delete`     | List tracked products with inline buttons to remove tracking           |
| `drops`      | Run ML prediction and show which of your products may drop ≥10% soon  |
| Amazon URL   | Fetch price + AI analysis; offer to start tracking                     |

---

## Architecture

### Files

| File            | Responsibility                                                              |
|-----------------|-----------------------------------------------------------------------------|
| `bot.py`        | Telegram handlers, startup logic, thread pool management                    |
| `scraper.py`    | Amazon price and title scraping via undetected Chrome                       |
| `ai_handler.py` | Groq API integration (LLaMA 3.1) for deal analysis                          |
| `database.py`   | SQLite schema, all read/write operations                                    |
| `clock.py`      | Periodic price check job                                                    |
| `graph.py`      | Matplotlib price history chart (daily lowest price)                         |
| `predictor.py`  | Logistic regression model — trains on price history, predicts ≥10% drops   |

### Database Schema

**tracked\_products**

| Column        | Type    | Description                              |
|---------------|---------|------------------------------------------|
| id            | INTEGER | Primary key                              |
| user\_id      | INTEGER | Telegram user ID                         |
| url           | TEXT    | Canonical amazon.com product URL         |
| last\_price   | REAL    | Most recently recorded price             |
| target\_price | REAL    | User-defined alert threshold             |
| title         | TEXT    | Product name scraped from Amazon         |

**price\_history**

| Column      | Type    | Description                              |
|-------------|---------|------------------------------------------|
| id          | INTEGER | Primary key                              |
| product\_id | INTEGER | Foreign key to tracked\_products         |
| price       | REAL    | Price recorded at this point in time     |
| timestamp   | TEXT    | ISO 8601 UTC timestamp                   |

### ML Price-Drop Prediction

`predictor.py` trains a logistic regression model on the accumulated price history every time the user sends `drops`. Features extracted per product:

| Feature             | Description                                                    |
|---------------------|----------------------------------------------------------------|
| `current_price`     | Latest observed price                                          |
| `avg_30`            | Mean price over the last 30 observations                       |
| `std_30`            | Standard deviation over the last 30 observations              |
| `price_ratio`       | `current / avg_30` — above 1.0 signals a candidate for a drop |
| `trend`             | Normalised linear slope of the last 7 prices                  |
| `position_in_range` | Where the current price sits in the 30-observation range       |
| `n_observations`    | Total number of price records for this product                 |

**Label**: did the price fall ≥10% within the next 10 price checks?

The model requires at least 10 labelled samples with both classes present to train. If there is not enough history yet it prints a clear message and skips sending predictions.

### Concurrency

- All blocking operations (Chrome scraping, Groq API, model training) run in a shared `ThreadPoolExecutor` (5 workers) via `asyncio.run_in_executor`, keeping the Telegram event loop responsive.
- Periodic price checks run concurrently across all tracked products, capped at 3 simultaneous Chrome instances via an `asyncio.Semaphore`.

### USD Pricing

Any Amazon regional URL (`.co.uk`, `.de`, etc.) is normalised to `amazon.com` by extracting the ASIN. On each scrape the bot:
1. Navigates to the Amazon homepage to establish a session
2. Sets `i18n-prefs=USD` and `lc-main=en_US` cookies
3. Interacts with the "Deliver to" location widget to set a US zip code (10001), forcing USD pricing server-side
4. Navigates to the product page and validates the `$` symbol before accepting the price

---

## Setup

### Requirements

```
pip install -r requirements.txt
```

`requirements.txt` includes: `python-telegram-bot`, `undetected-chromedriver`, `selenium`, `webdriver-manager`, `groq`, `python-dotenv`, `matplotlib`, `scikit-learn`, `numpy`

### Environment Variables

Create a `.env` file in the project root:

```
TELEGRAM_TOKEN=your_bot_token_from_botfather
GROQ_API_KEY=your_api_key_from_groq_cloud
```

### Run

```
python bot.py
```

The database is created automatically on first run.

---

## Disclaimer

This tool is for personal and educational use. Users are responsible for complying with Amazon's terms of service regarding automated data collection.
