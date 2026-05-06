import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from scraper import fetch_amazon_price
from ai_handler import get_ai_advice
from database import init_db, add_product, get_user_products, get_product_by_id, get_price_history, record_price_history, delete_product_and_history
from graph import build_price_graph
from clock import check_prices_periodically
import re
import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Get the token from environment variables
TOKEN = os.getenv('TELEGRAM_TOKEN')

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
    """Extract the ASIN and rebuild as a canonical amazon.com USD URL."""
    asin_match = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', url)
    if asin_match:
        asin = asin_match.group(1)
        return f"https://www.amazon.com/dp/{asin}?currency=USD&language=en_US"
    # Fallback: strip params and add currency
    url = re.split(r'[?#]', url)[0]
    url = re.sub(r'/ref=.*', '', url)
    return f"{url}?currency=USD&language=en_US"


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

            title = context.user_data.get('temp_title')
            product_id = add_product(update.effective_user.id, url, current_price, target_price, title)
            record_price_history(product_id, current_price)
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
        loop = asyncio.get_event_loop()
        executor = context.bot_data.get('executor')
        result = await loop.run_in_executor(executor, fetch_amazon_price, usd_url)

        if result:
            price, title = result
            ai_analysis = await loop.run_in_executor(executor, get_ai_advice, usd_url, price, title)
            context.user_data['last_url'] = usd_url
            context.user_data['temp_title'] = title
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


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists the user's tracked products as a numbered text list with graph buttons."""
    user_id = update.effective_user.id
    products = get_user_products(user_id)

    if not products:
        await update.message.reply_text("You have no tracked products yet.")
        return

    keyboard = []
    for prod_id, url, price, target, title in products:
        asin_match = re.search(r'/dp/([A-Z0-9]{10})', url)
        name = title or f"Product {asin_match.group(1) if asin_match else prod_id}"
        label = name[:40] + '...' if len(name) > 40 else name
        keyboard.append([InlineKeyboardButton(
            f"{label} — ${price:.2f}",
            callback_data=f"graph_{prod_id}"
        )])

    await update.message.reply_text(
        "Your tracked products:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists tracked products with a delete button for each."""
    user_id = update.effective_user.id
    products = get_user_products(user_id)

    if not products:
        await update.message.reply_text("You have no tracked products.")
        return

    keyboard = []
    for prod_id, url, price, target, title in products:
        asin_match = re.search(r'/dp/([A-Z0-9]{10})', url)
        name = title or f"Product {asin_match.group(1) if asin_match else prod_id}"
        label = name[:40] + '...' if len(name) > 40 else name
        keyboard.append([InlineKeyboardButton(
            f"Delete: {label}",
            callback_data=f"confirm_delete_{prod_id}"
        )])

    await update.message.reply_text(
        "Choose a product to stop tracking and delete its history:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles button interactions: tracking start and price graph requests."""
    query = update.callback_query
    await query.answer()

    if query.data.startswith("track_"):
        price = query.data.split("_")[1]
        context.user_data['waiting_for_target'] = True
        context.user_data['temp_price'] = price
        await query.message.reply_text(f"📉 Current: **${price}**. What is your **Target Price**?")

    elif query.data.startswith("graph_"):
        product_id = int(query.data.split("_")[1])
        product = get_product_by_id(product_id)
        history = get_price_history(product_id)

        if not history:
            await query.message.reply_text("No price history recorded for this product yet.")
            return

        _, url, _, target_price, title = product
        graph_buf = build_price_graph(title or url, history, target_price)
        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=graph_buf,
            caption=f"Price history — target: ${target_price:.2f}"
        )

    elif query.data.startswith("confirm_delete_"):
        product_id = int(query.data.split("_")[2])
        product = get_product_by_id(product_id)
        if product:
            _, _, _, _, title = product
            delete_product_and_history(product_id)
            await query.edit_message_text(f"Deleted: {title or f'Product {product_id}'}")
        else:
            await query.edit_message_text("Product not found.")


if __name__ == '__main__':
    init_db()
    executor = ThreadPoolExecutor(max_workers=5)
    application = ApplicationBuilder().token(TOKEN).build()
    application.bot_data['executor'] = executor

    # Schedule periodic checks every 30 minutes
    if application.job_queue:
        application.job_queue.run_repeating(check_prices_periodically, interval=1800, first=10)

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('products', history_command))
    application.add_handler(CommandHandler('delete', delete_command))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))

    print("--- Bot is LIVE ---")
    application.run_polling()