import json
import unittest

from build import _materially_changed


def encoded(payload: dict) -> bytes:
	return json.dumps(payload).encode()


class MaterialChangeTests(unittest.TestCase):
	def test_ignores_scrape_timestamp(self) -> None:
		previous = {"meta": {"scraped_at": "before"}, "tools": [{"id": "knife"}]}
		current = {"meta": {"scraped_at": "after"}, "tools": [{"id": "knife"}]}

		self.assertFalse(_materially_changed(encoded(previous), encoded(current)))

	def test_detects_reordered_items(self) -> None:
		previous = {
			"meta": {"scraped_at": "before"},
			"tools": [{"id": "knife"}, {"id": "fusees"}],
		}
		current = {
			"meta": {"scraped_at": "after"},
			"tools": [{"id": "fusees"}, {"id": "knife"}],
		}

		self.assertTrue(_materially_changed(encoded(previous), encoded(current)))


if __name__ == "__main__":
	unittest.main()
