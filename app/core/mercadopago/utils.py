import hashlib
import hmac
import mercadopago
from app.core.mercadopago.config import mp_settings


def get_mp_sdk() -> mercadopago.SDK:
    return mercadopago.SDK(mp_settings.MP_ACCESS_TOKEN)


def verify_mp_signature(
    x_signature: str | None, x_request_id: str | None, data_id: str | None
) -> bool:
    if not x_signature or not x_request_id or not data_id:
        return False

    parts = dict(
        part.strip().split("=", 1) for part in x_signature.split(",") if "=" in part
    )
    ts = parts.get("ts", "").strip()
    received_hash = parts.get("v1", "").strip()

    if not ts or not received_hash:
        return False

    manifest = f"id:{data_id};request-id:{x_request_id};ts:{ts};"

    expected_hash = hmac.new(
        key=mp_settings.MP_WEBHOOK_SECRET.encode("utf-8"),
        msg=manifest.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_hash, received_hash)
