import asyncio
import unittest
from unittest.mock import patch

import scrape


class ScrapeToolsTests(unittest.IsolatedAsyncioTestCase):
	async def test_preserves_declared_group_order(self) -> None:
		real_sleep = asyncio.sleep

		async def fetch_page_html(client, page, api):
			if page == "slow":
				await real_sleep(0.01)
			return page

		def parse_tool_page(html, tool_class):
			return [{"id": f"{html}-tool", "tool_class": tool_class}]

		groups = {"slow": "first", "fast": "second"}
		with (
			patch.dict(scrape.TOOL_GROUPS, groups, clear=True),
			patch.object(scrape, "fetch_page_html", side_effect=fetch_page_html),
			patch.object(scrape, "parse_tool_page", side_effect=parse_tool_page),
			patch.object(scrape.asyncio, "sleep", return_value=None),
		):
			tools = await scrape.scrape_tools(object(), asyncio.Semaphore(2))

		self.assertEqual([tool["id"] for tool in tools], ["slow-tool", "fast-tool"])


if __name__ == "__main__":
	unittest.main()
