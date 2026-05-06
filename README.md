# Amazon Price Tracker — Telegram Bot

A Telegram bot that monitors Amazon product prices, stores price history, and notifies users when a tracked product drops to their target price.

---

## Features

- Track any Amazon product by sending its URL to the bot
- Automatic price checks every 30 minutes
- AI-powered deal analysis on each new product (Groq / LLaMA)
- Instant Telegram notification when a product hits its target price, including the product name
- Full price history recorded per product
- Price history graph (lowest price per day) available on demand
- Delete a tracked product and its full history at any time
- Handles multiple users concurrently via a thread pool
- All prices fetched in USD regardless of the user's region

---

## Bot Commands

| Command      | Description                                                     |
|--------------|-----------------------------------------------------------------|
| `/start`     | Welcome message                                                 |
| `/products`  | List all tracked products with inline buttons to view graphs    |
| `/delete`    | List tracked products with inline buttons to remove tracking    |

Sending an Amazon product URL directly starts the tracking flow.

---

## Architecture

### Files

| File              | Responsibility                                                         |
|-------------------|------------------------------------------------------------------------|
| `bot.py`          | Telegram handlers, startup logic, thread pool management               |
| `scraper.py`      | Amazon price and title scraping via undetected Chrome; lightweight title fetch via HTTP |
| `ai_handler.py`   | Groq API integration (LLaMA 3.1) for deal analysis                    |
| `database.py`     | SQLite schema, all read/write operations                               |
| `clock.py`        | Periodic price check job; concurrent scraping with semaphore           |
| `graph.py`        | Matplotlib price history chart (daily lowest price)                    |

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

### Concurrency

- All blocking operations (Chrome scraping, Groq API) run in a shared `ThreadPoolExecutor` (5 workers) via `asyncio.run_in_executor`, keeping the Telegram event loop responsive.
- Periodic price checks run concurrently across all tracked products, capped at 3 simultaneous Chrome instances via an `asyncio.Semaphore`.

### USD Pricing

Any Amazon regional URL (`.co.uk`, `.de`, etc.) is normalised to `amazon.com` by extracting the ASIN. On each scrape the bot:
1. Navigates to the Amazon homepage to establish a session
2. Sets `i18n-prefs=USD` and `lc-main=en_US` cookies
3. Interacts with the "Deliver to" location widget to set a US zip code (10001), forcing USD pricing server-side
4. Navigates to the product page and validates the `$` symbol before accepting the price

### Title Backfill

On every startup, the bot fetches missing product titles via a lightweight HTTP request (no Chrome). If the product page returns 404, the title is derived from the URL slug.

---

## Setup

### Requirements

```
pip install -r requirements.txt
```

`requirements.txt` includes: `python-telegram-bot`, `undetected-chromedriver`, `selenium`, `webdriver-manager`, `groq`, `python-dotenv`, `matplotlib`, `cloudscraper`, `lxml`

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
