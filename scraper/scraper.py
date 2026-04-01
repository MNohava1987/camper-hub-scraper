import json
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


def scrape_page(url: str, timeout_ms: int = 45000) -> dict:
    """
    Render page fully and return:
      {
        "text":     visible body text,
        "api_data": list of JSON payloads captured from XHR/fetch calls
      }
    Intercepts all network responses so we catch API calls the page makes
    after initial load (common on React/Next.js sites).
    """
    captured_api = []

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()

        # Capture every JSON response the page fetches
        def handle_response(response):
            try:
                ct = response.headers.get("content-type", "")
                if "json" in ct and response.status == 200:
                    try:
                        data = response.json()
                        captured_api.append({
                            "url": response.url,
                            "data": data
                        })
                    except Exception:
                        pass
            except Exception:
                pass

        page.on("response", handle_response)

        try:
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        except PWTimeout:
            pass

        # Extra wait for lazy-loaded content
        page.wait_for_timeout(5000)

        # Scroll to trigger any lazy loading
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2000)

        text = page.inner_text("body")
        context.close()
        browser.close()

    return {
        "text": text.strip(),
        "api_data": captured_api,
    }
