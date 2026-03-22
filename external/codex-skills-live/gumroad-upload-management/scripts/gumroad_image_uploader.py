#!/usr/bin/env python3
import argparse
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


DEFAULT_TARGETS = [
    "WorldForge",
    "HYDRA Protocol",
    "Notion Templates",
    "WorldForge duplicate",
]

DEFAULT_FILE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".pdf", ".zip", ".md", ".txt"}


@dataclass
class ProductLink:
    name: str
    href: str


def setup_logger(log_path: Path) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def norm(text: str) -> str:
    s = text.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def split_tokens(text: str) -> List[str]:
    return [t for t in norm(text).split(" ") if t]


def list_assets(images_dir: Path, allowed_exts: set[str] | None = None) -> List[Path]:
    if not images_dir.exists():
        return []
    extensions = allowed_exts or DEFAULT_FILE_EXTS
    files = [p for p in images_dir.iterdir() if p.is_file() and p.suffix.lower() in extensions]
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def image_score(product_name: str, image_path: Path) -> int:
    p_tokens = split_tokens(product_name)
    f_tokens = split_tokens(image_path.stem)
    if not p_tokens or not f_tokens:
        return 0
    score = 0
    for t in p_tokens:
        if t in f_tokens:
            score += 2
    p_join = norm(product_name)
    f_join = norm(image_path.stem)
    if p_join and p_join in f_join:
        score += 3
    return score


def pick_image(product_name: str, images: Sequence[Path], used: set) -> Optional[Path]:
    scored: List[Tuple[int, Path]] = []
    for img in images:
        if img in used:
            continue
        score = image_score(product_name, img)
        if score > 0:
            scored.append((score, img))
    if not scored:
        return None
    scored.sort(key=lambda x: (-x[0], x[1].name.lower()))
    return scored[0][1]


def ensure_selenium_cache_path() -> None:
    cache_dir = Path.home() / ".selenium-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("SE_CACHE_PATH", str(cache_dir))
    os.environ.setdefault("SELENIUM_MANAGER_CACHE_PATH", str(cache_dir))


def build_driver(profile_dir: Optional[Path], headless: bool, debugger_address: Optional[str]) -> webdriver.Chrome:
    options = Options()
    if debugger_address:
        options.debugger_address = debugger_address
    else:
        if profile_dir is None:
            raise ValueError("profile_dir is required when debugger_address is not used")
        options.add_argument(f"--user-data-dir={profile_dir}")
        options.add_argument("--profile-directory=Default")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--start-maximized")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--remote-debugging-port=0")
    if headless:
        options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(2)
    return driver


def wait_login_ready(driver: webdriver.Chrome, timeout: int) -> None:
    driver.get("https://app.gumroad.com/products")
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )


def collect_products(driver: webdriver.Chrome) -> List[ProductLink]:
    anchors = driver.find_elements(By.CSS_SELECTOR, "a[href*='/products/']")
    products: List[ProductLink] = []
    seen = set()
    for a in anchors:
        href = (a.get_attribute("href") or "").strip()
        txt = (a.text or "").strip()
        if not href or "/products/" not in href:
            continue
        if href in seen:
            continue
        if not txt:
            txt = href.rstrip("/").split("/")[-1]
        seen.add(href)
        products.append(ProductLink(name=txt, href=href))
    return products


def match_targets(products: Sequence[ProductLink], targets: Sequence[str]) -> List[ProductLink]:
    target_norms = [norm(t) for t in targets]
    out: List[ProductLink] = []
    for p in products:
        p_norm = norm(p.name)
        for t in target_norms:
            if t and (t in p_norm or p_norm in t):
                out.append(p)
                break
    return out


def open_edit_page(driver: webdriver.Chrome, href: str, timeout: int) -> None:
    edit_url = href.rstrip("/")
    if not edit_url.endswith("/edit"):
        edit_url += "/edit"
    driver.get(edit_url)
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )


def find_file_input(driver: webdriver.Chrome, timeout: int):
    wait = WebDriverWait(driver, timeout)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']")))
    inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
    for inp in inputs:
        try:
            if inp.is_enabled():
                return inp
        except Exception:
            continue
    if inputs:
        return inputs[0]
    raise NoSuchElementException("No file input found")


def click_save_if_present(driver: webdriver.Chrome) -> bool:
    candidates = [
        "//button[contains(., 'Save changes')]",
        "//button[contains(., 'Save')]",
        "//button[contains(., 'Update')]",
    ]
    for xp in candidates:
        try:
            btn = driver.find_element(By.XPATH, xp)
            if btn.is_enabled():
                btn.click()
                return True
        except Exception:
            continue
    return False


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Upload Gumroad product images via Selenium + existing Chrome profile")
    p.add_argument("--profile-dir", default=None, help="Chrome user data dir, e.g. C:/Users/you/AppData/Local/Google/Chrome/User Data")
    p.add_argument("--debugger-address", default=None, help="Attach to an existing Chrome debug session, e.g. 127.0.0.1:9222")
    p.add_argument("--images-dir", default=None, help="Folder containing files. Default: C:/Users/<user>/Downloads, fallback OneDrive/Downloads")
    p.add_argument("--asset-exts", default=",".join(sorted(DEFAULT_FILE_EXTS)), help="Comma-separated file extensions (without dot)")
    p.add_argument("--targets", nargs="+", default=DEFAULT_TARGETS, help="Product names to target")
    p.add_argument("--timeout", type=int, default=30)
    p.add_argument("--headless", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="Preview matches without uploading")
    p.add_argument("--log", default="gumroad_upload.log")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    log_path = Path(args.log).resolve()
    setup_logger(log_path)
    ensure_selenium_cache_path()

    user_home = Path.home()
    default_downloads = user_home / "Downloads"
    fallback_downloads = user_home / "OneDrive" / "Downloads"
    images_dir = Path(args.images_dir) if args.images_dir else default_downloads
    if (not images_dir.exists() or not any(images_dir.iterdir())) and fallback_downloads.exists():
        images_dir = fallback_downloads

    profile_dir: Optional[Path] = None
    if args.profile_dir:
        profile_dir = Path(args.profile_dir)
        if not profile_dir.exists():
            logging.error("Profile dir not found: %s", profile_dir)
            return 2
    elif not args.debugger_address:
        logging.error("Pass either --profile-dir or --debugger-address")
        return 2

    allowed_exts = {f".{e.strip().lower().lstrip('.')}" for e in args.asset_exts.split(",") if e.strip()}
    images = list_assets(images_dir, allowed_exts)
    if not images:
        logging.error("No files found in %s", images_dir)
        return 2
    logging.info("Allowed extensions: %s", ", ".join(sorted(allowed_exts)))

    if args.debugger_address:
        logging.info("Attaching to Chrome debugger at: %s", args.debugger_address)
    else:
        logging.info("Using profile: %s", profile_dir)
    logging.info("Using files dir: %s", images_dir)
    logging.info("Found %d file(s)", len(images))

    driver = None
    used_images = set()

    try:
        driver = build_driver(profile_dir, args.headless, args.debugger_address)
        wait_login_ready(driver, args.timeout)

        products = collect_products(driver)
        if not products:
            logging.error("No products found on Gumroad products page. Ensure you are logged in on this Chrome profile.")
            return 3

        matched_products = match_targets(products, args.targets)
        if not matched_products:
            logging.error("No target products matched. Available product names: %s", [p.name for p in products])
            return 4

        logging.info("Matched %d target product(s)", len(matched_products))

        for p in matched_products:
            img = pick_image(p.name, images, used_images)
            if img is None:
                logging.warning("SKIP product='%s' (no filename match in images dir)", p.name)
                continue

            used_images.add(img)
            logging.info("MATCH product='%s' -> image='%s'", p.name, img.name)

            if args.dry_run:
                continue

            open_edit_page(driver, p.href, args.timeout)
            file_input = find_file_input(driver, args.timeout)
            file_input.send_keys(str(img.resolve()))
            time.sleep(3)
            saved = click_save_if_present(driver)
            if saved:
                logging.info("Uploaded and clicked save for '%s'", p.name)
                time.sleep(2)
            else:
                logging.info("Uploaded for '%s' (save button not auto-detected; verify in UI)", p.name)

        logging.info("Done. Log saved to %s", log_path)
        return 0

    except TimeoutException as e:
        logging.exception("Timeout: %s", e)
        return 5
    except Exception as e:
        logging.exception("Failure: %s", e)
        return 1
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
