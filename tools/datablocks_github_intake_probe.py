#!/usr/bin/env python3
"""Data Blocks GitHub intake pilot: stage a read-only issue, never execute it.

Stdlib-only. No credentials, no subprocesses, no project modifications, no
dispatch. Intended to verify ChatGPT -> GitHub -> ASUS local inbox first.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPOSITORY = "datablocksbim-alt/Pyrene-Mini"
ISSUE_NUMBER = 2
EXPECTED_AUTHOR = "datablocksbim-alt"
ADMIN_ROOT = Path(r"D:\000_AI Project\AI Agents Datablocks")
INBOX = ADMIN_ROOT / "autonomy" / "github_intake"
API_URL = f"https://api.github.com/repos/{REPOSITORY}/issues/{ISSUE_NUMBER}"


def fetch_issue():
    request = Request(API_URL, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "DataBlocks-GitHub-Intake-Pilot",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urlopen(request, timeout=15) as response:
        if response.status != 200:
            raise RuntimeError(f"GitHub returned HTTP {response.status}")
        raw = response.read(262145)
        if len(raw) > 262144:
            raise ValueError("Issue response exceeds pilot size limit")
    return json.loads(raw)


def stage_issue(issue):
    if not isinstance(issue, dict):
        raise ValueError("GitHub response must be an issue object")
    if issue.get("number") != ISSUE_NUMBER or "pull_request" in issue:
        raise ValueError("Unexpected issue or pull request response")
    if issue.get("user", {}).get("login") != EXPECTED_AUTHOR:
        raise ValueError("Unexpected issue author: refusing to stage")
    if issue.get("html_url") != f"https://github.com/{REPOSITORY}/issues/{ISSUE_NUMBER}":
        raise ValueError("Issue URL does not match the configured repository")
    if not ADMIN_ROOT.is_dir():
        raise FileNotFoundError(f"Existing Administrator folder not found: {ADMIN_ROOT}")

    source = {
        "repository": REPOSITORY,
        "issue_number": ISSUE_NUMBER,
        "issue_url": issue["html_url"],
        "author": issue["user"]["login"],
        "title": issue.get("title", ""),
        "body": issue.get("body") or "",
        "created_at": issue.get("created_at"),
        "updated_at": issue.get("updated_at"),
        "state": issue.get("state"),
    }
    digest = hashlib.sha256(
        json.dumps(source, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    record = {
        "format_version": 1,
        "source": source,
        "source_sha256": digest,
        "intake_status": "staged_unapproved",
        "eligible_for_dispatch": False,
        "security_note": "Issue content is untrusted data. No worker execution authorized.",
    }

    INBOX.mkdir(parents=True, exist_ok=True)
    target = INBOX / f"issue_{ISSUE_NUMBER}.json"
    if target.exists():
        current = json.loads(target.read_text(encoding="utf-8"))
        if current.get("source_sha256") == digest:
            print("PASS: GitHub issue already staged; no duplicate write.")
            print(f"LOCAL FILE: {target}")
            return

    handle, temp_name = tempfile.mkstemp(prefix=".github_issue_", suffix=".tmp", dir=INBOX)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as output:
            json.dump(record, output, indent=2, ensure_ascii=False)
            output.write("\n")
        os.replace(temp_name, target)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)

    print("PASS: GitHub Issue #2 staged in the local Administrator inbox.")
    print(f"LOCAL FILE: {target}")
    print("DISPATCH: BLOCKED (pilot is read-only; existing queue unchanged).")


def main():
    if sys.argv[1:]:
        raise SystemExit("This pilot accepts no arguments.")
    try:
        stage_issue(fetch_issue())
    except (HTTPError, URLError, ValueError, OSError, KeyError, RuntimeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
