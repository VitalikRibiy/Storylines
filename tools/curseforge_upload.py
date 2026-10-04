#!/usr/bin/env python3
"""Upload a packaged release to CurseForge (used by .github/workflows/release.yml).

Reads the version and the WoW interface number from Storylines.toc, takes that version's
section from CHANGELOG.md as the changelog, looks up the CurseForge game version (e.g. 1.60.1
for interface 16001 = WoW Forever) and uploads the zip.

Environment:
    CF_API_TOKEN      CurseForge API token (CurseForge: My Account -> API Tokens). Required to upload.
    CF_PROJECT_ID     Project ID, unless Storylines.toc has "## X-Curse-Project-ID".
    CF_RELEASE_TYPE   alpha, beta or release (default: beta).

Usage:
    python3 tools/curseforge_upload.py --zip dist/Storylines-0.4.0.zip [--dry-run]
    python3 tools/curseforge_upload.py --print-changelog
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = os.environ.get("CF_API_URL", "https://wow.curseforge.com/api")  # override only for testing
RELEASE_TYPES = ("alpha", "beta", "release")


def toc_field(name):
    with open(os.path.join(ROOT, "Storylines.toc"), encoding="utf-8") as fh:
        for line in fh:
            m = re.match(r"^##\s*%s:\s*(.+?)\s*$" % re.escape(name), line)
            if m:
                return m.group(1)
    return None


def game_version_name(interface):
    """WoW interface number -> game version name, e.g. 16001 -> 1.60.1, 11508 -> 1.15.8."""
    first = interface.split(",")[0].strip()
    if not re.fullmatch(r"\d{5,6}", first):
        sys.exit("Unexpected ## Interface value: %r" % interface)
    major, minor, patch = int(first[:-4]), int(first[-4:-2]), int(first[-2:])
    return "%d.%d.%d" % (major, minor, patch)


def changelog_section(version):
    """The CHANGELOG.md section for this version (without its heading), and its date/status."""
    with open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8") as fh:
        text = fh.read()
    m = re.search(r"^## \[%s\]\s*-\s*(.+?)\s*$(.*?)(?=^## \[|\Z)" % re.escape(version), text, re.M | re.S)
    if not m:
        sys.exit("CHANGELOG.md has no section for version %s" % version)
    return m.group(2).strip(), m.group(1)


def api_request(path, token, data=None, content_type=None):
    request = urllib.request.Request(API + path, data=data, method="POST" if data else "GET")
    request.add_header("X-Api-Token", token)
    request.add_header("User-Agent", "Storylines release script")
    if content_type:
        request.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        sys.exit("CurseForge API %s failed: HTTP %d %s" % (path, err.code, err.read().decode("utf-8", "replace")[:500]))


def find_game_versions(versions, name):
    ids = [v["id"] for v in versions if v.get("name") == name]
    if not ids:
        close = sorted({v.get("name") for v in versions if str(v.get("name", "")).startswith(name.rsplit(".", 1)[0])})
        sys.exit("CurseForge has no game version named %s (similar: %s). Set CF_GAME_VERSION to override."
                 % (name, ", ".join(close) or "none"))
    return ids


def multipart(fields, file_field, file_name, file_bytes):
    boundary = uuid.uuid4().hex
    parts = []
    for key, value in fields.items():
        parts.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n"
                      % (boundary, key, value)).encode("utf-8"))
    parts.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\n"
                  "Content-Type: application/zip\r\n\r\n" % (boundary, file_field, file_name)).encode("utf-8"))
    parts.append(file_bytes)
    parts.append(("\r\n--%s--\r\n" % boundary).encode("utf-8"))
    return b"".join(parts), "multipart/form-data; boundary=%s" % boundary


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zip", help="packaged addon zip to upload")
    ap.add_argument("--dry-run", action="store_true", help="check everything and print the request, don't upload")
    ap.add_argument("--print-changelog", action="store_true", help="print this version's changelog and exit")
    args = ap.parse_args()

    version = toc_field("Version")
    notes, status = changelog_section(version)
    if args.print_changelog:
        print(notes)
        return
    if not args.zip or not os.path.isfile(args.zip):
        sys.exit("--zip must point to the packaged addon")
    if status.lower() == "unreleased" and not args.dry_run:
        sys.exit("CHANGELOG.md still lists %s as Unreleased; run tools/release.py first" % version)

    release_type = (os.environ.get("CF_RELEASE_TYPE") or "beta").strip().lower()
    if release_type not in RELEASE_TYPES:
        sys.exit("CF_RELEASE_TYPE must be one of %s" % ", ".join(RELEASE_TYPES))
    project_id = toc_field("X-Curse-Project-ID") or os.environ.get("CF_PROJECT_ID", "").strip()
    game_version = os.environ.get("CF_GAME_VERSION", "").strip() or game_version_name(toc_field("Interface") or "")
    metadata = {
        "changelog": notes,
        "changelogType": "markdown",
        "displayName": "Storylines %s" % version,
        "releaseType": release_type,
        "gameVersions": [],
    }

    token = os.environ.get("CF_API_TOKEN", "").strip()
    if args.dry_run:
        metadata["gameVersions"] = ["<id of %s>" % game_version]
        print("Dry run: would upload %s (%d bytes) to project %s" % (
            args.zip, os.path.getsize(args.zip), project_id or "<CF_PROJECT_ID missing>"))
        print(json.dumps(metadata, indent=2))
        return
    if not token:
        sys.exit("CF_API_TOKEN is not set")
    if not project_id:
        sys.exit("Set CF_PROJECT_ID or add '## X-Curse-Project-ID: <id>' to Storylines.toc")

    metadata["gameVersions"] = find_game_versions(api_request("/game/versions", token), game_version)
    with open(args.zip, "rb") as fh:
        body, content_type = multipart({"metadata": json.dumps(metadata)}, "file", os.path.basename(args.zip), fh.read())
    result = api_request("/projects/%s/upload-file" % project_id, token, body, content_type)
    print("Uploaded %s as CurseForge file %s (%s, game version %s)" % (
        os.path.basename(args.zip), result.get("id"), release_type, game_version))


if __name__ == "__main__":
    main()
