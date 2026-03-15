import undetected_chromedriver as uc
import time
from selenium.webdriver.common.by import By
import re


def fetch_amazon_price(url):
    """
    Navigates to an Amazon URL using a mobile User-Agent to extract the exact price.
    Forces USD currency settings via cookies and regex matching for high precision.

    Args:
        url (str): The Amazon product link.

    Returns:
        str: The formatted price (e.g., '19.95') or None if extraction fails.
    """
    options = uc.ChromeOptions()
    mobile_ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
    options.add_argument(f'--user-agent={mobile_ua}')

    try:
        print("[*] Scraping Amazon for exact price (including cents)...")
        driver = uc.Chrome(options=options)
        driver.get(url)

        # Force USD currency by injecting a cookie
        driver.add_cookie({"name": "i18n-prefs", "value": "USD", "domain": ".amazon.com"})
        driver.refresh()
        time.sleep(5)

        # Strategy 1: Attempt to find combined price text in span.a-price
        try:
            full_price_element = driver.find_element(By.CSS_SELECTOR, "span.a-price")
            if full_price_element:
                raw_text = full_price_element.get_attribute("innerText").replace('\n', '')
                print(f"[+] Raw price text: {raw_text}")
                match = re.search(r"(\d+\.\d{2})", raw_text)
                if match:
                    return "{:.2f}".format(float(match.group(1)))
        except:
            pass

        # Strategy 2: Fallback to separate whole and fraction elements
        try:
            whole = driver.find_element(By.CSS_SELECTOR, "span.a-price-whole").text.replace(',', '').strip()
            fraction = driver.find_element(By.CSS_SELECTOR, "span.a-price-fraction").text.strip()
            if whole and fraction:
                final_val = float(f"{whole}.{fraction}")
                return "{:.2f}".format(final_val)
        except:
            pass

        return None

    except Exception as e:
        print(f"[-] Scraping Error: {e}")
        return None
    finally:
        if 'driver' in locals():
            driver.quit()