from __future__ import annotations

import base64
import json
import logging
import os
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote, urlsplit

LOGGER = logging.getLogger(__name__)

CODE_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
TTL_DAYS = {
    "24h": 1,
    "7d": 7,
}


class RequestError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class CollisionRetriesExhausted(Exception):
    pass


@dataclass(frozen=True)
class Config:
    redirect_bucket_name: str
    public_base_url: str
    alerts_topic_arn: str
    environment: str = "unknown"
    public_hosts: tuple[str, ...] = ()
    default_ttl: str = "24h"
    max_url_length: int = 2048
    code_length: int = 8
    max_code_attempts: int = 5

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> Config:
        values = os.environ if environ is None else environ
        required = ("REDIRECT_BUCKET_NAME", "PUBLIC_BASE_URL", "ALERTS_TOPIC_ARN")
        missing = [name for name in required if not values.get(name)]
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

        default_ttl = values.get("DEFAULT_TTL", "24h")
        if default_ttl not in TTL_DAYS:
            raise RuntimeError(f"DEFAULT_TTL must be one of: {', '.join(TTL_DAYS)}")

        public_base_url = values["PUBLIC_BASE_URL"].rstrip("/")
        public_hosts = tuple(
            host
            for host in (
                normalize_host(value) for value in values.get("PUBLIC_HOSTS", "").split(",")
            )
            if host
        )

        return cls(
            redirect_bucket_name=values["REDIRECT_BUCKET_NAME"],
            public_base_url=public_base_url,
            alerts_topic_arn=values["ALERTS_TOPIC_ARN"],
            environment=values.get("ENVIRONMENT", "unknown"),
            public_hosts=public_hosts,
            default_ttl=default_ttl,
            max_url_length=int(values.get("MAX_URL_LENGTH", "2048")),
            code_length=int(values.get("CODE_LENGTH", "8")),
            max_code_attempts=int(values.get("MAX_CODE_ATTEMPTS", "5")),
        )


class CreateLinkHandler:
    def __init__(
        self,
        config: Config,
        s3_client: Any,
        sns_client: Any,
        code_generator: Callable[[int], str] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.config = config
        self.s3_client = s3_client
        self.sns_client = sns_client
        self.code_generator = code_generator or generate_code
        self.clock = clock or utc_now

    def handle(self, event: dict[str, Any], context: Any) -> dict[str, Any]:
        try:
            method = get_method(event)
            if method != "POST":
                return json_response(
                    405,
                    {"error": "method not allowed"},
                    extra_headers={"Allow": "POST"},
                )

            path = get_path(event)
            if path != "/api/links":
                return json_response(404, {"error": "not found"})

            payload = parse_body(event)
            target_url = validate_url(payload.get("url"), self.config.max_url_length)
            ttl = validate_ttl(payload.get("ttl"), self.config.default_ttl)

            now = self.clock().astimezone(UTC).replace(microsecond=0)
            expires_at = now + timedelta(days=TTL_DAYS[ttl])
            code, object_key = self.create_redirect_object(target_url, ttl)
            public_base_url = resolve_public_base_url(event, self.config)
            short_url = f"{public_base_url}/l/{code}"

            self.publish_alert(
                event=event,
                context=context,
                code=code,
                object_key=object_key,
                short_url=short_url,
                target_url=target_url,
                ttl=ttl,
                created_at=now,
                nominal_expires_at=expires_at,
            )

            return json_response(
                201,
                {
                    "code": code,
                    "short_url": short_url,
                    "target_url": target_url,
                    "ttl": ttl,
                    "nominal_expires_at": format_timestamp(expires_at),
                },
            )
        except RequestError as error:
            return json_response(error.status_code, {"error": error.message})
        except CollisionRetriesExhausted:
            return json_response(409, {"error": "generated code collision retries exhausted"})
        except Exception:
            LOGGER.exception("Unexpected create-link failure")
            return json_response(500, {"error": "internal server error"})

    def create_redirect_object(self, target_url: str, ttl: str) -> tuple[str, str]:
        for _ in range(self.config.max_code_attempts):
            code = self.code_generator(self.config.code_length)
            object_key = f"l/{code}"
            if self.object_exists(object_key):
                continue

            self.s3_client.put_object(
                Bucket=self.config.redirect_bucket_name,
                Key=object_key,
                Body=b"",
                ContentType="text/plain",
                WebsiteRedirectLocation=target_url,
                Tagging=f"ttl={quote(ttl, safe='')}",
            )
            return code, object_key

        raise CollisionRetriesExhausted()

    def object_exists(self, object_key: str) -> bool:
        try:
            self.s3_client.head_object(Bucket=self.config.redirect_bucket_name, Key=object_key)
            return True
        except Exception as error:
            if is_not_found_error(error):
                return False
            raise

    def publish_alert(
        self,
        *,
        event: dict[str, Any],
        context: Any,
        code: str,
        object_key: str,
        short_url: str,
        target_url: str,
        ttl: str,
        created_at: datetime,
        nominal_expires_at: datetime,
    ) -> None:
        headers = normalize_headers(event.get("headers") or {})
        request_context = event.get("requestContext", {})
        http_context = request_context.get("http", {})
        forwarded_for = headers.get("x-forwarded-for", "")
        requester_ip = forwarded_for.split(",", 1)[0].strip() or http_context.get("sourceIp")

        message = {
            "event_type": "link_created",
            "environment": self.config.environment,
            "short_code": code,
            "short_url": short_url,
            "target_url": target_url,
            "ttl": ttl,
            "nominal_expires_at": format_timestamp(nominal_expires_at),
            "redirect_bucket_name": self.config.redirect_bucket_name,
            "redirect_object_key": object_key,
            "requester_ip": requester_ip,
            "user_agent": headers.get("user-agent") or http_context.get("userAgent"),
            "referer": headers.get("referer") or headers.get("referrer"),
            "cloudfront_request_id": headers.get("x-amz-cf-id"),
            "lambda_request_id": getattr(context, "aws_request_id", None),
            "created_at": format_timestamp(created_at),
        }

        self.sns_client.publish(
            TopicArn=self.config.alerts_topic_arn,
            Subject=f"Lynx link created: {code}",
            Message=json.dumps(message, sort_keys=True),
        )


def build_runtime_handler() -> CreateLinkHandler:
    import boto3

    return CreateLinkHandler(
        config=Config.from_env(),
        s3_client=boto3.client("s3"),
        sns_client=boto3.client("sns"),
    )


_RUNTIME_HANDLER: CreateLinkHandler | None = None


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    global _RUNTIME_HANDLER
    if _RUNTIME_HANDLER is None:
        _RUNTIME_HANDLER = build_runtime_handler()
    return _RUNTIME_HANDLER.handle(event, context)


def generate_code(length: int) -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(length))


def utc_now() -> datetime:
    return datetime.now(UTC)


def get_method(event: dict[str, Any]) -> str:
    request_context = event.get("requestContext", {})
    http_context = request_context.get("http", {})
    return (http_context.get("method") or event.get("httpMethod") or "").upper()


def get_path(event: dict[str, Any]) -> str:
    request_context = event.get("requestContext", {})
    http_context = request_context.get("http", {})
    return event.get("rawPath") or http_context.get("path") or event.get("path") or ""


def parse_body(event: dict[str, Any]) -> dict[str, Any]:
    raw_body = event.get("body")
    if raw_body is None:
        raise RequestError(400, "request body is required")

    if event.get("isBase64Encoded"):
        try:
            raw_body = base64.b64decode(raw_body).decode("utf-8")
        except Exception as error:
            raise RequestError(400, "request body must be valid base64") from error

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as error:
        raise RequestError(400, "request body must be valid JSON") from error

    if not isinstance(payload, dict):
        raise RequestError(400, "request body must be a JSON object")

    return payload


def validate_url(value: Any, max_url_length: int) -> str:
    if value is None:
        raise RequestError(400, "url is required")

    if not isinstance(value, str):
        raise RequestError(400, "url must be a string")

    target_url = value.strip()
    if not target_url:
        raise RequestError(400, "url is required")

    if len(target_url) > max_url_length:
        raise RequestError(400, f"url must be {max_url_length} characters or fewer")

    try:
        parsed = urlsplit(target_url)
        hostname = parsed.hostname
    except ValueError as error:
        raise RequestError(400, "url is malformed") from error

    if not parsed.scheme or not parsed.netloc:
        raise RequestError(400, "url must be absolute")

    if parsed.scheme.lower() != "https":
        raise RequestError(400, "url must use the https scheme")

    if not hostname:
        raise RequestError(400, "url must include a hostname")

    return target_url


def validate_ttl(value: Any, default_ttl: str) -> str:
    ttl = default_ttl if value is None else value
    if not isinstance(ttl, str) or ttl not in TTL_DAYS:
        raise RequestError(400, "ttl must be one of: 24h, 7d")
    return ttl


def resolve_public_base_url(event: dict[str, Any], config: Config) -> str:
    headers = normalize_headers(event.get("headers") or {})
    allowed_hosts = allowed_public_hosts(config)
    candidate_hosts = [
        normalize_host(headers.get("x-lynx-viewer-host")),
        host_from_https_url(headers.get("origin")),
        host_from_https_url(headers.get("referer") or headers.get("referrer")),
    ]

    for host in candidate_hosts:
        if host and host in allowed_hosts:
            return f"https://{host}"

    return config.public_base_url


def allowed_public_hosts(config: Config) -> set[str]:
    if config.public_hosts:
        return set(config.public_hosts)

    host = host_from_https_url(config.public_base_url)
    return {host} if host else set()


def host_from_https_url(value: str | None) -> str | None:
    if not value:
        return None

    try:
        parsed = urlsplit(value.strip())
    except ValueError:
        return None

    if parsed.scheme.lower() != "https":
        return None

    return normalize_host(parsed.hostname)


def normalize_host(value: str | None) -> str | None:
    if not value:
        return None

    try:
        parsed = urlsplit(f"//{value.strip()}")
    except ValueError:
        return None

    return parsed.hostname.lower() if parsed.hostname else None


def is_not_found_error(error: Exception) -> bool:
    response = getattr(error, "response", {})
    error_info = response.get("Error", {})
    metadata = response.get("ResponseMetadata", {})
    code = str(error_info.get("Code", ""))
    status = metadata.get("HTTPStatusCode")
    return status == 404 or code in {"404", "NoSuchKey", "NotFound"}


def normalize_headers(headers: dict[str, Any]) -> dict[str, str]:
    return {str(key).lower(): str(value) for key, value in headers.items() if value is not None}


def json_response(
    status_code: int,
    body: dict[str, Any],
    *,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-store",
    }
    if extra_headers:
        headers.update(extra_headers)

    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body, sort_keys=True),
    }


def format_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
