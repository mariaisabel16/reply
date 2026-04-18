from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_env_file(path: Path) -> None:
    """Minimal .env loader (no python-dotenv): avoids Windows Scripts install issues."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        # Same as python-dotenv default: do not override existing process env
        if key not in os.environ:
            os.environ[key] = value


def _truthy(raw: str | None, default: bool) -> bool:
    if raw is None or raw.strip() == "":
        return default
    s = raw.strip().lower()
    if s in ("0", "false", "no", "off"):
        return False
    if s in ("1", "true", "yes", "on"):
        return True
    return default


@dataclass(frozen=True)
class Settings:
    bedrock_region: str
    bedrock_model_id: str
    openai_api_key: str
    openai_model: str
    ollama_base_url: str
    ollama_model: str
    nat_api_base_url: str
    nat_semester_url_template: str
    nat_http_timeout_s: float
    use_fixture_if_nat_fails: bool
    auth_dev_fallback_secret: str
    cors_allow_origin_regex: str


def load_settings() -> Settings:
    env_path = Path(__file__).resolve().parent / ".env"
    _load_env_file(env_path)
    timeout_raw = os.environ.get("NAT_HTTP_TIMEOUT_S", "20").strip()
    try:
        timeout = float(timeout_raw)
    except ValueError:
        timeout = 20.0
    return Settings(
        bedrock_region=os.environ.get("BEDROCK_REGION", "eu-central-1").strip() or "eu-central-1",
        bedrock_model_id=os.environ.get("BEDROCK_MODEL_ID", "").strip(),
        openai_api_key=os.environ.get("OPENAI_API_KEY", "").strip(),
        openai_model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip(),
        ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "").strip().rstrip("/"),
        ollama_model=os.environ.get("OLLAMA_MODEL", "llama3.2").strip(),
        nat_api_base_url=os.environ.get("NAT_API_BASE_URL", "https://api.srv.nat.tum.de").strip().rstrip("/")
        or "https://api.srv.nat.tum.de",
        nat_semester_url_template=os.environ.get("NAT_SEMESTER_URL_TEMPLATE", "").strip(),
        nat_http_timeout_s=timeout,
        use_fixture_if_nat_fails=_truthy(os.environ.get("USE_FIXTURE_IF_NAT_FAILS"), True),
        auth_dev_fallback_secret=os.environ.get("CAMPUSPILOT_SECRET", "dev-local-only-insecure").strip()
        or "dev-local-only-insecure",
        cors_allow_origin_regex=os.environ.get(
            "CORS_ALLOW_ORIGIN_REGEX",
            r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
        ).strip()
        or r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    )


settings = load_settings()
