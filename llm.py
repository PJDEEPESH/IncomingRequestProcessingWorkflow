"""
Central place that creates the OpenAI client and holds model config.

The rest of the app never talks to OpenAI directly - it always goes through
here. That keeps the AI provider in ONE file, so swapping models (or providers)
later is a one-line change.
"""
import os
import ssl

from dotenv import load_dotenv

load_dotenv()  # reads a local .env file if present

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Corporate networks (and this machine) do SSL inspection, so Python's default
# cert bundle can't verify api.openai.com ("unable to get local issuer
# certificate"). truststore makes verification use the OS (Windows) trust store,
# which DOES contain the corporate root CA - so HTTPS works *without* disabling
# security. Falls back to normal verification if truststore isn't available.
try:
    import truststore
    _SSL_VERIFY = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
except Exception:
    _SSL_VERIFY = True


def get_client(api_key: str | None = None):
    """
    Return an OpenAI client, or None if no key is available.

    Returning None (instead of crashing) is deliberate: it lets the app fall
    back to the rule-based engine so a demo never dies just because a key is
    missing or the network is down.
    """
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    try:
        import httpx
        from openai import OpenAI
        return OpenAI(api_key=key, http_client=httpx.Client(verify=_SSL_VERIFY))
    except Exception:
        return None
