#!/usr/bin/env python3
"""Prepare a release: set the version, date the changelog, commit and tag (no push).

    python3 tools/release.py 0.4.0

1. CHANGELOG.md must already have a "## [0.4.0] - Unreleased" section describing the changes.
2. This sets "## Version: 0.4.0" in Storylines.toc, replaces "Unreleased" with today's date,
   runs the tests, commits "Release 0.4.0" and creates the tag v0.4.0.
3. Pushing the tag (git push origin <branch> v0.4.0) starts the GitHub workflow, which builds the
   zip, creates a GitHub release and uploads the version to CurseForge.
"""
import datetime
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(*cmd):
    subprocess.run(cmd, cwd=ROOT, check=True)


def main():
    if len(sys.argv) != 2 or not re.fullmatch(r"\d+\.\d+\.\d+", sys.argv[1]):
        sys.exit(__doc__)
    version = sys.argv[1]
    if subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout.strip():
        sys.exit("Commit or stash your changes first (the release commit should only contain the version bump).")
    if subprocess.run(["git", "rev-parse", "-q", "--verify", "refs/tags/v" + version], cwd=ROOT,
                      capture_output=True).returncode == 0:
        sys.exit("Tag v%s already exists" % version)

    changelog_path = os.path.join(ROOT, "CHANGELOG.md")
    with open(changelog_path, encoding="utf-8") as fh:
        changelog = fh.read()
    heading = re.compile(r"^## \[%s\] - Unreleased$" % re.escape(version), re.M)
    if not heading.search(changelog):
        sys.exit('CHANGELOG.md needs a "## [%s] - Unreleased" section first' % version)
    changelog = heading.sub("## [%s] - %s" % (version, datetime.date.today().isoformat()), changelog)

    toc_path = os.path.join(ROOT, "Storylines.toc")
    with open(toc_path, encoding="utf-8") as fh:
        toc = fh.read()
    toc, count = re.subn(r"^## Version: .*$", "## Version: " + version, toc, flags=re.M)
    if count != 1:
        sys.exit("Could not find '## Version:' in Storylines.toc")

    with open(changelog_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(changelog)
    with open(toc_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(toc)

    run(sys.executable, "tools/test_addon.py")
    run(sys.executable, "tools/validate_data.py")
    run("git", "add", "CHANGELOG.md", "Storylines.toc")
    run("git", "commit", "-q", "-m", "Release %s" % version)
    run("git", "tag", "-a", "v" + version, "-m", "Storylines %s" % version)
    branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, capture_output=True,
                            text=True).stdout.strip()
    print("\nReady. Publish with:\n    git push origin %s v%s" % (branch, version))


if __name__ == "__main__":
    main()
