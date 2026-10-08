"""Managed OIDC token verification for the commercial API."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from typing import Any
from urllib.parse import urlsplit

import jwt


class AuthenticationDenied(PermissionError):
    """A generic authentication failure safe to translate at the API edge."""


class IdentityConfigurationError(RuntimeError):
    """The server-side identity configuration is missing or unsafe."""


class IdentityProviderUnavailable(RuntimeError):
    """The configured identity provider could not supply verification keys."""


@dataclass(frozen=True)
class OIDCSettings:
    issuer: str
    audience: str
    jwks_url: str
    max_token_age_seconds: int = 3600
    clock_skew_seconds: int = 30

    @classmethod
    def from_env(cls) -> "OIDCSettings":
        issuer = os.getenv("BIZPILOT_OIDC_ISSUER", "").strip()
        audience = os.getenv("BIZPILOT_OIDC_AUDIENCE", "").strip()
        jwks_url = os.getenv("BIZPILOT_OIDC_JWKS_URL", "").strip()
        if not issuer or not audience or not jwks_url:
            raise IdentityConfigurationError("OIDC configuration is incomplete.")
        try:
            max_age = int(os.getenv("BIZPILOT_OIDC_MAX_TOKEN_AGE_SECONDS", "3600"))
            clock_skew = int(os.getenv("BIZPILOT_OIDC_CLOCK_SKEW_SECONDS", "30"))
        except ValueError as error:
            raise IdentityConfigurationError("OIDC timing configuration is invalid.") from error
        settings = cls(issuer, audience, jwks_url, max_age, clock_skew)
        settings.validate()
        return settings

    def validate(self) -> None:
        for label, value in (("issuer", self.issuer), ("JWKS URL", self.jwks_url)):
            parsed = urlsplit(value)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
                or len(value) > 2048
            ):
                raise IdentityConfigurationError(f"OIDC {label} must be an HTTPS URL.")
        if len(self.issuer) > 512:
            raise IdentityConfigurationError("OIDC issuer is invalid.")
        if not self.audience or len(self.audience) > 512:
            raise IdentityConfigurationError("OIDC audience is invalid.")
        if not 60 <= self.max_token_age_seconds <= 86400:
            raise IdentityConfigurationError("OIDC maximum token age is invalid.")
        if not 0 <= self.clock_skew_seconds <= 300:
            raise IdentityConfigurationError("OIDC clock skew is invalid.")


@dataclass(frozen=True)
class VerifiedIdentity:
    issuer: str
    subject: str
    issued_at: datetime
    expires_at: datetime


SigningKeyResolver = Callable[[str], Any]


class OIDCVerifier:
    """Verify bearer tokens without accepting algorithms from token claims."""

    def __init__(
        self,
        settings: OIDCSettings,
        signing_key_resolver: SigningKeyResolver | None = None,
    ) -> None:
        settings.validate()
        self.settings = settings
        if signing_key_resolver is None:
            client = jwt.PyJWKClient(
                settings.jwks_url,
                cache_keys=True,
                max_cached_keys=16,
                cache_jwk_set=True,
                lifespan=300,
                timeout=5,
            )
            signing_key_resolver = lambda token: client.get_signing_key_from_jwt(token).key
        self._signing_key_resolver = signing_key_resolver

    def verify(self, token: str) -> VerifiedIdentity:
        if not token or len(token) > 8192:
            raise AuthenticationDenied("Invalid authentication token.")
        try:
            key = self._signing_key_resolver(token)
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.settings.audience,
                issuer=self.settings.issuer,
                leeway=self.settings.clock_skew_seconds,
                options={"require": ["exp", "iat", "iss", "sub", "aud"]},
            )
            subject = claims["sub"]
            issued_at = datetime.fromtimestamp(claims["iat"], tz=timezone.utc)
            expires_at = datetime.fromtimestamp(claims["exp"], tz=timezone.utc)
        except jwt.PyJWKClientConnectionError as error:
            raise IdentityProviderUnavailable("Identity provider unavailable.") from error
        except (jwt.PyJWTError, KeyError, TypeError, ValueError, OverflowError) as error:
            raise AuthenticationDenied("Invalid authentication token.") from error

        if (
            not isinstance(subject, str)
            or not subject.strip()
            or len(subject) > 255
            or any(ord(character) < 32 for character in subject)
        ):
            raise AuthenticationDenied("Invalid authentication token.")
        now = datetime.now(timezone.utc)
        if (now - issued_at).total_seconds() > self.settings.max_token_age_seconds:
            raise AuthenticationDenied("Invalid authentication token.")
        return VerifiedIdentity(self.settings.issuer, subject, issued_at, expires_at)
