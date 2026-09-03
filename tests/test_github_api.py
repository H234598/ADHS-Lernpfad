from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import github_api
from github_api import request_json


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
        response = Mock(status=200)
        response.read.return_value = b'{"ok": true}'
        connection = Mock()
        connection.getresponse.return_value = response

        with patch.object(
            github_api,
            "HTTPSConnection",
            return_value=connection,
        ) as connection_factory:
            payload = request_json(
                "https://api.github.com/repos/example/repo?per_page=10",
                "token",
                user_agent="test",
            )

        self.assertEqual(payload, {"ok": True})
        connection_factory.assert_called_once_with(
            "api.github.com", 443, timeout=30
        )
        connection.request.assert_called_once()
        method, path = connection.request.call_args.args[:2]
        self.assertEqual(method, "GET")
        self.assertEqual(path, "/repos/example/repo?per_page=10")
        connection.close.assert_called_once()

    def test_non_success_response_fails_with_bounded_body(self) -> None:
        response = Mock(status=403)
        response.read.return_value = b"forbidden"
        connection = Mock()
        connection.getresponse.return_value = response

        with (
            patch.object(
                github_api,
                "HTTPSConnection",
                return_value=connection,
            ),
            self.assertRaisesRegex(RuntimeError, "GitHub API 403"),
        ):
            request_json(
                "https://api.github.com/repos/example/repo",
                "token",
                user_agent="test",
            )


if __name__ == "__main__":
    unittest.main()
