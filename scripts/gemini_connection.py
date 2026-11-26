"""Read-only Gemini connection check; no generation or billing changes."""
import json
import os
import sys
import urllib.error
import urllib.request

NAMES = ("GEMINI_API_KEY", "GEMINI_API_KEY_1", "GEMINI_API_KEY_2",
         "GEMINI_API_KEY_3", "GEMINI_API_KEY1", "GEMINI_API_KEY2",
         "GEMINI_API_KEY3")
URL = "https://generativelanguage.googleapis.com/v1beta/models?pageSize=100"

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def check(key):
    req = urllib.request.Request(URL, headers={"x-goog-api-key": key, "Accept": "application/json"})
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=15) as response:
            body = json.loads(response.read(500000))
            models = [m.get("name", "") for m in body.get("models", [])
                      if "generateContent" in m.get("supportedGenerationMethods", [])]
            return {"status": "connected", "http": response.status,
                    "generationModelsListed": len(models)}
    except urllib.error.HTTPError as exc:
        return {"status": "http_error", "http": exc.code}
    except Exception:
        return {"status": "connection_error"}

def report(env, probe=check):
    seen = set()
    results = []
    for name in NAMES:
        key = env.get(name, "").strip()
        if not key:
            continue
        if key in seen:
            results.append({"secretName": name, "status": "duplicate_key"})
            continue
        seen.add(key)
        results.append({"secretName": name, **probe(key)})
    return {"configuredUniqueKeys": len(seen),
            "connectedKeys": sum(r["status"] == "connected" for r in results),
            "checks": results, "generationAttempted": False,
            "freeTierVerified": False}

def self_test():
    result = report({"GEMINI_API_KEY": "test-a", "GEMINI_API_KEY_2": "test-b",
                     "GEMINI_API_KEY_3": "test-a"},
                    lambda key: {"status": "connected", "http": 200})
    assert result["configuredUniqueKeys"] == 2
    assert result["connectedKeys"] == 2
    assert "test-a" not in json.dumps(result)
    assert not result["generationAttempted"]
    assert report({}, lambda _: None)["configuredUniqueKeys"] == 0
    print("Gemini connection-check self-test passed.")

if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    else:
        result = report(os.environ)
        print(json.dumps(result, indent=2))
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a", encoding="utf-8") as handle:
                handle.write("## Gemini read-only connection check\n\n")
                handle.write("Configured unique keys: %s; connected: %s\n\n" %
                             (result["configuredUniqueKeys"], result["connectedKeys"]))
                for item in result["checks"]:
                    handle.write("- %s: %s (HTTP %s)\n" %
                                 (item["secretName"], item["status"], item.get("http", "-")))
                handle.write("\nNo content generation. Free tier and billing status not verified.\n")
        if not result["connectedKeys"]:
            sys.exit(1)
