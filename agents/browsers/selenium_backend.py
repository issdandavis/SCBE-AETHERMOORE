"""
Selenium Browser Backend
========================

Browser automation using Selenium WebDriver.

Requirements:
    pip install selenium webdriver-manager
"""

import asyncio
from typing import Optional, Dict, Any, List
from .base import BrowserBackend

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.support.ui import WebDriverWait, Select
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False


class SeleniumBackend(BrowserBackend):
    """
    Browser backend using Selenium WebDriver.

    Selenium provides:
    - Wide browser support (Chrome, Firefox, Safari, Edge, IE)
    - Mature ecosystem with extensive documentation
    - Multi-language bindings
    - Grid support for distributed testing
    - Strong enterprise adoption
    """

    name = "selenium"

    def __init__(
        self,
        browser: str = "chrome",
        headless: bool = True,
        implicit_wait: int = 10,
        page_load_timeout: int = 30,
        driver_path: Optional[str] = None
    ):
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium not installed. Run: pip install selenium webdriver-manager")

        self.browser = browser
        self.headless = headless
        self.implicit_wait = implicit_wait
        self.page_load_timeout = page_load_timeout
        self.driver_path = driver_path

        self._driver = None
        self._loop = None

    async def initialize(self) -> bool:
        """Initialize Selenium WebDriver."""
        self._loop = asyncio.get_event_loop()

        def _init_driver():
            if self.browser == "chrome":
                options = ChromeOptions()
                if self.headless:
                    options.add_argument("--headless=new")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--window-size=1280,720")
                options.add_argument("user-agent=SCBE-GovernedBrowser/1.0 (Selenium)")

                if self.driver_path:
                    service = ChromeService(executable_path=self.driver_path)
                elif WEBDRIVER_MANAGER_AVAILABLE:
                    service = ChromeService(ChromeDriverManager().install())
                else:
                    service = ChromeService()

                driver = webdriver.Chrome(service=service, options=options)

            elif self.browser == "firefox":
                from selenium.webdriver.firefox.options import Options as FirefoxOptions
                from selenium.webdriver.firefox.service import Service as FirefoxService

                options = FirefoxOptions()
                if self.headless:
                    options.add_argument("--headless")

                driver = webdriver.Firefox(options=options)

            elif self.browser == "edge":
                from selenium.webdriver.edge.options import Options as EdgeOptions
                from selenium.webdriver.edge.service import Service as EdgeService

                options = EdgeOptions()
                if self.headless:
                    options.add_argument("--headless")

                driver = webdriver.Edge(options=options)

            else:
                raise ValueError(f"Unsupported browser: {self.browser}")

            driver.implicitly_wait(self.implicit_wait)
            driver.set_page_load_timeout(self.page_load_timeout)
            return driver

        try:
            self._driver = await self._loop.run_in_executor(None, _init_driver)
            print(f"[Selenium] Initialized {self.browser} (headless={self.headless})")
            return True
        except Exception as e:
            print(f"[Selenium] Initialization failed: {e}")
            return False

    def _run_sync(self, func):
        """Run synchronous Selenium function in executor."""
        return self._loop.run_in_executor(None, func)

    async def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate to URL."""
        def _nav():
            self._driver.get(url)
            return {"url": url, "title": self._driver.title}

        return await self._run_sync(_nav)

    async def click(self, selector: str) -> Dict[str, Any]:
        """Click element by CSS selector."""
        def _click():
            try:
                element = self._driver.find_element(By.CSS_SELECTOR, selector)
                element.click()
                return {"selector": selector, "clicked": True}
            except Exception as e:
                return {"selector": selector, "clicked": False, "error": str(e)}

        return await self._run_sync(_click)

    async def type_text(self, selector: str, text: str) -> Dict[str, Any]:
        """Type text into element."""
        def _type():
            try:
                element = self._driver.find_element(By.CSS_SELECTOR, selector)
                element.clear()
                element.send_keys(text)
                return {"selector": selector, "typed": True, "length": len(text)}
            except Exception as e:
                return {"selector": selector, "typed": False, "error": str(e)}

        return await self._run_sync(_type)

    async def get_page_content(self) -> str:
        """Get page source."""
        return await self._run_sync(lambda: self._driver.page_source)

    async def screenshot(self) -> bytes:
        """Take screenshot."""
        return await self._run_sync(lambda: self._driver.get_screenshot_as_png())

    async def execute_script(self, script: str) -> Any:
        """Execute JavaScript."""
        return await self._run_sync(lambda: self._driver.execute_script(script))

    async def get_current_url(self) -> str:
        """Get current page URL."""
        return await self._run_sync(lambda: self._driver.current_url)

    async def scroll(self, direction: str = "down", amount: int = 300) -> Dict[str, Any]:
        """Scroll the page."""
        delta = amount if direction == "down" else -amount

        def _scroll():
            self._driver.execute_script(f"window.scrollBy(0, {delta})")
            return {"direction": direction, "amount": amount}

        return await self._run_sync(_scroll)

    async def find_element(self, selector: str) -> Optional[Dict[str, Any]]:
        """Find element by CSS selector."""
        def _find():
            try:
                element = self._driver.find_element(By.CSS_SELECTOR, selector)
                return {
                    "selector": selector,
                    "found": True,
                    "tag": element.tag_name,
                    "text": element.text[:100] if element.text else None,
                    "displayed": element.is_displayed()
                }
            except NoSuchElementException:
                return {"selector": selector, "found": False}

        return await self._run_sync(_find)

    async def get_cookies(self) -> List[Dict[str, Any]]:
        """Get browser cookies."""
        return await self._run_sync(lambda: self._driver.get_cookies())

    async def set_cookie(self, cookie: Dict[str, Any]) -> bool:
        """Set a cookie."""
        def _set():
            try:
                self._driver.add_cookie(cookie)
                return True
            except Exception:
                return False

        return await self._run_sync(_set)

    async def close(self) -> None:
        """Close browser."""
        if self._driver:
            await self._run_sync(lambda: self._driver.quit())
        print("[Selenium] Browser closed")

    # ==========================================================================
    # Selenium-Specific Features
    # ==========================================================================

    async def find_by_xpath(self, xpath: str) -> Optional[Dict[str, Any]]:
        """Find element by XPath."""
        def _find():
            try:
                element = self._driver.find_element(By.XPATH, xpath)
                return {
                    "xpath": xpath,
                    "found": True,
                    "tag": element.tag_name,
                    "text": element.text[:100] if element.text else None
                }
            except NoSuchElementException:
                return {"xpath": xpath, "found": False}

        return await self._run_sync(_find)

    async def find_by_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Find element by text content."""
        xpath = f"//*[contains(text(), '{text}')]"
        return await self.find_by_xpath(xpath)

    async def wait_for_element(self, selector: str, timeout: int = 10) -> bool:
        """Wait for element to be present."""
        def _wait():
            try:
                WebDriverWait(self._driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                return True
            except TimeoutException:
                return False

        return await self._run_sync(_wait)

    async def wait_for_clickable(self, selector: str, timeout: int = 10) -> bool:
        """Wait for element to be clickable."""
        def _wait():
            try:
                WebDriverWait(self._driver, timeout).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                return True
            except TimeoutException:
                return False

        return await self._run_sync(_wait)

    async def get_page_title(self) -> str:
        """Get page title."""
        return await self._run_sync(lambda: self._driver.title)

    async def submit_form(self, form_selector: str) -> Dict[str, Any]:
        """Submit a form."""
        def _submit():
            try:
                form = self._driver.find_element(By.CSS_SELECTOR, form_selector)
                form.submit()
                return {"selector": form_selector, "submitted": True}
            except Exception as e:
                return {"selector": form_selector, "submitted": False, "error": str(e)}

        return await self._run_sync(_submit)

    async def select_dropdown(self, selector: str, value: str, by: str = "value") -> Dict[str, Any]:
        """Select option from dropdown."""
        def _select():
            try:
                element = self._driver.find_element(By.CSS_SELECTOR, selector)
                select = Select(element)
                if by == "value":
                    select.select_by_value(value)
                elif by == "text":
                    select.select_by_visible_text(value)
                elif by == "index":
                    select.select_by_index(int(value))
                return {"selector": selector, "value": value, "selected": True}
            except Exception as e:
                return {"selector": selector, "selected": False, "error": str(e)}

        return await self._run_sync(_select)

    async def hover(self, selector: str) -> Dict[str, Any]:
        """Hover over element."""
        def _hover():
            try:
                element = self._driver.find_element(By.CSS_SELECTOR, selector)
                ActionChains(self._driver).move_to_element(element).perform()
                return {"selector": selector, "hovered": True}
            except Exception as e:
                return {"selector": selector, "hovered": False, "error": str(e)}

        return await self._run_sync(_hover)

    async def double_click(self, selector: str) -> Dict[str, Any]:
        """Double-click element."""
        def _dclick():
            try:
                element = self._driver.find_element(By.CSS_SELECTOR, selector)
                ActionChains(self._driver).double_click(element).perform()
                return {"selector": selector, "double_clicked": True}
            except Exception as e:
                return {"selector": selector, "double_clicked": False, "error": str(e)}

        return await self._run_sync(_dclick)

    async def right_click(self, selector: str) -> Dict[str, Any]:
        """Right-click (context menu) on element."""
        def _rclick():
            try:
                element = self._driver.find_element(By.CSS_SELECTOR, selector)
                ActionChains(self._driver).context_click(element).perform()
                return {"selector": selector, "right_clicked": True}
            except Exception as e:
                return {"selector": selector, "right_clicked": False, "error": str(e)}

        return await self._run_sync(_rclick)

    async def drag_and_drop(self, source_selector: str, target_selector: str) -> Dict[str, Any]:
        """Drag element to target."""
        def _drag():
            try:
                source = self._driver.find_element(By.CSS_SELECTOR, source_selector)
                target = self._driver.find_element(By.CSS_SELECTOR, target_selector)
                ActionChains(self._driver).drag_and_drop(source, target).perform()
                return {"source": source_selector, "target": target_selector, "success": True}
            except Exception as e:
                return {"source": source_selector, "target": target_selector, "success": False, "error": str(e)}

        return await self._run_sync(_drag)

    async def switch_to_frame(self, frame_id: str) -> bool:
        """Switch to iframe."""
        def _switch():
            try:
                self._driver.switch_to.frame(frame_id)
                return True
            except Exception:
                return False

        return await self._run_sync(_switch)

    async def switch_to_default(self) -> None:
        """Switch back to main content."""
        await self._run_sync(lambda: self._driver.switch_to.default_content())

    async def get_window_handles(self) -> List[str]:
        """Get all window handles."""
        return await self._run_sync(lambda: self._driver.window_handles)

    async def switch_to_window(self, handle: str) -> bool:
        """Switch to window by handle."""
        def _switch():
            try:
                self._driver.switch_to.window(handle)
                return True
            except Exception:
                return False

        return await self._run_sync(_switch)

    async def accept_alert(self) -> Dict[str, Any]:
        """Accept browser alert."""
        def _accept():
            try:
                alert = self._driver.switch_to.alert
                text = alert.text
                alert.accept()
                return {"accepted": True, "text": text}
            except Exception as e:
                return {"accepted": False, "error": str(e)}

        return await self._run_sync(_accept)

    async def dismiss_alert(self) -> Dict[str, Any]:
        """Dismiss browser alert."""
        def _dismiss():
            try:
                alert = self._driver.switch_to.alert
                text = alert.text
                alert.dismiss()
                return {"dismissed": True, "text": text}
            except Exception as e:
                return {"dismissed": False, "error": str(e)}

        return await self._run_sync(_dismiss)

    async def maximize_window(self) -> None:
        """Maximize browser window."""
        await self._run_sync(lambda: self._driver.maximize_window())

    async def set_window_size(self, width: int, height: int) -> None:
        """Set browser window size."""
        await self._run_sync(lambda: self._driver.set_window_size(width, height))


# =============================================================================
# Example Usage
# =============================================================================

async def example_usage():
    """Example of using SeleniumBackend with GovernedBrowser."""
    from .base import GovernedBrowser

    # Create backend
    backend = SeleniumBackend(
        browser="chrome",
        headless=True
    )

    # Wrap with governance
    browser = GovernedBrowser(
        backend,
        agent_id="selenium-agent-001"
    )

    # Initialize
    if await browser.initialize():
        # All actions are now governed by SCBE
        result = await browser.navigate("https://example.com")
        print(f"Navigate result: {result}")

        # Take screenshot
        result = await browser.screenshot()
        print(f"Screenshot result: {result}")

        # Get summary
        browser.print_summary()

        # Close
        await browser.close()


if __name__ == "__main__":
    asyncio.run(example_usage())
