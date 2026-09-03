from __future__ import annotations

from io import BytesIO
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import github_api
from github_api import request_json


class _Response(BytesIO):
    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class GitHubApiTests(unittest.TestCase):
    def test_rejects_non_https_url(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "unerwartetes Ziel"):
            request_json(
                "http://api.github.com/repos/example/repo",
                "token",
                user_agent="test",
            )

    def test_rejects_non_github_host(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "unerwartetes Ziel"):
            request_json(
                "https://example.invalid/repos/example/repo",
                "token",
                user_agent="test",
            )

    def test_allows_canonical_github_api_host(self) -> None:
        response = _Response(b'{"ok": true}')
        with patch.object(github_api, "urlopen", return_value=response) as opener:
            payload = request_json(
                "https://api.github.com/repos/example/repo",
                "token",
                user_agent="test",
            )

        self.assertEqual(payload, {"ok": True})
        request = opener.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.github.com/repos/example/repo")
        self.assertEqual(request.get_method(), "GET")


if __name__ == "__main__":
    unittest.main()
