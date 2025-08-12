import asyncio

from playwright.async_api import Page

from config_app import PASSWORD, EMAIL, BASE_URL_PRO
from parce_screenshots.delete_any_popup import nuke_poll_overlay
from parce_screenshots.utils import goto_strict


class AuthService:
    def __init__(self, page: Page):
        self.page = page

    async def login(self):
        await goto_strict(
            self.page,
            f"{BASE_URL_PRO}/auth/login#account",
            nuke_overlays=nuke_poll_overlay,
            expect_url=f"{BASE_URL_PRO}/auth/login#account",
        )

        await self.page.wait_for_selector('input[name="email"]', timeout=10000)
        await self.page.fill('input[name="email"]', EMAIL)
        await self.page.fill('input[name="password"]', PASSWORD)
        await self.page.click('button[type="submit"]')
        await asyncio.sleep(2)
