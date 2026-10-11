"""Standard-library client smoke test. Run while the FastAPI server is running."""
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
payload = (ROOT / "examples" / "request.json").read_bytes()
headers = {"Content-Type": "application/json"}
if os.getenv("REON_ENGINE_TOKEN"):
    headers["X-Service-Token"] = os.environ["REON_ENGINE_TOKEN"]
req = Request("http://127.0.0.1:8000/api/v1/memories/analyze", data=payload,
              headers=headers, method="POST")
try:
    with urlopen(req, timeout=10) as response:
        result = json.load(response)
    output = ROOT / "outputs" / "api_response.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"API OK: {result['meta']['input_moments']} Moments -> {len(result['memories'])} Memories")
    for m in result["memories"]:
        print(f"  [{m['sync_action']}] {m['title']}")
    print(f"Saved response: {output}")
except (HTTPError, URLError, OSError) as exc:
    print("API call failed:", exc)
    raise SystemExit(1) from exc
