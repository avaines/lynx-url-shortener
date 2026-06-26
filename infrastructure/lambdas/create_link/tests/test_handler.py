from __future__ import annotations

import json
import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from create_link.handler import Config, CreateLinkHandler

FIXED_NOW = datetime(2026, 6, 26, 12, 0, 0, tzinfo=UTC)


class FakeClientError(Exception):
    def __init__(self, code: str, status_code: int) -> None:
        super().__init__(code)
        self.response = {
            "Error": {"Code": code},
            "ResponseMetadata": {"HTTPStatusCode": status_code},
        }


class FakeS3Client:
    def __init__(self, existing_keys: set[str] | None = None) -> None:
        self.existing_keys = set(existing_keys or set())
        self.head_calls: list[dict[str, Any]] = []
        self.put_calls: list[dict[str, Any]] = []

    def head_object(self, **kwargs: Any) -> dict[str, Any]:
        self.head_calls.append(kwargs)
        if kwargs["Key"] in self.existing_keys:
            return {}
        raise FakeClientError("404", 404)

    def put_object(self, **kwargs: Any) -> dict[str, Any]:
        self.put_calls.append(kwargs)
        self.existing_keys.add(kwargs["Key"])
        return {}


class FakeSnsClient:
    def __init__(self) -> None:
        self.publish_calls: list[dict[str, Any]] = []

    def publish(self, **kwargs: Any) -> dict[str, Any]:
        self.publish_calls.append(kwargs)
        return {"MessageId": "message-1"}


class CodeSequence:
    def __init__(self, *codes: str) -> None:
        self.codes = list(codes)

    def __call__(self, length: int) -> str:
        del length
        return self.codes.pop(0)


class CreateLinkHandlerTests(unittest.TestCase):
    def make_config(self, **overrides: Any) -> Config:
        values = {
            "redirect_bucket_name": "redirect-bucket",
            "public_base_url": "https://lynx.example.com",
            "alerts_topic_arn": "arn:aws:sns:us-east-1:123456789012:alerts",
            "environment": "test",
            "default_ttl": "24h",
            "max_url_length": 2048,
            "code_length": 8,
            "max_code_attempts": 5,
        }
        values.update(overrides)
        return Config(**values)

    def make_handler(
        self,
        *,
        config: Config | None = None,
        s3_client: FakeS3Client | None = None,
        sns_client: FakeSnsClient | None = None,
        codes: tuple[str, ...] = ("aB3kP9xQ",),
    ) -> tuple[CreateLinkHandler, FakeS3Client, FakeSnsClient]:
        s3 = s3_client or FakeS3Client()
        sns = sns_client or FakeSnsClient()
        handler = CreateLinkHandler(
            config=config or self.make_config(),
            s3_client=s3,
            sns_client=sns,
            code_generator=CodeSequence(*codes),
            clock=lambda: FIXED_NOW,
        )
        return handler, s3, sns

    def make_event(
        self,
        body: dict[str, Any] | str,
        *,
        method: str = "POST",
        path: str = "/api/links",
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return {
            "version": "2.0",
            "rawPath": path,
            "headers": headers
            or {
                "x-forwarded-for": "203.0.113.10, 70.132.1.1",
                "user-agent": "UnitTest/1.0",
                "referer": "https://lynx.example.com/",
                "x-amz-cf-id": "cloudfront-request-1",
            },
            "requestContext": {
                "requestId": "function-url-request-1",
                "http": {
                    "method": method,
                    "path": path,
                    "sourceIp": "198.51.100.20",
                    "userAgent": "FallbackAgent/1.0",
                },
            },
            "body": body if isinstance(body, str) else json.dumps(body),
            "isBase64Encoded": False,
        }

    def invoke(
        self,
        handler: CreateLinkHandler,
        event: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        response = handler.handle(event, SimpleNamespace(aws_request_id="lambda-request-1"))
        try:
            body = json.loads(response["body"])
        except json.JSONDecodeError as error:
            self.fail(f"response body was not valid JSON: {error}")
        return response, body

    def test_successful_24h_link_creation(self) -> None:
        handler, s3, sns = self.make_handler()

        response, body = self.invoke(
            handler,
            self.make_event({"url": "https://example.com/some/long/path", "ttl": "24h"}),
        )

        self.assertEqual(response["statusCode"], 201)
        self.assertEqual(body["code"], "aB3kP9xQ")
        self.assertEqual(body["short_url"], "https://lynx.example.com/l/aB3kP9xQ")
        self.assertEqual(body["target_url"], "https://example.com/some/long/path")
        self.assertEqual(body["ttl"], "24h")
        self.assertEqual(body["nominal_expires_at"], "2026-06-27T12:00:00Z")
        self.assertEqual(s3.put_calls[0]["Bucket"], "redirect-bucket")
        self.assertEqual(s3.put_calls[0]["Key"], "l/aB3kP9xQ")
        self.assertEqual(sns.publish_calls[0]["TopicArn"], handler.config.alerts_topic_arn)

    def test_successful_7d_link_creation(self) -> None:
        handler, _, _ = self.make_handler(codes=("7DayCode",))

        response, body = self.invoke(
            handler,
            self.make_event({"url": "https://example.com/resource", "ttl": "7d"}),
        )

        self.assertEqual(response["statusCode"], 201)
        self.assertEqual(body["ttl"], "7d")
        self.assertEqual(body["nominal_expires_at"], "2026-07-03T12:00:00Z")

    def test_missing_ttl_defaults_to_24h(self) -> None:
        handler, s3, _ = self.make_handler()

        response, body = self.invoke(
            handler,
            self.make_event({"url": "https://example.com/default-ttl"}),
        )

        self.assertEqual(response["statusCode"], 201)
        self.assertEqual(body["ttl"], "24h")
        self.assertEqual(s3.put_calls[0]["Tagging"], "ttl=24h")

    def test_missing_url_returns_400(self) -> None:
        handler, _, _ = self.make_handler()

        response, body = self.invoke(handler, self.make_event({"ttl": "24h"}))

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(body["error"], "url is required")

    def test_non_string_url_returns_400(self) -> None:
        handler, _, _ = self.make_handler()

        response, body = self.invoke(handler, self.make_event({"url": 123, "ttl": "24h"}))

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(body["error"], "url must be a string")

    def test_relative_url_returns_400(self) -> None:
        handler, _, _ = self.make_handler()

        response, body = self.invoke(handler, self.make_event({"url": "/relative", "ttl": "24h"}))

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(body["error"], "url must be absolute")

    def test_http_url_returns_400(self) -> None:
        handler, _, _ = self.make_handler()

        response, body = self.invoke(
            handler,
            self.make_event({"url": "http://example.com", "ttl": "24h"}),
        )

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(body["error"], "url must use the https scheme")

    def test_url_with_no_hostname_returns_400(self) -> None:
        handler, _, _ = self.make_handler()

        response, body = self.invoke(handler, self.make_event({"url": "https://@", "ttl": "24h"}))

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(body["error"], "url must include a hostname")

    def test_over_length_url_returns_400(self) -> None:
        handler, _, _ = self.make_handler(config=self.make_config(max_url_length=20))

        response, body = self.invoke(
            handler,
            self.make_event({"url": "https://example.com/too-long", "ttl": "24h"}),
        )

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(body["error"], "url must be 20 characters or fewer")

    def test_invalid_ttl_returns_400(self) -> None:
        handler, _, _ = self.make_handler()

        response, body = self.invoke(
            handler,
            self.make_event({"url": "https://example.com", "ttl": "30d"}),
        )

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(body["error"], "ttl must be one of: 24h, 7d")

    def test_unsupported_method_returns_405(self) -> None:
        handler, s3, sns = self.make_handler()

        response, body = self.invoke(
            handler,
            self.make_event({"url": "https://example.com"}, method="GET"),
        )

        self.assertEqual(response["statusCode"], 405)
        self.assertEqual(response["headers"]["Allow"], "POST")
        self.assertEqual(body["error"], "method not allowed")
        self.assertEqual(s3.put_calls, [])
        self.assertEqual(sns.publish_calls, [])

    def test_collision_retry_behavior(self) -> None:
        existing_key = "l/firstOne"
        handler, s3, _ = self.make_handler(
            s3_client=FakeS3Client(existing_keys={existing_key}),
            codes=("firstOne", "nextCode"),
        )

        response, body = self.invoke(handler, self.make_event({"url": "https://example.com"}))

        self.assertEqual(response["statusCode"], 201)
        self.assertEqual(body["code"], "nextCode")
        self.assertEqual([call["Key"] for call in s3.head_calls], ["l/firstOne", "l/nextCode"])
        self.assertEqual(s3.put_calls[0]["Key"], "l/nextCode")

    def test_collision_retry_exhaustion_returns_409(self) -> None:
        handler, s3, sns = self.make_handler(
            config=self.make_config(max_code_attempts=2),
            s3_client=FakeS3Client(existing_keys={"l/firstOne", "l/secondOn"}),
            codes=("firstOne", "secondOn"),
        )

        response, body = self.invoke(handler, self.make_event({"url": "https://example.com"}))

        self.assertEqual(response["statusCode"], 409)
        self.assertEqual(body["error"], "generated code collision retries exhausted")
        self.assertEqual(s3.put_calls, [])
        self.assertEqual(sns.publish_calls, [])

    def test_s3_put_object_metadata_and_tags(self) -> None:
        handler, s3, _ = self.make_handler()

        response, _ = self.invoke(
            handler,
            self.make_event({"url": "https://example.com/redirect-target", "ttl": "7d"}),
        )

        self.assertEqual(response["statusCode"], 201)
        self.assertEqual(s3.put_calls[0]["Body"], b"")
        self.assertEqual(s3.put_calls[0]["ContentType"], "text/plain")
        self.assertEqual(
            s3.put_calls[0]["WebsiteRedirectLocation"],
            "https://example.com/redirect-target",
        )
        self.assertEqual(s3.put_calls[0]["Tagging"], "ttl=7d")

    def test_sns_payload_includes_required_fields(self) -> None:
        handler, _, sns = self.make_handler()

        response, _ = self.invoke(
            handler,
            self.make_event({"url": "https://example.com/alert", "ttl": "24h"}),
        )

        self.assertEqual(response["statusCode"], 201)
        message = json.loads(sns.publish_calls[0]["Message"])
        self.assertEqual(message["event_type"], "link_created")
        self.assertEqual(message["environment"], "test")
        self.assertEqual(message["short_code"], "aB3kP9xQ")
        self.assertEqual(message["short_url"], "https://lynx.example.com/l/aB3kP9xQ")
        self.assertEqual(message["target_url"], "https://example.com/alert")
        self.assertEqual(message["ttl"], "24h")
        self.assertEqual(message["nominal_expires_at"], "2026-06-27T12:00:00Z")
        self.assertEqual(message["redirect_bucket_name"], "redirect-bucket")
        self.assertEqual(message["redirect_object_key"], "l/aB3kP9xQ")
        self.assertEqual(message["requester_ip"], "203.0.113.10")
        self.assertEqual(message["user_agent"], "UnitTest/1.0")
        self.assertEqual(message["referer"], "https://lynx.example.com/")
        self.assertEqual(message["cloudfront_request_id"], "cloudfront-request-1")
        self.assertEqual(message["lambda_request_id"], "lambda-request-1")
        self.assertEqual(message["created_at"], "2026-06-26T12:00:00Z")


if __name__ == "__main__":
    unittest.main()
