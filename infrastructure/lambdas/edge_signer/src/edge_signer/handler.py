from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qsl, quote

LOGGER = logging.getLogger(__name__)

ALGORITHM = "AWS4-HMAC-SHA256"
SERVICE = "lambda"
LAMBDA_FUNCTION_URL_HOST_PATTERN = re.compile(r"\.lambda-url\.([a-z0-9-]+)\.on\.aws\.?$")
VIEWER_HOST_HEADER = "X-Lynx-Viewer-Host"


@dataclass(frozen=True)
class AwsCredentials:
    access_key_id: str
    secret_access_key: str
    session_token: str | None = None

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> AwsCredentials:
        values = os.environ if environ is None else environ
        access_key_id = values.get("AWS_ACCESS_KEY_ID")
        secret_access_key = values.get("AWS_SECRET_ACCESS_KEY")

        if not access_key_id or not secret_access_key:
            raise RuntimeError("AWS credentials are required for Lambda Function URL signing")

        return cls(
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            session_token=values.get("AWS_SESSION_TOKEN"),
        )


class EdgeSigner:
    def __init__(
        self,
        credentials: AwsCredentials,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.credentials = credentials
        self.clock = clock or utc_now

    def handle(self, event: dict[str, Any], context: Any) -> dict[str, Any]:
        del context
        request = event["Records"][0]["cf"]["request"]
        self.sign_request(request)
        return request

    def sign_request(self, request: dict[str, Any]) -> None:
        viewer_host = get_header(request, "Host")
        host = extract_origin_host(request)
        region = extract_region_from_host(host)
        timestamp = self.clock().astimezone(UTC).replace(microsecond=0)
        amz_date = timestamp.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = timestamp.strftime("%Y%m%d")
        credential_scope = f"{date_stamp}/{region}/{SERVICE}/aws4_request"

        set_header(request, "Host", host)
        if viewer_host and viewer_host.lower() != host:
            set_header(request, VIEWER_HOST_HEADER, viewer_host)
        set_header(request, "X-Amz-Date", amz_date)

        signed_header_values = {
            "host": host,
            "x-amz-date": amz_date,
        }

        if self.credentials.session_token:
            set_header(request, "X-Amz-Security-Token", self.credentials.session_token)
            signed_header_values["x-amz-security-token"] = self.credentials.session_token

        signed_headers = ";".join(sorted(signed_header_values))
        canonical_request = build_canonical_request(
            method=request["method"],
            uri=request.get("uri", "/"),
            querystring=request.get("querystring", ""),
            signed_header_values=signed_header_values,
            signed_headers=signed_headers,
            payload_hash=hash_payload(request),
        )
        string_to_sign = build_string_to_sign(
            amz_date=amz_date,
            credential_scope=credential_scope,
            canonical_request=canonical_request,
        )
        signature = calculate_signature(
            secret_access_key=self.credentials.secret_access_key,
            date_stamp=date_stamp,
            region=region,
            string_to_sign=string_to_sign,
        )
        authorization = (
            f"{ALGORITHM} "
            f"Credential={self.credentials.access_key_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )

        set_header(request, "Authorization", authorization)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return EdgeSigner(AwsCredentials.from_env()).handle(event, context)


def utc_now() -> datetime:
    return datetime.now(UTC)


def extract_origin_host(request: dict[str, Any]) -> str:
    origin = request.get("origin", {})
    custom_origin = origin.get("custom", {})
    domain_name = custom_origin.get("domainName") or get_header(request, "Host")

    if not domain_name:
        raise ValueError("CloudFront request does not include an origin domain name")

    return domain_name.lower()


def extract_region_from_host(host: str) -> str:
    match = LAMBDA_FUNCTION_URL_HOST_PATTERN.search(host.lower())
    if not match:
        raise ValueError(f"Could not derive Lambda Function URL region from host: {host}")
    return match.group(1)


def build_canonical_request(
    *,
    method: str,
    uri: str,
    querystring: str,
    signed_header_values: dict[str, str],
    signed_headers: str,
    payload_hash: str,
) -> str:
    canonical_headers = "".join(
        f"{name}:{normalize_header_value(signed_header_values[name])}\n"
        for name in sorted(signed_header_values)
    )

    return "\n".join(
        [
            method.upper(),
            canonical_uri(uri),
            canonical_query_string(querystring),
            canonical_headers,
            signed_headers,
            payload_hash,
        ]
    )


def build_string_to_sign(
    *,
    amz_date: str,
    credential_scope: str,
    canonical_request: str,
) -> str:
    canonical_request_hash = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    return "\n".join([ALGORITHM, amz_date, credential_scope, canonical_request_hash])


def calculate_signature(
    *,
    secret_access_key: str,
    date_stamp: str,
    region: str,
    string_to_sign: str,
) -> str:
    signing_key = derive_signing_key(secret_access_key, date_stamp, region)
    return hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()


def derive_signing_key(secret_access_key: str, date_stamp: str, region: str) -> bytes:
    date_key = sign_bytes(f"AWS4{secret_access_key}".encode(), date_stamp)
    region_key = sign_bytes(date_key, region)
    service_key = sign_bytes(region_key, SERVICE)
    return sign_bytes(service_key, "aws4_request")


def sign_bytes(key: bytes, value: str) -> bytes:
    return hmac.new(key, value.encode("utf-8"), hashlib.sha256).digest()


def hash_payload(request: dict[str, Any]) -> str:
    return hashlib.sha256(request_body_bytes(request)).hexdigest()


def request_body_bytes(request: dict[str, Any]) -> bytes:
    body = request.get("body") or {}
    data = body.get("data")
    if not data:
        return b""

    encoding = body.get("encoding", "text")
    if encoding == "base64":
        return base64.b64decode(data)

    return data.encode("utf-8")


def canonical_uri(uri: str) -> str:
    value = uri or "/"
    if not value.startswith("/"):
        value = f"/{value}"
    return quote(value, safe="/-_.~")


def canonical_query_string(querystring: str) -> str:
    pairs = parse_qsl(querystring, keep_blank_values=True)
    encoded_pairs = [
        (quote(name, safe="-_.~"), quote(value, safe="-_.~")) for name, value in pairs
    ]
    return "&".join(f"{name}={value}" for name, value in sorted(encoded_pairs))


def normalize_header_value(value: str) -> str:
    return " ".join(value.strip().split())


def get_header(request: dict[str, Any], header_name: str) -> str | None:
    headers = request.get("headers", {})
    entries = headers.get(header_name.lower(), [])
    if not entries:
        return None
    return entries[0].get("value")


def set_header(request: dict[str, Any], header_name: str, value: str) -> None:
    request.setdefault("headers", {})[header_name.lower()] = [
        {
            "key": header_name,
            "value": value,
        }
    ]
