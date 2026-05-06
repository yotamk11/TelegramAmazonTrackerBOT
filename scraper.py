import threading
import undetected_chromedriver as uc
from webdriver_manager.chrome import ChromeDriverManager
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re

_driver_init_lock = threading.Lock()


def _set_us_delivery(driver):
    """Click through Amazon's 'Deliver to' UI to set delivery zip to the US."""
    try:
        wait = WebDriverWait(driver, 6)

        btn = wait.until(EC.element_to_be_clickable((By.ID, "nav-global-location-popover-link")))
        btn.click()

        zip_input = wait.until(EC.visibility_of_element_located((By.ID, "GLUXZipUpdateInput")))
        zip_input.clear()
        zip_input.send_keys("10001")

        apply_btn = driver.find_element(By.CSS_SELECTOR, "span#GLUXZipUpdate input[type='submit']")
        apply_btn.click()
        time.sleep(1.5)

        try:
            done_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.a-button-text[data-action='GLUXConfirmAction']"))
            )
            done_btn.click()
        except:
            pass

        print("[+] Delivery location set to US (10001)")
    except Exception as e:
        print(f"[!] Could not set delivery location via UI: {e}")


def fetch_amazon_price(url):
    """
    Returns (price_str, title) tuple, or None on failure.
    """
    options = uc.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')

    try:
        print("[*] Scraping Amazon for price and title...")
        with _driver_init_lock:
            driver_path = ChromeDriverManager().install()
            driver = uc.Chrome(options=options, driver_executable_path=driver_path, use_subprocess=True)

        driver.get("https://www.amazon.com")
        time.sleep(3)
        driver.add_cookie({"name": "i18n-prefs", "value": "USD", "domain": ".amazon.com"})
        driver.add_cookie({"name": "lc-main",    "value": "en_US", "domain": ".amazon.com"})
        _set_us_delivery(driver)

        driver.get(url)
        time.sleep(5)

        # Scrape title
        title = None
        try:
            title = driver.find_element(By.CSS_SELECTOR, "#productTitle").text.strip()
        except:
            pass

        # Strategy 1: combined price span
        try:
            full_price_element = driver.find_element(By.CSS_SELECTOR, "span.a-price")
            raw_text = full_price_element.get_attribute("innerText").replace('\n', '')
            print(f"[+] Raw price text: {raw_text}")
            if '$' not in raw_text:
                print(f"[-] Price not in USD (got: {raw_text})")
                return None
            match = re.search(r"(\d[\d,]*\.\d{2})", raw_text)
            if match:
                price = "{:.2f}".format(float(match.group(1).replace(',', '')))
                return price, title
        except:
            pass

        # Strategy 2: separate whole + fraction spans
        try:
            price_block = driver.find_element(By.CSS_SELECTOR, "span.a-price")
            if '$' not in price_block.get_attribute("outerHTML"):
                print("[-] Price block does not contain USD symbol")
                return None
            whole = driver.find_element(By.CSS_SELECTOR, "span.a-price-whole").text.replace(',', '').strip()
            fraction = driver.find_element(By.CSS_SELECTOR, "span.a-price-fraction").text.strip()
            if whole and fraction:
                price = "{:.2f}".format(float(f"{whole}.{fraction}"))
                return price, title
        except:
            pass

        return None

    except Exception as e:
        print(f"[-] Scraping Error: {e}")
        return None
    finally:
        if 'driver' in locals():
            driver.quit()
