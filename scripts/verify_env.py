"""Script to verify and print current environment configuration with masked secrets."""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

def mask_key(key: Optional[str]) -> str:
    if not key:
        return "Not Set"
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"

def verify():
    repo_root = Path(__file__).resolve().parents[1]
    if load_dotenv is not None:
        load_dotenv(repo_root / ".env", override=True)

    print("=== ENVIRONMENT CONFIGURATION STATUS ===")
    
    variables = [
        "LLM_PROVIDER",
        "PRIMARY_PROVIDER",
        "SECONDARY_PROVIDER",
        "GEMINI_API_KEY",
        "GEMINI_MODEL",
        "OPENROUTER_API_KEY",
        "OPENROUTER_MODELS",
        "OPENROUTER_SITE_URL",
        "OPENROUTER_APP_NAME"
    ]

    for var in variables:
        val = os.environ.get(var)
        if "API_KEY" in var:
            masked = mask_key(val)
            print(f"  {var}: {masked}")
        else:
            print(f"  {var}: {val or 'Not Set'}")

    print("========================================\n")

if __name__ == "__main__":
    verify()
