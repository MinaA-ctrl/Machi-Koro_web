"""Runtime config + startup guards (S2.6a).

`MK_ENV=prod` makes the service refuse to boot with missing/insecure secrets — so a
real deployment can never run on the dev defaults. Tests/dev (MK_ENV unset) skip the
guard (they set their own test secrets).
"""
import os

# Must match app.auth's dev fallback — the guard rejects it in prod.
INSECURE_JWT_DEFAULT = "dev-insecure-jwt-secret-change-me"


def is_prod() -> bool:
    return os.getenv("MK_ENV", "").lower() == "prod"


def require_secrets() -> None:
    """In prod, MK_JWT_SECRET and MK_WS_SECRET must be set to real (non-default)
    values. Raises RuntimeError (→ boot fails) otherwise. No-op outside prod."""
    if not is_prod():
        return
    problems = []
    jwt = os.getenv("MK_JWT_SECRET", "")
    if not jwt or jwt == INSECURE_JWT_DEFAULT:
        problems.append("MK_JWT_SECRET (unset or insecure default)")
    if not os.getenv("MK_WS_SECRET", ""):
        problems.append("MK_WS_SECRET (unset)")
    if problems:
        raise RuntimeError(
            "MK_ENV=prod but required secrets are missing/insecure: " + ", ".join(problems)
        )
