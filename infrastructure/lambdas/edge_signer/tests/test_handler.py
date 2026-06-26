from __future__ import annotations

import base64
import copy
import re
import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from edge_signer.handler import AwsCredentials, EdgeSigner

FIXED_NOW = datetime(2026, 6, 26, 12, 0, 0, tzinfo=UTC)
LAMBDA_URL_HOST = "abc123lambdaurl.lambda-url.us-east-1.on.aws"


class EdgeSignerTests(unittest.TestCase):
    def make_signer(
        self,
        *,
        session_token: str | None = "session-token",
    ) -> EdgeSigner:
        return EdgeSigner(
            credentials=AwsCredentials(
                access_key_id="AKIDEXAMPLE",
                secret_access_key="wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY",
                session_token=session_token,
            ),
            clock=lambda: FIXED_NOW,
        )

    def make_event(
        self,
        *,
        method: str = "POST",
        uri: str = "/api/links",
        querystring: str = "ttl=24h&source=portal",
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        request: dict[str, Any] = {
            "method": method,
            "uri": uri,
            "querystring": querystring,
            "headers": {
                "host": [
                    {
                        "key": "Host",
                        "value": "lynx.example.com",
                    }
                ],
                "content-type": [
                    {
                        "key": "Content-Type",
                        "value": "application/json",
                    }
                ],
            },
            "origin": {
                "custom": {
                    "domainName": LAMBDA_URL_HOST,
                    "port": 443,
                    "protocol": "https",
                    "path": "",
                    "sslProtocols": ["TLSv1.2"],
                    "readTimeout": 30,
                    "keepaliveTimeout": 5,
                    "customHeaders": {},
                }
            },
        }

        if body is not None:
            request["body"] = {
                "action": "read-only",
                "encoding": "base64",
                "inputTruncated": False,
                "data": base64.b64encode(b'{"url":"https://example.com"}').decode("utf-8"),
            }

        return {"Records": [{"cf": {"request": request}}]}

    def signed_request(
        self,
        event: dict[str, Any],
        *,
        session_token: str | None = "session-token",
    ) -> dict[str, Any]:
        return self.make_signer(session_token=session_token).handle(
            event,
            SimpleNamespace(aws_request_id="edge-request-1"),
        )

    def header_value(self, request: dict[str, Any], header_name: str) -> str:
        return request["headers"][header_name.lower()][0]["value"]

    def test_sigv4_authorization_headers_are_added(self) -> None:
        request = self.signed_request(self.make_event(body={"url": "https://example.com"}))

        authorization = self.header_value(request, "Authorization")

        self.assertEqual(self.header_value(request, "Host"), LAMBDA_URL_HOST)
        self.assertEqual(self.header_value(request, "X-Lynx-Viewer-Host"), "lynx.example.com")
        self.assertEqual(self.header_value(request, "X-Amz-Date"), "20260626T120000Z")
        self.assertTrue(authorization.startswith("AWS4-HMAC-SHA256 Credential=AKIDEXAMPLE/"))
        self.assertIn("/20260626/us-east-1/lambda/aws4_request", authorization)
        self.assertIn("SignedHeaders=host;x-amz-date;x-amz-security-token", authorization)
        self.assertRegex(authorization, r"Signature=[0-9a-f]{64}$")

    def test_method_path_and_query_string_are_preserved(self) -> None:
        event = self.make_event(
            method="POST",
            uri="/api/links",
            querystring="z=last&a=first&a=second",
            body={"url": "https://example.com"},
        )
        original_request = copy.deepcopy(event["Records"][0]["cf"]["request"])

        request = self.signed_request(event)

        self.assertEqual(request["method"], original_request["method"])
        self.assertEqual(request["uri"], original_request["uri"])
        self.assertEqual(request["querystring"], original_request["querystring"])

    def test_body_preservation_for_post_requests(self) -> None:
        event = self.make_event(body={"url": "https://example.com"})
        original_body = copy.deepcopy(event["Records"][0]["cf"]["request"]["body"])

        request = self.signed_request(event)

        self.assertEqual(request["body"], original_body)

    def test_temporary_credentials_include_security_token(self) -> None:
        request = self.signed_request(
            self.make_event(body={"url": "https://example.com"}),
            session_token="temporary-session-token",
        )

        self.assertEqual(
            self.header_value(request, "X-Amz-Security-Token"),
            "temporary-session-token",
        )
        self.assertIn(
            "SignedHeaders=host;x-amz-date;x-amz-security-token",
            self.header_value(request, "Authorization"),
        )

    def test_signing_without_session_token_omits_security_token(self) -> None:
        request = self.signed_request(self.make_event(), session_token=None)

        self.assertNotIn("x-amz-security-token", request["headers"])
        self.assertIn(
            "SignedHeaders=host;x-amz-date",
            self.header_value(request, "Authorization"),
        )

    def test_authorization_values_are_not_logged(self) -> None:
        event = self.make_event(body={"url": "https://example.com"})

        with self.assertNoLogs("edge_signer.handler", level="INFO"):
            request = self.signed_request(event)

        authorization = self.header_value(request, "Authorization")
        self.assertIsNotNone(re.search(r"Signature=[0-9a-f]{64}$", authorization))


if __name__ == "__main__":
    unittest.main()
