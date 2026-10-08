"""Send one minimal Gemini request and print only non-secret diagnostics."""

from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from openai import OpenAI


def main() -> int:
    load_dotenv()
    key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip()
    if not key:
        print(json.dumps({"ok": False, "error_type": "MissingGeminiKey"}))
        return 1

    client = OpenAI(
        api_key=key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        max_retries=0,
    )
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with exactly OK"}],
            max_tokens=8,
        )
        print(
            json.dumps(
                {
                    "ok": True,
                    "configured_model": model,
                    "response_model": response.model,
                    "reply": response.choices[0].message.content,
                },
                ensure_ascii=False,
            )
        )
        return 0
    except Exception as exc:  # Provider exception types vary by SDK release.
        print(
            json.dumps(
                {
                    "ok": False,
                    "configured_model": model,
                    "error_type": type(exc).__name__,
                    "status_code": getattr(exc, "status_code", None),
                    "error_code": getattr(exc, "code", None),
                }
            )
        )
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
