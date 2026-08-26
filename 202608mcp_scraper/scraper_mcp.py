import asyncio
import os
import urllib.request
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import certifi
from dotenv import load_dotenv
from fastmcp import FastMCP
from playwright.async_api import async_playwright

# User-Agentを付けないと素のurllibだと判断されて403で弾くサイトがあり、
# RobotFileParserは403を「全面禁止」と誤解釈してしまうため明示的に付与する
ROBOTS_TXT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# python.org版PythonはmacOSのシステム証明書ストアを使わないため、
# certifiの証明書バンドルを明示的に指定して証明書検証エラーを防ぐ
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

load_dotenv(Path(__file__).parent / ".env")

BRIGHT_DATA_AUTH = os.environ["BRIGHT_DATA_AUTH"]
CDP_ENDPOINT = f"wss://{BRIGHT_DATA_AUTH}@brd.superproxy.io:9222"

mcp = FastMCP("scraper")


def _allowed_by_robots_txt(url: str) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = RobotFileParser()
    parser.set_url(robots_url)
    try:
        request = urllib.request.Request(
            robots_url, headers={"User-Agent": ROBOTS_TXT_USER_AGENT}
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            content = response.read().decode("utf-8", errors="replace")
        parser.parse(content.splitlines())
    except Exception:
        # robots.txtが取得できない場合はブロックしない
        return True
    return parser.can_fetch("*", url)


async def _scrape_once(url: str) -> dict:
    if not _allowed_by_robots_txt(url):
        return {
            "success": False,
            "url": url,
            "status": 402,
            "error": "robots.txtによりこのURLへのアクセスが禁止されています",
        }

    async with async_playwright() as playwright:
        browser = await playwright.chromium.connect_over_cdp(CDP_ENDPOINT)
        try:
            page = await browser.new_page()
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            title = await page.title()
            text = await page.inner_text("body")
            return {
                "success": True,
                "url": url,
                "title": title,
                "text": text[:5000],
            }
        finally:
            await browser.close()


async def _scrape_with_retry(url: str, max_retries: int = 3) -> dict:
    last_error = None
    for attempt in range(max_retries):
        try:
            return await _scrape_once(url)
        except Exception as e:
            last_error = str(e)
            await asyncio.sleep(2**attempt)
    return {"success": False, "url": url, "error": last_error}


@mcp.tool()
async def scrape_website(url: str) -> dict:
    """指定したURLのページ内容を取得する。robots.txtを自動で確認し、禁止されている場合は取得しない。"""
    return await _scrape_with_retry(url)


@mcp.tool()
async def batch_scrape(urls: list[str]) -> list[dict]:
    """複数のURLを並列でスクレイピングする。"""
    return await asyncio.gather(*[_scrape_with_retry(url) for url in urls])


if __name__ == "__main__":
    mcp.run()
