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
    function methods:CreateFontString()
        local fs = newObject("FontString")
        fs.__parent = self
        self.__regions = self.__regions or {}
        table.insert(self.__regions, fs)
        return fs
    end
    function methods:IsVisible()
        local o = self
        while o do
            if not o.__shown then return false end
            o = o.__parent
        end
        return true
    end
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
    f.__parent = parent
    if parent then
        parent.__children = parent.__children or {}
        table.insert(parent.__children, f)
    end
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
__level = 20
function UnitLevel() return __level end
function UnitName() return "Tester" end
function UnitClass() return "Warrior" end
function UnitSex() return 2 end
__waypoint = nil
UiMapPoint = { CreateFromCoordinates = function(map, x, y) return { map = map, x = x, y = y } end }
-- Collects the visible text of a frame tree (for checking what the inspector shows).
function __visibleText(frame)
    local out = {}
    local function walk(f)
        if not f.__shown then return end
        for _, r in ipairs(f.__regions or {}) do
            if r.__shown and r.__text ~= "" then out[#out + 1] = r.__text end
        end
        for _, c in ipairs(f.__children or {}) do walk(c) end
    end
    walk(frame)
    return table.concat(out, "\n")
end
C_QuestLog = {
    IsQuestFlaggedCompleted = function(id) return __completed[id] == true end,
    IsOnQuest = function(id) return __inLog[id] == true end,
    ReadyForTurnIn = function(id) return __ready[id] == true end,
    GetTitleForQuestID = function() return nil end,
}
local mapNames = { [1436] = "Westfall", [1429] = "Elwynn Forest", [1415] = "Eastern Kingdoms", [1411] = "Durotar",
                   [9999] = "Sentinel Hill" }
local mapParents = { [1436] = 1415, [1429] = 1415, [1411] = 1414, [9999] = 1436 }
__rep, __npcGUID, __secret, __errors = {}, nil, false, {}
C_Reputation = { GetFactionDataByID = function(id) return __rep[id] and { currentStanding = __rep[id] } end }
function UnitGUID() return __npcGUID end
function issecretvalue() return __secret end
UIErrorsFrame = { AddMessage = function(_, msg) table.insert(__errors, msg) end }
function strsplit(sep, s)
    local out = {}
    for part in (s .. sep):gmatch("(.-)%" .. sep) do out[#out + 1] = part end
    return unpack(out)
end
C_Map = {
    GetBestMapForUnit = function() return __map end,
    GetMapInfo = function(id) return mapNames[id] and { name = mapNames[id], parentMapID = mapParents[id] or 0 } end,
    SetUserWaypoint = function(point) __waypoint = point end,
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
    lua_do("local ns = ... ns.__fire('QUEST_LOG_UPDATE')")  # the client fires this on every quest state change
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
    check(lua_do("""local ns = ...
        for _, row in ipairs(StorylinesFrame.zoneList.rows) do
            if row:IsShown() and row.item and row.item.areaID == 40 then return true end
        end
        return false""") is True, "the zone list is scrolled to show the current zone")
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
    clicked = lua_do("""local ns = ...
        for _, row in ipairs(StorylinesFrame.zoneList.rows) do
            if row:IsShown() and row.item and row.item.areaID and row.item.areaID ~= 40 then
                row:GetScript('OnClick')(row, 'LeftButton')
                return row.item.areaID
            end
        end""")
    check(clicked and lua_do("local ns = ... return ns.selectedArea") == clicked, "clicking a zone selects it")
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

    print("Levels, quest types and inspector:")
    lua_do("local ns = ... ns:ShowUI(40)")
    colors = lua_do("""local ns = ...
        __level = 20
        local function hex(level) local r, g, b = ns:GetLevelColor(level) return ('%02x%02x%02x'):format(r * 255, g * 255, b * 255) end
        return table.concat({ hex(26), hex(23), hex(20), hex(14), hex(5) }, ',')""")
    check(colors == "ff1919,ff7f3f,ffd100,3fbf3f,7f7f7f",
          "difficulty colors red/orange/yellow/green/gray at level 20 (%s)" % colors)
    check(lua_do("local ns = ... return ns:GetQuestTag(166)") == 81, "VanCleef quest (166) is tagged Dungeon")
    check(lua_do("local ns = ... return ns:GetQuestTag(176)") == 1, "Wanted: Hogger (176) is tagged Elite")
    line = lua_do("local ns = ... __level = 17 local l = ns:FormatQuestLine(166, '8. ', ns.STATE_TODO) __level = 20 return l")
    check("|cffff1919[22]|r" in line and "INV_Misc_Key_03" in line,
          "quest line has a level colored by difficulty and a dungeon icon (%s)" % line)
    # Click the Defias storyline: it expands and opens in the inspector.
    lua_do("""local ns = ...
        ns.db.hideCompleted = false
        ns.db.showSide = true
        ns:RefreshUI()
        for _, row in ipairs(StorylinesFrame.storyList.rows) do
            if row.item and row.item.type == 'story' and row.item.story.name == 'The Defias Brotherhood' then
                row:GetScript('OnClick')(row, 'LeftButton')
                break
            end
        end""")
    check(lua.eval("StorylinesInspector ~= nil and StorylinesInspector:IsShown()"), "clicking a storyline opens the inspector")
    story_text = lua.eval("__visibleText(StorylinesInspector)")
    print("   " + story_text.replace("\n", "\n   ")[:900])
    check("Levels:" in story_text and "Starts with" in story_text and "Gryan Stoutmantle" in story_text,
          "storyline overview shows levels, start and quest giver")
    check("Dungeon" in story_text, "storyline overview lists its dungeon quest type")
    # Click the last step (VanCleef) in the story list to inspect the quest.
    lua_do("""local ns = ...
        for _, row in ipairs(StorylinesFrame.storyList.rows) do
            if row.item and row.item.questID == 166 then row:GetScript('OnClick')(row, 'LeftButton') break end
        end""")
    quest_text = lua.eval("__visibleText(StorylinesInspector)")
    print("   " + quest_text.replace("\n", "\n   "))
    for needle, label in (("Kill Edwin VanCleef", "objectives"), ("Requires level 14", "required level"),
                          ("Dungeon quest", "quest type"), ("Westfall (56.3, 47.5)", "giver location"),
                          ("+500|r Stormwind", "reputation reward"), ("Tunic of Westfall", "reward items"),
                          ("2,600 XP", "experience"), ("Quest 8 of 8", "position in storyline")):
        check(needle in quest_text, "quest details show " + label)
    # Click the giver location to set a waypoint.
    lua_do("""local ns = ...
        local function walk(f)
            for _, c in ipairs(f.__children or {}) do
                if c.text and c.text.__text and c.text.__text:find('56.3') and c:IsVisible() then
                    c:GetScript('OnClick')(c) return true
                end
                if walk(c) then return true end
            end
        end
        walk(StorylinesInspector)""")
    wp = lua.eval("__waypoint")
    check(wp is not None and wp["map"] == 1436 and abs(wp["x"] - 0.563) < 1e-6, "clicking the location sets a map waypoint")
    lua_do("local ns = ... ns:CloseInspector()")
    check(not lua.eval("StorylinesInspector:IsShown()"), "inspector closes")

    print("Review fixes:")
    check(lua_do("local ns = ... return ns.Quests[1149] ~= nil and ns.Quests[151] ~= nil"),
          "real quests like 'Test of Faith' and 'Poor Old Blanchy' are not filtered as placeholders")
    lua_do("""local ns = ...
        ns.db.collapsedGroups[3] = true
        ns:RefreshUI()
        local list = StorylinesFrame.zoneList
        list.offset = #list.items
        list:Update()
        for _, row in ipairs(StorylinesFrame.zoneList.rows) do
            if row:IsShown() and row.item and row.item.type == 'group' and row.item.group == 3 then
                row:GetScript('OnClick')(row, 'LeftButton') break
            end
        end""")
    check(lua_do("local ns = ... return ns.db.collapsedGroups[3]") is False,
          "expanding a default-collapsed group is saved as false (survives the defaults on reload)")
    check(lua_do("local ns = ... return ns:FindAreaByName('westf')") == 40, "partial zone name 'westf' finds Westfall")
    ambiguous = lua_do("local ns = ... local id, names = ns:FindAreaByName('west') return id == nil and table.concat(names, ',')")
    check(ambiguous and "Westfall" in ambiguous and "Western Plaguelands" in ambiguous,
          "ambiguous 'west' lists the candidates (%s)" % ambiguous)
    lua_do("__level = 20")
    names = lua_do("""local ns = ...
        local out = {}
        for _, l in ipairs({26, 23, 20, 14, 5}) do out[#out + 1] = ns:GetDifficultyName(l) end
        return table.concat(out, ',')""")
    check(names == "Very hard,Hard,Normal,Easy,Trivial", "difficulty names match the colors (%s)" % names)
    before = lua_do("""local ns = ...
        for _, s in ipairs(ns:GetZoneStories(40)) do
            if s.name == 'The Defias Brotherhood' then __defias = s; local _, t = ns:GetStoryProgress(s) return t end
        end""")
    lua_do("local ns = ... ns:SetQuestIgnored(65, true)")
    after = lua_do("local ns = ... local _, t = ns:GetStoryProgress(__defias) return t")
    lua_do("local ns = ... ns:SetQuestIgnored(65, false)")
    check(after == before - 1, "ignoring a quest updates cached storyline progress (%s -> %s)" % (before, after))
    lua_do("local ns = ... ns:ShowUI(40) ns:InspectQuest(1150, __defias)")
    check(lua_do("local ns = ... local v = ns:GetInspected() return v.story and v.story.name") == "Final Passage",
          "inspecting a quest from another storyline shows that storyline")
    lua_do("local ns = ... ns:CloseInspector()")

    print("Quest availability:")
    # Duskwood's Sven chain (untouched by the tests above): 95 -> 230 -> 262 -> 265, all required level 20.
    lua_do("""local ns = ...
        __level = 25
        __completed[95] = true
        ns.__fire('QUEST_LOG_UPDATE')""")
    check(lua_do("local ns = ... return ns:GetQuestAvailability(230)") == "available", "230 is available once 95 is done")
    check(lua_do("local ns = ... return ns:GetQuestAvailability(262)") == "locked", "262 is locked until 230 is done")
    lua_do("__level = 15")
    avail = lua_do("local ns = ... local a, l = ns:GetQuestAvailability(230) return a .. ':' .. tostring(l)")
    check(avail == "level:20", "at level 15, 230 needs level 20 (%s)" % avail)
    lua_do("__level = 25")
    lua_do("""local ns = ...
        ns.db.hideCompleted = false
        ns:ShowUI(10)
        for _, row in ipairs(StorylinesFrame.storyList.rows) do
            if row:IsShown() and row.item and row.item.type == 'story' and row.item.story.name == 'Morbent Fel' then
                row:GetScript('OnClick')(row, 'LeftButton') break
            end
        end""")
    rows = lua_do("""local ns = ...
        local out = {}
        for _, row in ipairs(StorylinesFrame.storyList.rows) do
            if row:IsShown() and row.item and row.item.type == 'step' and row.item.index <= 3 then
                out[#out + 1] = row.item.questID .. '=' .. row.right:GetText()
            end
        end
        return table.concat(out, ' ')""")
    check("230=|cffffd100available|r" in rows and "262=" in rows and "262=|cffffd100available" not in rows,
          "the list marks only the quest you can pick up now as available (%s)" % rows)
    status = lua_do("local ns = ... return ns:GetQuestStatusText(262, ns.STATE_TODO)")
    check("Not available yet" in status, "locked quests explain why in their status")

    print("Reputation:")
    lua_do("""local ns = ...
        __faction, __race, __level = 'Alliance', 1, 25
        ns:UpdatePlayerInfo()
        __rep[47] = 4200 -- Ironforge: Friendly +1,200""")
    check(lua_do("local ns = ... return (ns:GetQuestAvailability(484))") == "reputation",
          "Young Crocolisk Skins (484, needs Honored with Ironforge) is blocked at Friendly")
    status = lua_do("local ns = ... return ns:GetQuestStatusText(484, ns.STATE_TODO)")
    check("Requires Honored with Ironforge (you are Friendly +1,200)" in status, "status explains it (%s)" % status)
    lua_do("""local ns = ... __npcGUID = 'Creature-0-1-0-1-2094-0000AAAA'
        ns.__fire('GOSSIP_SHOW')""")
    chat = lua.eval("table.concat(__printed, '\\n')")
    expected = ("James Halloran has |cffffd100[Young Crocolisk Skins]|r for you, but your reputation is not high "
                "enough: Requires Honored with Ironforge (you are Friendly +1,200).")
    check(expected in chat, "talking to the quest giver warns in chat")
    check(lua.eval("__errors[#__errors]") == "Reputation too low for Young Crocolisk Skins",
          "and shows red on-screen text")
    count = lua.eval("#__printed")
    lua_do("local ns = ... ns.__fire('GOSSIP_SHOW')")
    check(lua.eval("#__printed") == count, "the warning is not repeated for the same quest")
    lua_do("local ns = ... __rep[47] = 9000 ns.__fire('UPDATE_FACTION')")
    check(lua_do("local ns = ... return ns:GetQuestAvailability(484)") == "available", "reaching Honored unlocks it")
    lua_do("local ns = ... __secret = true __npcGUID = 'Creature-0-1-0-1-2094-0000AAAA' ns.__fire('QUEST_GREETING') __secret = false")
    check(True, "a hidden (secret) NPC identity is ignored without errors")
    # Follow-up warning after a turn-in (Horde, Alterac Valley: 7161 -> 7163 needs Friendly with Frostwolf Clan).
    lua_do("""local ns = ...
        __faction, __race, __level = 'Horde', 2, 55
        ns:UpdatePlayerInfo()
        __rep[729] = 500
        __completed[7161] = true
        ns.__fire('QUEST_TURNED_IN', 7161)""")
    chat = lua.eval("table.concat(__printed, '\\n')")
    check("Your reputation is not high enough for the next quest, |cffffd100[Rise and Be Recognized]|r: Requires "
          "Friendly with Frostwolf Clan (you are Neutral +500)." in chat, "turning in a quest warns about the follow-up")
    lua_do("local ns = ... ns.db.repWarnings = false __rep[47] = 0 __faction, __race = 'Alliance', 1 ns:UpdatePlayerInfo()")
    count = lua.eval("#__printed")
    lua_do("local ns = ... __npcGUID = 'Creature-0-1-0-1-1-0' ns.__fire('GOSSIP_SHOW')")
    check(lua.eval("#__printed") == count, "/stl repwarn turns the warnings off")
    lua_do("local ns = ... ns.db.repWarnings = true __rep[47] = 4200")
    lua_do("local ns = ... ns:ShowUI(11) ns:InspectQuest(484)")
    text = lua.eval("__visibleText(StorylinesInspector)")
    check("Reputation: Honored with Ironforge |cffff4040(you are Friendly +1,200)|r" in text,
          "the details panel shows the reputation requirement")
    lua_do("local ns = ... ns:CloseInspector()")

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
