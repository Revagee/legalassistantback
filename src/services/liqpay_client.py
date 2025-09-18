import os
import json
import base64
import hashlib
from typing import Any
import httpx


def _b64_encode(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")


def _generate_signature(private_key: str, data_b64: str) -> str:
    signature_raw = f"{private_key}{data_b64}{private_key}".encode("utf-8")
    sha1_digest = hashlib.sha1(signature_raw).digest()
    return _b64_encode(sha1_digest)


def _prepare_request_payload(
    payload: dict[str, Any], public_key: str, private_key: str
) -> dict[str, str]:
    payload.update(public_key=public_key)

    json_str = json.dumps(payload, ensure_ascii=False)
    data_b64 = _b64_encode(json_str.encode("utf-8"))
    signature = _generate_signature(private_key, data_b64)
    return {"data": data_b64, "signature": signature}


async def liqpay_request(
    payload: dict[str, Any],
    *,
    endpoint_url: str | None = None,
    timeout_seconds: float = 15.0,
) -> dict[str, Any]:
    """
    Send an async request to LiqPay's API using httpx.

    Args:
        payload: Raw LiqPay payload (e.g., {"action": "subscribe", "version": "3", ...}).
        public_key: LiqPay public key. If None, read from env LIQPAY_PUBLIC_KEY.
        private_key: LiqPay private key. If None, read from env LIQPAY_PRIVATE_KEY.
        endpoint_url: Override API URL. Defaults to production request endpoint.
        timeout_seconds: HTTP timeout.

    Returns:
        Parsed JSON response from LiqPay.
    """

    public_key = os.getenv("LIQPAY_PUBLIC_KEY")
    private_key = os.getenv("LIQPAY_PRIVATE_KEY")
    if not public_key or not private_key:
        raise RuntimeError("LiqPay keys are not configured")

    # Default endpoint for LiqPay request API
    url = endpoint_url or "https://www.liqpay.ua/api/request"

    form = _prepare_request_payload(payload, public_key, private_key)

    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        response = await client.post(url, data=form)
        response.raise_for_status()
        return response.json()
