import base64
import hashlib
import hmac

from app.integrations.line import verify_signature
from app.services.matching import circular_month_distance, normalize_name


def test_hospital_normalization() -> None:
    assert normalize_name(" รพ. กรุงเทพ-เหนือ ") == normalize_name("โรงพยาบาลกรุงเทพ เหนือ")


def test_circular_month_distance() -> None:
    assert circular_month_distance(12, 1) == 1
    assert circular_month_distance(10, 1) == 3


def test_line_signature_validation() -> None:
    body = b'{"events":[]}'
    secret = "secret"
    signature = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
    assert verify_signature(body, signature, secret)
    assert not verify_signature(body + b"x", signature, secret)

