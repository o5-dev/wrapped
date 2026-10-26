import argparse
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

from .cardlink import encode_card

DOCS = Path(__file__).resolve().parent.parent / "docs"


class CardRenderer:
    def __init__(self, scale=3):
        self.scale = scale
        self.playwright = None
        self.browser = None

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch()

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def render(self, payload):
        page = await self.browser.new_page(viewport={"width": 800, "height": 800}, device_scale_factor=self.scale)
        try:
            await page.goto((DOCS / "card.html").as_uri() + "?render#" + payload)
            await page.wait_for_function("window.cardReady === true", timeout=20000)
            return await page.locator("#card").screenshot()
        finally:
            await page.close()


def demo_payload(long_names):
    if long_names:
        return encode_card(
            server="The Extremely Long Server Name That Keeps Going",
            channel="super-duper-long-channel-name-here",
            total=1234567890,
            name="Řehoř Žlutoučký-Kůň the Magnificent",
            emoji="👨‍👩‍👧‍👦",
        )
    return encode_card(server="Hack Club", channel="general", total=54045, name="username", emoji="😂")


async def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("out")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--demo-long", action="store_true")
    parser.add_argument("--payload")
    parser.add_argument("--scale", type=int, default=3)
    args = parser.parse_args()

    if args.payload:
        payload = args.payload
    elif args.demo_long:
        payload = demo_payload(True)
    else:
        payload = demo_payload(False)

    renderer = CardRenderer(args.scale)
    await renderer.start()
    try:
        png = await renderer.render(payload)
    finally:
        await renderer.close()
    Path(args.out).write_bytes(png)
    print("wrote", args.out)


if __name__ == "__main__":
    asyncio.run(run())
