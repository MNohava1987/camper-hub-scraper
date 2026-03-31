from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


def scrape_page(url: str, timeout_ms: int = 30000) -> str:
    """Render the page fully (JS included) and return visible body text."""
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            # Extra wait for JS-heavy React/Next.js pages
            page.wait_for_timeout(3000)
            text = page.inner_text("body")
        except PWTimeout:
            # Fallback: grab whatever rendered so far
            text = page.inner_text("body")
        finally:
            browser.close()
    return text.strip()
