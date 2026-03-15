import asyncio
from scraper import fetch_amazon_price
from database import get_all_tracked, update_price, remove_product

async def check_prices_periodically(context):
    """
    Scheduled background task that iterates through all items in the database,
    scrapes their current Amazon price, and notifies the user if it drops below target.
    """
    print("[*] Starting periodic price check...")
    products = get_all_tracked()

    if not products:
        print("[!] No products to track.")
        return

    for user_id, url, last_price, target_price, product_id in products:
        print(f"[*] Checking product {product_id} (Target: ${target_price})...")
        new_price_str = fetch_amazon_price(url)

        if new_price_str:
            new_price = float(new_price_str)

            # Check if the current price hit the user's target
            if new_price <= target_price:
                print(f"[!] TARGET REACHED for product {product_id}!")
                message = (
                    f"🎯 **TARGET PRICE REACHED!**\n\n"
                    f"The product is now available for **${new_price:.2f}**!\n"
                    f"(Your target was ${target_price:.2f})\n\n"
                    f"🔗 [Buy it now on Amazon]({url})"
                )
                try:
                    await context.bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
                    # Stop tracking this product once notified
                    remove_product(product_id)
                except Exception as e:
                    print(f"[-] Messaging Error: {e}")
            else:
                # Update DB with current price for next comparison
                update_price(product_id, new_price)

        # Anti-scraping delay
        await asyncio.sleep(15)

    print("[*] Periodic check finished.")