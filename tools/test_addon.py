#!/usr/bin/env python3
"""Headless smoke test: loads the addon in Lua 5.1 with a mocked WoW API and exercises it.

Requires `pip install lupa`. Run: python3 tools/test_addon.py
"""
import os
import sys

from lupa import lua51

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MOCK = r"""
local printed = {}
_G.__printed = printed

local function newObject(kind, name)
    local o = { __kind = kind, __scripts = {}, __shown = kind ~= "Frame" or true, __text = "", __checked = false,
                __min = 0, __max = 0, __value = 0, __width = 300, __height = 400 }
    local methods = {}
    function methods:SetScript(event, fn) self.__scripts[event] = fn end
    function methods:GetScript(event) return self.__scripts[event] end
    function methods:HookScript(event, fn) self.__scripts[event] = fn end
    function methods:Show() local was = self.__shown; self.__shown = true
        if not was and self.__scripts.OnShow then self.__scripts.OnShow(self) end end
    function methods:Hide() self.__shown = false end
    function methods:IsShown() return self.__shown end
    function methods:SetShown(v) if v then self:Show() else self:Hide() end end
    function methods:GetHeight() return self.__height end
    function methods:GetWidth() return self.__width end
    function methods:SetSize(w, h) self.__width, self.__height = w, h end
    function methods:CreateTexture() return newObject("Texture") end
    function methods:CreateFontString() return newObject("FontString") end
    function methods:SetText(t) self.__text = t or "" end
    function methods:GetText() return self.__text end
    function methods:GetStringWidth() return #self.__text * 6 end
    function methods:SetChecked(v) self.__checked = v and true or false end
    function methods:GetChecked() return self.__checked end
    function methods:SetMinMaxValues(a, b) self.__min, self.__max = a, b end
    function methods:GetMinMaxValues() return self.__min, self.__max end
    function methods:SetValue(v) self.__value = v
        if self.__scripts.OnValueChanged then self.__scripts.OnValueChanged(self, v) end end
    function methods:GetValue() return self.__value end
    function methods:GetThumbTexture() self.__thumb = self.__thumb or newObject("Texture"); return self.__thumb end
    function methods:GetPoint() return "CENTER", nil, "CENTER", 0, 0 end
    function methods:GetCenter() return 0, 0 end
    function methods:GetEffectiveScale() return 1 end
    function methods:GetMapID() return 1436 end
    -- Unknown widget methods (capitalised names) are no-ops; other missing fields are nil, like real frames.
    return setmetatable(o, { __index = function(_, k)
        if methods[k] then return methods[k] end
        if type(k) == "string" and k:match("^%u") then return function() end end
    end })
end

function CreateFrame(kind, name, parent, template)
    local f = newObject(kind, name)
    f.__shown = true
    if name then _G[name] = f end
    return f
end

UIParent = CreateFrame("Frame", "UIParent")
Minimap = CreateFrame("Frame", "Minimap")
GameTooltip = CreateFrame("GameTooltip", "GameTooltip")
DEFAULT_CHAT_FRAME = { AddMessage = function(_, msg) printed[#printed + 1] = msg end }
UISpecialFrames = {}
SlashCmdList = {}
BackdropTemplateMixin = {}
SOUNDKIT = { IG_QUEST_LIST_COMPLETE = 619 }
function PlaySound() end
function Mixin(o, m) for k, v in pairs(m) do o[k] = v end return o end
function GameTooltip_Hide() end
function IsShiftKeyDown() return false end
function IsInInstance() return false end
function GetInstanceInfo() return "", "none" end
function GetRealZoneText() return __zoneText or "Westfall" end
function GetCursorPosition() return 0, 0 end
tinsert = table.insert
function wipe(t) for k in pairs(t) do t[k] = nil end return t end
function strtrim(s) return (s:gsub("^%s+", ""):gsub("%s+$", "")) end
C_Timer = { After = function(_, fn) fn() end }

__completed, __inLog, __ready = {}, {}, {}
__faction, __race, __map = "Alliance", 1, 1436
function UnitFactionGroup() return __faction end
function UnitRace() return "Race", "Race", __race end
C_QuestLog = {
    IsQuestFlaggedCompleted = function(id) return __completed[id] == true end,
    IsOnQuest = function(id) return __inLog[id] == true end,
    ReadyForTurnIn = function(id) return __ready[id] == true end,
    GetTitleForQuestID = function() return nil end,
}
local mapNames = { [1436] = "Westfall", [1429] = "Elwynn Forest", [1415] = "Eastern Kingdoms", [1411] = "Durotar",
                   [9999] = "Sentinel Hill" }
local mapParents = { [1436] = 1415, [1429] = 1415, [1411] = 1414, [9999] = 1436 }
C_Map = {
    GetBestMapForUnit = function() return __map end,
    GetMapInfo = function(id) return mapNames[id] and { name = mapNames[id], parentMapID = mapParents[id] or 0 } end,
}
"""


def main():
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(MOCK)
    # Remember every frame so the addon's (local) event frame can be driven from the test.
    lua.execute("""
        local orig = CreateFrame
        __frames = {}
        CreateFrame = function(...)
            local f = orig(...)
            table.insert(__frames, f)
            return f
        end
    """)
    run = lua.execute("return function(src, ns) return assert(loadstring(src))(ns) end")
    failures = []

    def check(cond, msg):
        print(("  ok   " if cond else "  FAIL ") + msg)
        if not cond:
            failures.append(msg)

    def lua_do(src):
        return run(src, ns)

    print("Loading:")
    toc = open(os.path.join(ROOT, "Storylines.toc"), encoding="utf-8").read()
    files = [l.strip() for l in toc.splitlines() if l.strip() and not l.startswith("#")]
    ns = lua.eval("{}")
    load = lua.execute("return function(src, name) return assert(loadstring(src, name)) end")
    for f in files:
        with open(os.path.join(ROOT, f.replace("\\", "/")), encoding="utf-8") as fh:
            load(fh.read(), "@" + f)("Storylines", ns)
    check(lua_do("local ns = ... return ns.Zones ~= nil and ns.Quests ~= nil"), "data tables loaded")
    lua_do("""local ns = ...
        for _, f in ipairs(__frames) do
            local h = f:GetScript("OnEvent")
            if h then ns.__fire = function(event, arg) h(f, event, arg) end end
        end
        ns.__fire("ADDON_LOADED", "Storylines")
        ns.__fire("PLAYER_LOGIN")
    """)
    check(lua_do("local ns = ... return ns.db ~= nil and StorylinesDB == ns.db"), "saved variables initialised")

    print("Zone detection:")
    check(lua_do("local ns = ... return ns:GetCurrentArea()") == 40, "map 1436 resolves to Westfall (40)")
    lua_do("__map = 9999")
    check(lua_do("local ns = ... return ns:GetCurrentArea()") == 40, "sub-map walks up to Westfall")
    lua_do("__map = nil; __zoneText = 'elwynn forest'")
    check(lua_do("local ns = ... return ns:GetCurrentArea()") == 12, "falls back to zone name")
    lua_do("__map = 1436; __zoneText = nil")

    print("Westfall as a Human:")
    stories = lua_do("""local ns = ...
        local out = {}
        for _, s in ipairs(ns:GetZoneStories(40)) do
            local d, t = ns:GetStoryProgress(s)
            out[#out + 1] = s.name .. '=' .. d .. '/' .. t
        end
        return table.concat(out, ';')""")
    print("   ", stories)
    check("The Defias Brotherhood=0/8" in stories, "Defias Brotherhood has 8 steps, none done")

    for q in (65, 132, 135, 141, 142, 155, 214):
        lua_do("__completed[%d] = true" % q)
    lua_do("__inLog[166] = true")
    defias = lua_do("""local ns = ...
        for _, s in ipairs(ns:GetZoneStories(40)) do
            if s.name == 'The Defias Brotherhood' then
                local d, t, started = ns:GetStoryProgress(s)
                local _, state = ns:ResolveStep(s.steps[#s.steps])
                return d .. '/' .. t .. ' started=' .. tostring(started) .. ' last=' .. state
            end
        end""")
    check(defias == "7/8 started=true last=1", "progress 7/8 with final quest in log (%s)" % defias)

    lua_do("__completed[166] = true; __inLog[166] = nil")
    lua_do("local ns = ... ns.__fire('QUEST_TURNED_IN', 166)")
    printed = lua.eval("table.concat(__printed, '\\n')")
    check("Storyline complete" in printed and "The Defias Brotherhood" in printed, "completion announced in chat")

    print("Faction filtering:")
    lua_do("__faction = 'Horde'; __race = 2")
    lua_do("local ns = ... ns:UpdatePlayerInfo()")
    horde_westfall = lua_do("""local ns = ...
        local out = {}
        for _, s in ipairs(ns:GetZoneStories(40)) do out[#out + 1] = s.name end
        return table.concat(out, ';')""")
    check("Defias" not in horde_westfall, "Horde does not see Alliance Westfall storylines (%s)" % horde_westfall)
    durotar = lua_do("local ns = ... local d, t = ns:GetZoneProgress(14) return t")
    check(durotar > 0, "Horde sees Durotar storylines (%d)" % durotar)
    lua_do("__faction = 'Alliance'; __race = 1")
    lua_do("local ns = ... ns:UpdatePlayerInfo()")
    check(lua_do("local ns = ... local d, t = ns:GetZoneProgress(14) return t") == 0, "Alliance sees no Durotar storylines")

    print("Race filtering:")
    # Find a quest restricted to some Alliance races.
    lua_do("""local ns = ...
        for id, q in pairs(ns.Quests) do
            if q[4] and q[3] == 1 then __raceQuest = id; __raceList = q[4]; break end
        end""")
    rq = lua.eval("__raceQuest")
    if rq:
        races = list(lua.eval("__raceList").values())
        other = next(r for r in (1, 3, 4, 7) if r not in races)
        lua_do("__race = %d" % races[0]); lua_do("local ns = ... ns:UpdatePlayerInfo()")
        check(lua_do("local ns = ... return ns:IsQuestForPlayer(%d)" % rq), "race quest %d visible to race %d" % (rq, races[0]))
        lua_do("__race = %d" % other); lua_do("local ns = ... ns:UpdatePlayerInfo()")
        check(not lua_do("local ns = ... return ns:IsQuestForPlayer(%d)" % rq), "hidden from race %d" % other)
        lua_do("__race = 40"); lua_do("local ns = ... ns:UpdatePlayerInfo()")
        check(lua_do("local ns = ... return ns:IsQuestForPlayer(%d)" % rq), "unknown new race falls back to faction")
        lua_do("__race = 1"); lua_do("local ns = ... ns:UpdatePlayerInfo()")

    print("UI:")
    lua_do("local ns = ... SlashCmdList.STORYLINES('')")
    check(lua.eval("StorylinesFrame ~= nil and StorylinesFrame:IsShown()"), "/storylines opens the window")
    check(lua_do("local ns = ... return ns.selectedArea") == 40, "window opens on the current zone")
    title = lua.eval("StorylinesFrame.zoneTitle:GetText()")
    check(title == "Westfall", "zone title is %r" % title)
    rows = lua_do("""local ns = ...
        local out = {}
        for _, row in ipairs(StorylinesFrame.storyList.rows) do
            if row:IsShown() then out[#out + 1] = row.text:GetText() .. ' | ' .. row.right:GetText() end
        end
        return table.concat(out, '\\n')""")
    print("   " + rows.replace("\n", "\n   "))
    check("The Defias Brotherhood" in rows, "story rows rendered")
    # Expand the first story by clicking it.
    lua_do("""local ns = ...
        local row = StorylinesFrame.storyList.rows[1]
        row:GetScript('OnClick')(row, 'LeftButton')""")
    expanded = lua.eval("StorylinesFrame.storyList.rows[2].text:GetText()")
    check(expanded.startswith("1. "), "clicking a story expands its steps (%r)" % expanded)
    # Tooltips must not error.
    lua_do("""local ns = ...
        for _, row in ipairs(StorylinesFrame.storyList.rows) do
            if row:IsShown() then row:GetScript('OnEnter')(row) end
        end
        for _, row in ipairs(StorylinesFrame.zoneList.rows) do
            if row:IsShown() then row:GetScript('OnEnter')(row) end
        end""")
    check(True, "tooltips render without errors")
    # Ignore the first step via right-click, then restore.
    lua_do("""local ns = ...
        local row = StorylinesFrame.storyList.rows[2]
        row:GetScript('OnClick')(row, 'RightButton')""")
    check(lua_do("local ns = ... return next(ns.db.ignoredQuests) ~= nil"), "right-click ignores a quest")
    lua_do("local ns = ... SlashCmdList.STORYLINES('reset')")
    check(lua_do("local ns = ... return next(ns.db.ignoredQuests) == nil"), "/storylines reset restores ignored quests")
    # Zone list: click a group header to collapse, click a zone to select it.
    zone_rows = lua_do("""local ns = ...
        local out = {}
        for _, row in ipairs(StorylinesFrame.zoneList.rows) do
            if row:IsShown() then out[#out + 1] = row.text:GetText() .. ' ' .. row.right:GetText() end
        end
        return table.concat(out, '\\n')""")
    print("   " + "\n   ".join(zone_rows.splitlines()[:6]) + "\n   ...")
    lua_do("""local ns = ...
        for _, row in ipairs(StorylinesFrame.zoneList.rows) do
            if row.item and row.item.areaID == 12 then row:GetScript('OnClick')(row, 'LeftButton') end
        end""")
    check(lua_do("local ns = ... return ns.selectedArea") == 12, "clicking a zone selects it")
    lua_do("local ns = ... SlashCmdList.STORYLINES('zone Durotar')")
    check(lua_do("local ns = ... return ns.selectedArea") == 14, "/storylines zone Durotar selects Durotar")
    lua_do("""local ns = ...
        StorylinesFrame.storyList:GetScript('OnMouseWheel')(StorylinesFrame.storyList, -1)
        ns.db.hideCompleted = true; ns:RefreshUI()
        ns.db.showSide = false; ns:RefreshUI()
        ns.db.showIgnored = true; ns:RefreshUI()""")
    check(True, "options and scrolling run without errors")
    lua_do("local ns = ... ns.__fire('ZONE_CHANGED_NEW_AREA'); ns.__fire('QUEST_LOG_UPDATE')")
    check(lua_do("local ns = ... return ns.selectedArea") == 40, "follows the player's zone on zone change")
    lua_do("local ns = ... SlashCmdList.STORYLINES('help'); SlashCmdList.STORYLINES('minimap'); Storylines_OnAddonCompartmentEnter(nil, StorylinesMinimapButton)")

    print("Data sanity:")
    bad = lua_do("""local ns = ...
        local missing = 0
        for _, zone in pairs(ns.Zones) do
            for _, story in ipairs(zone.stories) do
                for _, step in ipairs(story.steps) do
                    for _, id in ipairs(ns.StepIDs(step)) do if not ns.Quests[id] then missing = missing + 1 end end
                end
            end
            for _, step in ipairs(zone.side) do
                for _, id in ipairs(ns.StepIDs(step)) do if not ns.Quests[id] then missing = missing + 1 end end
            end
        end
        return missing""")
    check(bad == 0, "every referenced quest has data")

    if failures:
        print("\n%d check(s) failed" % len(failures))
        sys.exit(1)
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
