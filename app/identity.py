"""Validate Google's signed IAP assertion, never a client supplied email header."""

import threading

import jwt

IAP_KEYS_URL = "https://www.gstatic.com/iap/verify/public_key-jwk"
IAP_ISSUER = "https://cloud.google.com/iap"


class IdentityError(Exception):
    """The request does not carry an acceptable IAP identity."""


class IAPVerifier:
    def __init__(self, audience, key_client=None):
        self.audience = audience
        self.key_client = key_client or jwt.PyJWKClient(
            IAP_KEYS_URL, cache_jwk_set=True, lifespan=300, timeout=5
        )
        self._key_lock = threading.Lock()

    def __call__(self, token):
        if not token or len(token) > 16384:
            raise IdentityError("Missing or oversized assertion")
        try:
            header = jwt.get_unverified_header(token)
            if header.get("alg") != "ES256" or not isinstance(header.get("kid"), str):
                raise IdentityError("Unsupported assertion header")
            # The public key URL is fixed here, never obtained from token headers.
            with self._key_lock:
                key = self.key_client.get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                key,
                algorithms=["ES256"],
                audience=self.audience,
                issuer=IAP_ISSUER,
                leeway=30,
                options={"require": ["exp", "iat", "aud", "iss", "sub"], "strict_aud": True},
            )
            issued, expiry = claims["iat"], claims["exp"]
            if (
                not isinstance(issued, (int, float))
                or isinstance(issued, bool)
                or not isinstance(expiry, (int, float))
                or isinstance(expiry, bool)
                or not 0 < expiry - issued <= 660
                or not isinstance(claims["sub"], str)
                or not claims["sub"]
            ):
                raise IdentityError("Invalid assertion claims")
            return claims
        except (jwt.PyJWTError, OSError, ValueError, TypeError) as exc:
            # Never put the token, email, claims or remote error body in logs.
            raise IdentityError("Invalid assertion") from exc
