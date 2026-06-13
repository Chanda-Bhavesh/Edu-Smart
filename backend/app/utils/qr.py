import io
import uuid
import base64
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config import settings

_QR_TTL_MINUTES = 10
_QR_TOKEN_TYPE  = "qr_attendance"


def create_qr_token(course_assignment_id: str, faculty_id: str, session_date: str) -> str:
    """Create a signed JWT embedded inside a QR code. Valid for 10 minutes."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=_QR_TTL_MINUTES)
    payload = {
        "type":                 _QR_TOKEN_TYPE,
        "course_assignment_id": course_assignment_id,
        "faculty_id":           faculty_id,
        "date":                 session_date,        # YYYY-MM-DD
        "jti":                  str(uuid.uuid4()),
        "exp":                  expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_qr_token(token: str) -> dict:
    """
    Decode and validate the QR token.
    Raises jose.JWTError on invalid or expired token.
    """
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != _QR_TOKEN_TYPE:
        raise JWTError("Not a QR attendance token")
    return payload


def generate_qr_image_base64(token: str) -> str:
    """
    Generate a QR code image for the token and return it as a base64 PNG string
    so the frontend can render it directly: <img src="data:image/png;base64,...">
    """
    try:
        import qrcode
        from PIL import Image

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(token)
        qr.make(fit=True)
        img: Image.Image = qr.make_image(fill_color="black", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode("utf-8")

    except ImportError:
        # qrcode / pillow not installed — return the raw token as fallback
        return base64.b64encode(token.encode()).decode("utf-8")
