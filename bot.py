import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from scraper import fetch_amazon_price
from ai_handler import get_ai_advice
from database import init_db, add_product
from clock import check_prices_periodically
import re

TOKEN = '8733045124:AAFcgcGHLwSJ1hF4bPzuey0ENc3JjsJIOc8'

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


def is_valid_amazon_url(url):
    """
    Checks if the provided string is a valid Amazon product URL using regex.
    Supports various Amazon domains (com, co.uk, de, etc.) and product patterns.
    """
    # Pattern to match standard Amazon product URLs (dp or gp/product)
    amazon_pattern = r"https?://(www\.)?amazon\.(com|co\.uk|de|ca|it|es|fr|in|co\.jp|com\.au)/[^\s]+/(dp|gp/product)/[A-Z0-9]{10}"
    return re.search(amazon_pattern, url) is not None

def prepare_amazon_url(url):
    """Clean the URL and force English/USD settings."""
    url = url.split('?')[0].split('ref=')[0]
    connector = "&" if "?" in url else "?"
    return f"{url}{connector}currency=USD&language=en_US"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message to the user."""
    await update.message.reply_text("Welcome! 🛒\nSend me an Amazon link to start tracking.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles link processing and target price inputs."""
    # Scenario 1: User is responding with a Target Price
    if context.user_data.get('waiting_for_target'):
        try:
            target_price = float(update.message.text)
            url = context.user_data.get('last_url')
            current_price = context.user_data.get('temp_price')

            add_product(update.effective_user.id, url, current_price, target_price)
            context.user_data['waiting_for_target'] = False

            await update.message.reply_text(f"✅ **Tracking Confirmed!**\nTarget hit at ${target_price:.2f}.")
            return
        except ValueError:
            await update.message.reply_text("❌ Please send a valid number.")
            return

    # Scenario 2: User sent an Amazon link
    user_text = update.message.text
    if is_valid_amazon_url(user_text):
        usd_url = prepare_amazon_url(user_text)
        status_msg = await update.message.reply_text("🔍 Validating link and fetching price...")
        price = fetch_amazon_price(usd_url)

        if price:
            ai_analysis = get_ai_advice(usd_url, price)
            context.user_data['last_url'] = usd_url
            keyboard = [[InlineKeyboardButton("🔔 Start Price Tracking", callback_data=f"track_{price}")]]

            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=status_msg.message_id,
                text=f"✅ **Price: ${price}**\n\n🤖 **AI Analysis:**\n{ai_analysis}",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
    else:
        await update.message.reply_text("Please send a valid Amazon URL.")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles button interaction to initiate target price flow."""
    query = update.callback_query
    await query.answer()
    if query.data.startswith("track_"):
        price = query.data.split("_")[1]
        context.user_data['waiting_for_target'] = True
        context.user_data['temp_price'] = price
        await query.message.reply_text(f"📉 Current: **${price}**. What is your **Target Price**?")


if __name__ == '__main__':
    init_db()
    application = ApplicationBuilder().token(TOKEN).build()

    # Schedule periodic checks every 30 minutes
    if application.job_queue:
        application.job_queue.run_repeating(check_prices_periodically, interval=1800, first=10)

    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))

    print("--- Bot is LIVE ---")
    application.run_polling()