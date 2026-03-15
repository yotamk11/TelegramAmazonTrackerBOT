# Amazon Price Tracker Project

## Overview
This system is a specialized tool for monitoring Amazon product prices via Telegram. It utilizes high-precision web scraping, SQLite database management, and AI-driven analysis to notify users of price drops.

---

## Technical Features

### URL Processing
The system validates and cleans Amazon URLs to ensure they are compatible with the tracker. It forces English language and USD currency settings to maintain data consistency across different regions.

### Scraper Engine
Built with `undetected_chromedriver`, the scraper navigates Amazon's mobile interface to bypass automated detection. It extracts precise pricing information, including decimal values, using CSS selectors and regular expressions.

### AI Integration
The bot integrates with the Groq API using the `llama-3.1-8b-instant` model. It analyzes product details and provides a three-line summary:
1. Product Name
2. Price Quality
3. Deal Recommendation

---

## System Architecture

### Database Management
The system uses an SQLite database (`tracker.db`) with the following schema:
- **User ID**: Unique Telegram identifier.
- **URL**: The processed Amazon product link.
- **Last Price**: The most recently recorded price.
- **Target Price**: The user-defined threshold for automated alerts.

### Periodic Monitoring
A background job queue runs every 30 minutes (1800 seconds) to check all tracked products. If the current price is less than or equal to the target price, the user receives an immediate notification and the product is removed from the tracking list to prevent duplicate alerts.

---

## Installation and Setup

1. **Requirements**
   Install the necessary Python packages:
   `pip install python-telegram-bot undetected-chromedriver selenium groq python-dotenv`

2. **Environment Configuration**
   Create a `.env` file in the root directory with the following keys:
   - `TELEGRAM_TOKEN`: Your bot token from BotFather.
   - `GROQ_API_KEY`: Your API key from Groq Cloud.

3. **Execution**
   Initialize the database and start the bot:
   `python bot.py`

---

## Disclaimer
This tool is for educational purposes. Users are responsible for complying with Amazon's terms of service regarding automated data collection.