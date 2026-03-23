#!/usr/bin/env python3
"""Automate Gumroad product image uploads with Selenium.

Usage (Windows example):
  python gumroad_image_uploader.py \
    --download-dir "C:\\Users\\issda\\Downloads" \
    --profile-dir "C:\\Users\\issda\\AppData\\Local\\Google\\Chrome\\User Data" \
    --profile-name "Default"

Notes:
- This script expects you to already be logged into Gumroad.
- It uses robust, fallback selectors because Gumroad UI can change over time.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver import ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

DEFAULT_DOWNLOAD_DIR = r"C:\Users\issda\Downloads"
PRODUCTS_PAGE = "https://gumroad.com/products"


@dataclass(frozen=True)
class Product:
    name: str
    product_id: str


PRODUCTS_TO_UPDATE: tuple[Product, ...] = (
    Product("WorldForge", "tuxde"),
    Product("HYDRA Protocol", "hydra"),
    Product("Notion Templates Premium Bundle", "cebcjh"),
    Product("WorldForge duplicate", "worldforge"),
)


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("gumroad_upload.log", encoding="utf-8"),
        ],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload images to Gumroad products.")
    parser.add_argument("--download-dir", default=DEFAULT_DOWNLOAD_DIR, help="Folder containing source image files.")
    parser.add_argument(
        "--profile-dir",
        default=None,
        help=(
            "Chrome user data dir to reuse existing login session, e.g. "
            r"C:\Users\issda\AppData\Local\Google\Chrome\User Data"
        ),
    )
    parser.add_argument(
        "--profile-name",
        default="Default",
        help="Chrome profile name inside profile-dir (Default, Profile 1, etc.).",
    )
    parser.add_argument(
        "--driver-path",
        default=None,
        help="Optional explicit path to chromedriver executable.",
    )
    parser.add_argument("--headless", action="store_true", help="Run in headless mode.")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logs.")
    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="Retries per product when upload/save flow fails (default: 2).",
    )
    return parser.parse_args()


def create_driver(args: argparse.Namespace) -> WebDriver:
    options = ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    if args.headless:
        options.add_argument("--headless=new")

    if args.profile_dir:
        options.add_argument(f"--user-data-dir={args.profile_dir}")
        options.add_argument(f"--profile-directory={args.profile_name}")

    service = ChromeService(executable_path=args.driver_path) if args.driver_path else ChromeService()
    return webdriver.Chrome(service=service, options=options)


def sanitize(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def find_image_for_product(download_dir: Path, product: Product) -> Optional[Path]:
    if not download_dir.exists():
        logging.error("Download directory does not exist: %s", download_dir)
        return None

    image_extensions = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    files = [p for p in download_dir.iterdir() if p.is_file() and p.suffix.lower() in image_extensions]

    key_candidates = [sanitize(product.name), sanitize(product.product_id)]
    matched_files: list[Path] = []
    for file_path in files:
        normalized = sanitize(file_path.stem)
        if any(key in normalized or normalized in key for key in key_candidates):
            matched_files.append(file_path)

    if matched_files:
        newest_match = max(matched_files, key=lambda p: p.stat().st_mtime)
        logging.info("Matched image for '%s': %s", product.name, newest_match)
        return newest_match

    exact_filename_candidates = [
        f"{product.product_id}.png",
        f"{product.product_id}.jpg",
        f"{product.product_id}.jpeg",
        f"{product.name}.png",
        f"{product.name}.jpg",
    ]
    for filename in exact_filename_candidates:
        candidate = download_dir / filename
        if candidate.exists():
            logging.info("Matched exact filename for '%s': %s", product.name, candidate)
            return candidate

    logging.error("No image file found for product '%s' (%s)", product.name, product.product_id)
    return None


def click_first_visible(driver: WebDriver, locators: Iterable[tuple[str, str]], timeout: int = 12) -> bool:
    wait = WebDriverWait(driver, timeout)
    for by, locator in locators:
        try:
            element = wait.until(EC.element_to_be_clickable((by, locator)))
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            element.click()
            return True
        except TimeoutException:
            continue
        except WebDriverException as exc:
            logging.debug("Click failed for locator (%s, %s): %s", by, locator, exc)
    return False


def upload_product_image(driver: WebDriver, product: Product, image_path: Path) -> bool:
    wait = WebDriverWait(driver, 20)
    logging.info("Processing product: %s (%s)", product.name, product.product_id)

    driver.get(PRODUCTS_PAGE)

    product_link_locators = [
        (By.CSS_SELECTOR, f"a[href*='/{product.product_id}']"),
        (By.XPATH, f"//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{product.name.lower()}')]"),
        (By.XPATH, f"//a[contains(@href, '{product.product_id}') or contains(@href, '/{product.product_id}') ]"),
    ]

    if not click_first_visible(driver, product_link_locators, timeout=15):
        logging.error("Could not open product '%s' from products page.", product.name)
        return False

    time.sleep(1.5)

    upload_button_locators = [
        (By.XPATH, "//button[contains(., 'Upload images') or contains(., 'Upload image')]"),
        (By.XPATH, "//a[contains(., 'Upload images') or contains(., 'Upload image')]"),
        (By.XPATH, "//*[contains(@aria-label, 'Upload') and (self::button or self::a)]"),
    ]
    if not click_first_visible(driver, upload_button_locators, timeout=12):
        logging.warning("Upload button not clickable for '%s'; trying direct file input.", product.name)

    input_locators = [
        (By.CSS_SELECTOR, "input[type='file']"),
        (By.XPATH, "//input[@type='file']"),
    ]

    file_input = None
    for by, locator in input_locators:
        try:
            file_input = wait.until(EC.presence_of_element_located((by, locator)))
            if file_input:
                break
        except TimeoutException:
            continue

    if not file_input:
        logging.error("Could not find file input on product page '%s'.", product.name)
        return False

    try:
        file_input.send_keys(str(image_path.resolve()))
        wait.until(lambda d: file_input.get_attribute("value"))
        logging.info("Image uploaded for '%s': %s", product.name, image_path.name)
    except WebDriverException as exc:
        logging.error("Failed to upload image for '%s': %s", product.name, exc)
        return False
    except TimeoutException:
        logging.error("File selection timed out for '%s'.", product.name)
        return False

    save_locators = [
        (By.XPATH, "//button[contains(., 'Save changes') or contains(., 'Save')]"),
        (By.XPATH, "//button[@type='submit' and (contains(., 'Save') or contains(., 'Update'))]"),
        (By.XPATH, "//a[contains(., 'Save changes') or contains(., 'Save')]"),
    ]

    if not click_first_visible(driver, save_locators, timeout=15):
        logging.error("Could not click Save for '%s'.", product.name)
        return False

    logging.info("Saved product '%s'.", product.name)
    time.sleep(2)
    return True


def main() -> int:
    args = parse_args()
    setup_logging(args.verbose)

    download_dir = Path(os.path.expandvars(args.download_dir)).expanduser()
    logging.info("Using download directory: %s", download_dir)

    try:
        driver = create_driver(args)
    except WebDriverException as exc:
        logging.error("Could not start Chrome driver: %s", exc)
        return 1

    success_count = 0
    failed_products: list[str] = []

    try:
        driver.get(PRODUCTS_PAGE)
        logging.info("Opened Gumroad products page. Ensure you are logged in.")
        if "login" in driver.current_url.lower() or "sign" in driver.current_url.lower():
            logging.error("Session appears logged out. Open Gumroad in this profile and sign in first.")
            return 1

        for product in PRODUCTS_TO_UPDATE:
            image_path = find_image_for_product(download_dir, product)
            if not image_path:
                failed_products.append(f"{product.name}: image not found")
                continue

            product_success = False
            for attempt in range(1, args.max_retries + 1):
                logging.info("Attempt %d/%d for '%s'", attempt, args.max_retries, product.name)
                try:
                    product_success = upload_product_image(driver, product, image_path)
                    if product_success:
                        success_count += 1
                        break
                except (TimeoutException, NoSuchElementException, WebDriverException) as exc:
                    logging.exception("Selenium error for '%s' on attempt %d: %s", product.name, attempt, exc)
                except Exception as exc:  # noqa: BLE001
                    logging.exception("Unexpected error for '%s' on attempt %d: %s", product.name, attempt, exc)
                time.sleep(1)

            if not product_success:
                failed_products.append(f"{product.name}: upload/save step failed after retries")

        logging.info("Run completed. Success: %s, Failed: %s", success_count, len(failed_products))
        if failed_products:
            for item in failed_products:
                logging.error(" - %s", item)
            return 2
        return 0
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
