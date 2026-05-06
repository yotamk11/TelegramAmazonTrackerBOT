import asyncio
from scraper import fetch_amazon_price
from database import get_all_tracked, update_price, remove_product, record_price_history

_SCRAPE_CONCURRENCY = 3  # max simultaneous Chrome instances


async def check_prices_periodically(context):
    print("[*] Starting periodic price check...")
    products = get_all_tracked()

    if not products:
        print("[!] No products to track.")
        return

    executor = context.bot_data.get('executor')
    semaphore = asyncio.Semaphore(_SCRAPE_CONCURRENCY)

    async def check_one(user_id, url, last_price, target_price, product_id, title):
        async with semaphore:
            print(f"[*] Checking product {product_id} (Target: ${target_price})...")
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(executor, fetch_amazon_price, url)

            if not result:
                return

            new_price_str, _ = result
            new_price = float(new_price_str)
            record_price_history(product_id, new_price)
            if new_price <= target_price:
                print(f"[!] TARGET REACHED for product {product_id}!")
                product_name = title or url
                message = (
                    f"🎯 **TARGET PRICE REACHED!**\n\n"
                    f"*{product_name}*\n\n"
                    f"Now available for **${new_price:.2f}**!\n"
                    f"(Your target was ${target_price:.2f})\n\n"
                    f"🔗 [Buy it now on Amazon]({url})"
                )
                try:
                    await context.bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
                    remove_product(product_id)
                except Exception as e:
                    print(f"[-] Messaging Error: {e}")
            else:
                update_price(product_id, new_price)

    await asyncio.gather(*[check_one(*p) for p in products])
    print("[*] Periodic check finished.")
