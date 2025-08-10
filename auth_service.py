import asyncio

from playwright.async_api import Page

from config_app import PASSWORD, EMAIL


class AuthService:
    def __init__(self, page: Page):
        self.page = page

    async def login(self):
        await self.page.goto("https://tophotels.pro/auth/login", timeout=20000)
        await self.page.wait_for_selector('input[name="email"]', timeout=10000)
        await self.page.fill('input[name="email"]', EMAIL)
        await self.page.fill('input[name="password"]', PASSWORD)
        await self.page.click('button[type="submit"]')
        await asyncio.sleep(2)
