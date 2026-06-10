"""
CI helper: writes config.md from config.ci.md template,
substituting secrets passed as environment variables.
"""
import os
import sys
from pathlib import Path

root = Path(__file__).parent.parent
template = (root / "config.ci.md").read_text(encoding="utf-8")

token = os.environ.get("APIFY_API_TOKEN", "")
password = os.environ.get("GMAIL_APP_PASSWORD", "")

print(f"APIFY_API_TOKEN length: {len(token)}", flush=True)
print(f"GMAIL_APP_PASSWORD length: {len(password)}", flush=True)

if not token:
    sys.exit("ERROR: APIFY_API_TOKEN secret is empty or not set")

result = template.replace("__APIFY_API_TOKEN__", token)
result = result.replace("__GMAIL_APP_PASSWORD__", password)

(root / "config.md").write_text(result, encoding="utf-8")
print("config.md written OK", flush=True)
