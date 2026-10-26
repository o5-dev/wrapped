"""Turns a card payload into a PNG by opening docs/index.html in headless Chromium.

The bot and the website use the exact same page, so there is only one card template.

    python -m bot.render --demo card.png          # sample card
    python -m bot.render --demo-long card.png     # long names, to test the scale-down
    python -m bot.render --payload <payload> card.png
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

from .cardlink import encode_card

DOCS = Path(__file__).resolve().parent.parent / "docs"


class CardRenderer:
    """Keeps one browser open so each card only takes a moment. start() once, render() many times."""

    def __init__(self, docs: Path = DOCS, scale: int = 3):
        self.docs, self.scale = docs, scale
        self._pw = self._browser = None

    async def start(self):
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch()

    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    async def render(self, payload: str) -> bytes:
        page = await self._browser.new_page(
            viewport={"width": 800, "height": 800}, device_scale_factor=self.scale
        )
        try:
            await page.goto((self.docs / "index.html").as_uri() + "?render#" + payload)
            await page.wait_for_function("window.__cardReady === true", timeout=20000)
            return await page.locator("#card").screenshot()
        finally:
            await page.close()


def _demo(long: bool) -> str:
    if long:
        return encode_card(
            server="The Extremely Long Server Name That Keeps Going",
            channel="super-duper-long-channel-name-here",
            total=1234567890,
            name="Řehoř Žlutoučký-Kůň the Magnificent",
            emoji="👨‍👩‍👧‍👦",
        )
    return encode_card(server="Hack Club", channel="channel", total=54045, name="username", emoji="😂")


async def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--demo", action="store_true")
    g.add_argument("--demo-long", action="store_true")
    g.add_argument("--payload")
    ap.add_argument("--scale", type=int, default=3)
    a = ap.parse_args()

    payload = a.payload or _demo(a.demo_long)
    r = CardRenderer(scale=a.scale)
    await r.start()
    try:
        Path(a.out).write_bytes(await r.render(payload))
    finally:
        await r.close()
    print("wrote", a.out)


if __name__ == "__main__":
    asyncio.run(_main())
