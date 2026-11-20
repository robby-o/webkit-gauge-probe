"""Loads the probe page in a Safari through its own WebDriver and prints what the page reports.

Usage: python3 drive.py <safaridriver path> <page URL> <label>
Prints one JSON object: {"label", "browser", "report"}. Exit 0 when the page reported, 1 when the session or the
page failed (the reason is in the object's "failed").
"""

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request

PORT = 4477
BASE = f"http://127.0.0.1:{PORT}"


def call(method: str, path: str, body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(BASE + path, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        return json.loads(error.read())


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__)
        return 2
    driver_path, url, label = sys.argv[1:]
    driver = subprocess.Popen([driver_path, "-p", str(PORT), "--diagnose"])
    result: dict = {"label": label}
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen(BASE + "/status", timeout=2)
                break
            except OSError:
                time.sleep(0.2)
        value: dict = {}
        for _ in range(3):
            value = call("POST", "/session", {"capabilities": {"alwaysMatch": {}}}).get("value", {})
            if "sessionId" in value:
                break
            time.sleep(10)
        if "sessionId" not in value:
            result["failed"] = value
            return 1
        sid = value["sessionId"]
        result["browser"] = {k: value["capabilities"].get(k) for k in ("browserName", "browserVersion", "platformName")}
        call("POST", f"/session/{sid}/timeouts", {"script": 90000, "pageLoad": 60000})
        call("POST", f"/session/{sid}/url", {"url": url})
        script = "const done = arguments[arguments.length - 1]; window.probed.then(done);"
        report = call("POST", f"/session/{sid}/execute/async", {"script": script, "args": []})
        call("DELETE", f"/session/{sid}")
        result["report"] = report.get("value")
        return 0 if isinstance(result["report"], dict) and "failed" not in result["report"] else 1
    finally:
        print(json.dumps(result, indent=1, sort_keys=True))
        driver.terminate()


if __name__ == "__main__":
    sys.exit(main())
