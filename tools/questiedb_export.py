"""Merged WoW Forever quest / NPC / object / item data from QuestieDB.

QuestieDB keeps the Forever database in layers: raw data, inherited Classic corrections,
a generated delta-base with the quests and NPCs that are new in Forever, machine-made trace
corrections and hand-made Forever corrections. Its own tools/export-forever.lua merges these
layers exactly like the addon does in game; this module runs that export and reads the result.

A small sparse checkout of QuestieDB (about 30 MB) is kept in tools/.cache/QuestieDB, or pass
an existing checkout with --questiedb.
"""
import os
import platform
import re
import shutil
import subprocess
import sys

import luatable

REPO = "https://github.com/Questie/QuestieDB.git"
SPARSE_PATHS = ["src", "generator", "tools", "data/Forever", "support/Forever"]
COMBINED = os.path.join("src", "corrections", "Forever", "combined")
KINDS = {"quests": ("Quest", "quest"), "npcs": ("Npc", "npc"), "objects": ("Object", "object"),
         "items": ("Item", "item")}


def _run(cmd, cwd=None):
    print("$ " + " ".join(cmd), file=sys.stderr)
    subprocess.run(cmd, cwd=cwd, check=True)


def ensure_checkout(path, offline):
    """Clone (sparse, shallow) or update the QuestieDB checkout at path."""
    if os.path.isdir(os.path.join(path, ".git")):
        if not offline:
            _run(["git", "pull", "--quiet", "--ff-only"], cwd=path)
        return path
    if offline:
        sys.exit("No QuestieDB checkout at %s; run without --offline (or pass --questiedb)" % path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    _run(["git", "clone", "--quiet", "--depth", "1", "--filter=blob:none", "--sparse", REPO, path])
    _run(["git", "sparse-checkout", "set"] + SPARSE_PATHS, cwd=path)
    return path


def _lua_interpreter(checkout):
    if os.environ.get("LUA"):
        return os.environ["LUA"]
    system, machine = platform.system(), platform.machine().lower()
    if system == "Linux" and machine in ("x86_64", "amd64"):
        return os.path.join(checkout, "tools", "lua-binary", "linux-x64", "lua")
    if system == "Windows":
        return os.path.join(checkout, "tools", "lua-binary", "lua.exe")
    for candidate in ("lua5.1", "luajit", "lua"):
        if shutil.which(candidate):
            return candidate
    sys.exit("A Lua 5.1 interpreter is needed for the QuestieDB export; set LUA=/path/to/lua5.1")


def export(checkout, offline):
    """Run QuestieDB's Forever export (including authored corrections) unless offline and cached."""
    combined = os.path.join(checkout, COMBINED)
    if offline and all(os.path.exists(os.path.join(combined, "forever%sDB.lua" % k)) for k, _ in KINDS.values()):
        return combined
    _run([_lua_interpreter(checkout), "tools/export-forever.lua", "--include-authored"], cwd=checkout)
    return combined


def load(combined, kind):
    """Parse one exported database ('quests', 'npcs', 'objects' or 'items') into {id: {field: value}}."""
    file_kind, var = KINDS[kind]
    with open(os.path.join(combined, "forever%sDB.lua" % file_kind), encoding="utf-8") as fh:
        text = fh.read()
    rows = re.findall(r"^%s\[(\d+)\]=(\{.*\})$" % var, text, re.M)
    if not rows:
        sys.exit("No %s rows found in the QuestieDB export; has its format changed?" % kind)
    return {int(entity_id): luatable.parse(body) for entity_id, body in rows}


def commit_info(checkout):
    try:
        return subprocess.run(["git", "log", "-1", "--format=%h %cs"], cwd=checkout, check=True,
                              capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
