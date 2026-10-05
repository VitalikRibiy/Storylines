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
    function methods:SetScale(v) self.__scale = v end
    function methods:GetScale() return self.__scale or 1 end
    function methods:SetBackdropColor(r, g, b, a) self.__bgAlpha = a end
    function methods:SetFont(file, size, flags) self.__font = { file, size, flags } end
    function methods:GetFont() if self.__font then return unpack(self.__font) end end
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
__skills = {}
function GetNumSkillLines() return #__skills end
function GetSkillLineInfo(i) local l = __skills[i] return l[1], l[2], l[3], l[4] end
function CreateFont(name) local f = newObject("Font", name); _G[name] = f; return f end
for _, name in ipairs({ "GameFontNormal", "GameFontHighlight", "GameFontHighlightSmall", "GameFontNormalLarge",
                        "GameFontDisable", "GameFontDisableSmall" }) do
    CreateFont(name):SetFont("Fonts\\FRIZQT__.TTF", name:find("Small") and 10 or 12, "")
end
-- Settings window: OpenToCategory shows the registered canvas.
__settingsPanels = {}
Settings = {
    RegisterCanvasLayoutCategory = function(frame, name)
        local id = #__settingsPanels + 1
        __settingsPanels[id] = frame
        return { ID = id, GetID = function(self) return self.ID end, name = name }
    end,
    RegisterAddOnCategory = function() end,
    OpenToCategory = function(id) __settingsPanels[id]:Hide() __settingsPanels[id]:Show() end,
}
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
__class = 1 -- Warrior
local classFiles = { "WARRIOR", "PALADIN", "HUNTER", "ROGUE", "PRIEST", "DEATHKNIGHT", "SHAMAN", "MAGE", "WARLOCK", "MONK", "DRUID" }
function UnitClass() return "Class", classFiles[__class], __class end
LOCALIZED_CLASS_NAMES_MALE = { PALADIN = "Paladin", ROGUE = "Rogue", WARRIOR = "Warrior" }
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
    horde_only = lua_do("""local ns = ...
        local n = 0
        for _, s in ipairs(ns:GetZoneStories(14)) do
            for _, step in ipairs(s.steps) do
                local id = ns:ResolveStep(step)
                if id and ns.Quests[id][3] == 2 then n = n + 1 end
            end
        end
        return n""")
    check(horde_only == 0, "Alliance sees no Horde-only quests in Durotar (only neutral ones)")

    print("Race filtering:")
    # Find a quest restricted to some Alliance races.
    lua_do("""local ns = ...
        for id, q in pairs(ns.Quests) do
            if q[4] and q[3] == 1 and not q[5] then __raceQuest = id; __raceList = q[4]; break end
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
                          ("+200|r Stormwind", "reputation reward"), ("Tunic of Westfall", "reward items"),
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
    # Alliance Alterac Valley: 7168 "Rise and Be Recognized" needs 7162 done and Friendly (3000) with
    # the Stormpike Guard (730); it is given by Lieutenant Haggerdin (13841).
    lua_do("""local ns = ...
        __faction, __race, __level = 'Alliance', 1, 60
        ns:UpdatePlayerInfo()
        __completed[7162] = true
        __rep[730] = 1200 -- Neutral +1,200
        ns.__fire('QUEST_LOG_UPDATE')""")
    check(lua_do("local ns = ... return (ns:GetQuestAvailability(7168))") == "reputation",
          "Rise and Be Recognized (7168, needs Friendly with Stormpike Guard) is blocked at Neutral")
    status = lua_do("local ns = ... return ns:GetQuestStatusText(7168, ns.STATE_TODO)")
    check("Requires Friendly with Stormpike Guard (you are Neutral +1,200)" in status, "status explains it (%s)" % status)
    lua_do("""local ns = ... __npcGUID = 'Creature-0-1-0-1-13841-0000AAAA'
        ns.__fire('GOSSIP_SHOW')""")
    chat = lua.eval("table.concat(__printed, '\\n')")
    expected = ("has |cffffd100[Rise and Be Recognized]|r for you, but your reputation is not high "
                "enough: Requires Friendly with Stormpike Guard (you are Neutral +1,200).")
    check(expected in chat, "talking to the quest giver warns in chat")
    check(lua.eval("__errors[#__errors]") == "Reputation too low for Rise and Be Recognized",
          "and shows red on-screen text")
    count = lua.eval("#__printed")
    lua_do("local ns = ... ns.__fire('GOSSIP_SHOW')")
    check(lua.eval("#__printed") == count, "the warning is not repeated for the same quest")
    lua_do("local ns = ... __rep[730] = 3000 ns.__fire('UPDATE_FACTION')")
    check(lua_do("local ns = ... return (ns:GetQuestAvailability(7168))") == "available", "reaching Friendly unlocks it")
    lua_do("local ns = ... __secret = true __npcGUID = 'Creature-0-1-0-1-13841-0000AAAA' ns.__fire('QUEST_GREETING') __secret = false")
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
    lua_do("local ns = ... ns.db.repWarnings = false __faction, __race = 'Alliance', 1 ns:UpdatePlayerInfo()")
    count = lua.eval("#__printed")
    lua_do("local ns = ... __rep[730] = 0 __npcGUID = 'Creature-0-1-0-1-13841-0' ns.__fire('GOSSIP_SHOW')")
    check(lua.eval("#__printed") == count, "/stl repwarn turns the warnings off")
    lua_do("local ns = ... ns.db.repWarnings = true __rep[730] = 1200 ns.__fire('UPDATE_FACTION')")
    lua_do("local ns = ... ns:ShowUI(2597) ns:InspectQuest(7168)")
    text = lua.eval("__visibleText(StorylinesInspector)")
    check("Reputation: Friendly with Stormpike Guard |cffff4040(you are Neutral +1,200)|r" in text,
          "the details panel shows the reputation requirement")
    check("You can't get this quest yet" in text and "You need |cffffffff1,800|r more reputation with Stormpike Guard." in text,
          "the quest details show a warning box with how much reputation is missing")
    check("Reputation too low - see above" in text, "the status line points to the warning instead of repeating it")
    lua_do("local ns = ... __rep[730] = 3000 ns.__fire('UPDATE_FACTION') ns:InspectQuest(7168)")
    text = lua.eval("__visibleText(StorylinesInspector)")
    check("You can't get this quest yet" not in text, "the warning disappears once the reputation is reached")
    # Storyline overview (Horde, Alterac Valley storyline containing 7163 which needs Friendly with Frostwolf Clan).
    lua_do("""local ns = ...
        __faction, __race = 'Horde', 2
        ns:UpdatePlayerInfo()
        __rep[729] = 500
        ns:InspectStory(ns.storiesByQuest[7163][1])""")
    text = lua.eval("__visibleText(StorylinesInspector)")
    check("Reputation too low for" in text and "Rise and Be Recognized|r: Requires Friendly with Frostwolf Clan" in text,
          "the storyline overview warns about quests your reputation is too low for")
    lua_do("local ns = ... __faction, __race = 'Alliance', 1 ns:UpdatePlayerInfo() ns:CloseInspector()")
    # Storyline rows in the main list get a warning icon (Alliance Alterac Valley storyline containing 7168).
    lua_do("local ns = ... __rep[730] = 1200 ns.__fire('UPDATE_FACTION') ns.db.hideCompleted = false ns:ShowUI(2597)")
    def story_row_text():
        return lua_do("""local ns = ...
            for _, row in ipairs(StorylinesFrame.storyList.rows) do
                if row:IsShown() and row.item and row.item.type == 'story' and row.item.story == ns.storiesByQuest[7168][1] then
                    return row.text:GetText()
                end
            end""")
    row_text = story_row_text()
    check(row_text and "UI-Dialog-Icon-AlertNew" in row_text,
          "the storyline row shows a reputation warning icon (%s)" % row_text)
    lua_do("""local ns = ...
        for _, row in ipairs(StorylinesFrame.storyList.rows) do
            if row:IsShown() and row.item and row.item.type == 'story' then row:GetScript('OnEnter')(row) end
        end""")
    lua_do("local ns = ... __rep[730] = 3000 ns.__fire('UPDATE_FACTION') ns:RefreshUI()")
    check("AlertNew" in (story_row_text() or ""),
          "at Friendly the icon stays: later quests in the storyline need Honored and more")
    lua_do("local ns = ... __rep[730] = 42999 ns.__fire('UPDATE_FACTION') ns:RefreshUI()")
    check("AlertNew" not in (story_row_text() or ""), "the icon goes away once every requirement is met")
    lua_do("local ns = ... __level = 25")

    print("Faction-specific names:")
    names = lua_do("""local ns = ...
        local s = ns.storiesByQuest[92514][1]
        __faction, __race = 'Horde', 2 ns:UpdatePlayerInfo()
        local h = s.name
        __faction, __race = 'Alliance', 1 ns:UpdatePlayerInfo()
        return h .. '|' .. s.name""")
    check(names == "The Fate of Zephras|The Fate of Zephras", "Zephras Isle's main storyline is The Fate of Zephras (%s)" % names)
    names = lua_do("""local ns = ...
        local s = ns.storiesByQuest[1253] and ns.storiesByQuest[1253][1]
        local out = {}
        for _, f in ipairs({ {'Horde', 2}, {'Alliance', 1} }) do
            __faction, __race = f[1], f[2] ns:UpdatePlayerInfo()
            for _, st in ipairs(ns:GetZoneStories(1637)) do
                if st.name:find('A Donation of Runecloth') then out[#out + 1] = f[1] .. ':' .. st.name end
            end
        end
        return table.concat(out, ' / ')""")
    check("(Rashona Straglash)" in names or "(Vehena)" in names,
          "duplicate storyline names for one faction get the quest giver added (%s)" % names)
    lua_do("local ns = ... __faction, __race = 'Alliance', 1 ns:UpdatePlayerInfo()")

    print("Class quests:")
    classes = lua_do("""local ns = ...
        local function classZones()
            local out = {}
            for areaID, zone in pairs(ns.Zones) do
                if zone.group == 5 then
                    local d, t = ns:GetZoneProgress(areaID)
                    if t > 0 then out[#out + 1] = ns:GetZoneName(areaID) end
                end
            end
            table.sort(out)
            return table.concat(out, ',')
        end
        __faction, __race, __class = 'Alliance', 1, 2 ns:UpdatePlayerInfo()   -- Human Paladin
        local paladin = classZones()
        local tome = ns:IsQuestForPlayer(1642)
        __class = 4 ns:UpdatePlayerInfo()                                        -- Human Rogue
        local rogue = classZones()
        local tomeRogue = ns:IsQuestForPlayer(1642)
        __class = 1 ns:UpdatePlayerInfo()
        return paladin .. '|' .. rogue .. '|' .. tostring(tome) .. '|' .. tostring(tomeRogue)""")
    paladin, rogue, tome, tome_rogue = classes.split("|")
    check(paladin == "Paladin", "a paladin sees only the Paladin entry under Class Quests (%s)" % paladin)
    check(rogue == "Rogue", "a rogue sees only the Rogue entry (%s)" % rogue)
    check(tome == "true" and tome_rogue == "false", "paladin quests (The Tome of Divinity) are hidden from other classes")
    leaked = lua_do("""local ns = ...
        __faction, __race, __class = 'Alliance', 1, 2 ns:UpdatePlayerInfo()
        local n = 0
        for areaID in pairs(ns.Zones) do
            for _, s in ipairs(ns:GetZoneStories(areaID)) do
                for _, step in ipairs(s.steps) do
                    local id = ns:ResolveStep(step)
                    local mask = id and ns.Quests[id][5]
                    if mask and math.floor(mask / 2) % 2 == 0 then n = n + 1 end
                end
            end
            for _, e in ipairs(ns:GetZoneSideQuests(areaID)) do
                local mask = ns.Quests[e.questID][5]
                if mask and math.floor(mask / 2) % 2 == 0 then n = n + 1 end
            end
        end
        __class = 1 ns:UpdatePlayerInfo()
        return n""")
    check(leaked == 0, "no other class's quest shows anywhere for a paladin (%d found)" % leaked)
    sw = lua_do("""local ns = ...
        __faction, __race, __class = 'Alliance', 1, 2 ns:UpdatePlayerInfo()
        local found
        for _, s in ipairs(ns:GetZoneStories(1519)) do
            if s.zone ~= 1519 and ns.Zones[s.zone].group == 5 then found = s.name end
        end
        __class = 1 ns:UpdatePlayerInfo()
        return found""")
    check(sw is not None, "paladin storylines also show in Stormwind City, where they start (%s)" % sw)
    shared = lua_do("""local ns = ...
        -- The Forging of Quel'Serrar is for warriors and paladins: each sees it as their own class's.
        local out = {}
        for _, cls in ipairs({ 2, 1 }) do
            __faction, __race, __class = 'Alliance', 1, cls ns:UpdatePlayerInfo()
            local area = 100000 + 2 ^ (cls - 1)
            for _, s in ipairs(ns:GetZoneStories(area)) do
                if s.name == "The Forging of Quel'Serrar" then
                    out[#out + 1] = ns:GetZoneName(area) .. '=' .. ns:GetZoneName(s.zone)
                end
            end
        end
        __class = 1 ns:UpdatePlayerInfo()
        return table.concat(out, ',')""")
    check(shared == "Paladin=Paladin,Warrior=Warrior",
          "a quest for several classes belongs to the player's own class (%s)" % shared)

    starts = lua_do("""local ns = ...
        -- Durotar's "Burning Blade Medallion" starts with a pick-one of two warlock quests, one in
        -- Tirisfal Glades (Undead) and one in Durotar (Orc, Troll): it is listed in Tirisfal Glades
        -- only for Undead warlocks, and in Durotar for everyone.
        local function listed(areaID)
            for _, s in ipairs(ns:GetZoneStories(areaID)) do
                if s.name == 'Burning Blade Medallion' then return 'y' end
            end
            return 'n'
        end
        local out = {}
        for _, who in ipairs({ { 5, 1 }, { 5, 9 }, { 2, 9 } }) do
            __faction, __race, __class = 'Horde', who[1], who[2] ns:UpdatePlayerInfo()
            out[#out + 1] = listed(85) .. listed(14)
        end
        -- The warlock step shows the variant from your starting zone.
        local story
        for _, s in ipairs(ns:GetZoneStories(14)) do if s.name == 'Burning Blade Medallion' then story = s end end
        __race = 5 ns:UpdatePlayerInfo()
        local undead = ns:ResolveStep(story.steps[1])
        __race = 2 ns:UpdatePlayerInfo()
        local orc = ns:ResolveStep(story.steps[1])
        __faction, __race, __class = 'Alliance', 1, 1 ns:UpdatePlayerInfo()
        return table.concat(out, ' ') .. ' ' .. undead .. ' ' .. orc""")
    check(starts.startswith("ny yy ny "),
          "a storyline is listed where you start it: Undead warlocks in Tirisfal, others not (%s)" % starts)
    check(starts.endswith(" 1470 1485"), "a pick-one step shows the variant from your starting zone (%s)" % starts)

    print("Dungeons:")
    wc = lua_do("""local ns = ...
        __faction, __race, __class = 'Horde', 2, 1 ns:UpdatePlayerInfo()
        local names = {}
        for _, s in ipairs(ns:GetZoneStories(718)) do names[#names + 1] = s.name end
        local _, total, _, sideTotal = ns:GetZoneProgress(718)
        ns:ShowUI(718)
        local listed = false
        for _, item in ipairs(StorylinesFrame.zoneList.items) do
            if item.areaID == 718 then listed = true end
        end
        __faction, __race = 'Alliance', 1 ns:UpdatePlayerInfo()
        return table.concat(names, ',') .. '|' .. total .. '|' .. sideTotal .. '|' .. tostring(listed)""")
    names, total, side_total, listed = wc.split("|")
    check("Leaders of the Fang" in names, "Wailing Caverns lists the storylines that lead into it (%s)" % names)
    check(listed == "true", "Wailing Caverns is in the zone list")
    dm = lua_do("""local ns = ...
        for _, s in ipairs(ns:GetZoneStories(1581)) do if s.name == 'The Defias Brotherhood' then return true end end
        return false""")
    check(dm, "The Deadmines lists The Defias Brotherhood")
    side_only = lua_do("""local ns = ...
        -- a zone with side quests but no storylines for this character must still be listed
        for areaID, zone in pairs(ns.Zones) do
            local _, t, _, st = ns:GetZoneProgress(areaID)
            if t == 0 and st > 0 and ns:IsZoneForPlayer(zone) then
                ns:ShowUI(areaID)
                for _, row in ipairs(StorylinesFrame.zoneList.rows) do
                    if row:IsShown() and row.item and row.item.areaID == areaID then return row.right:GetText() end
                end
                return 'not listed: ' .. zone.name
            end
        end
        return 'none'""")
    check(side_only == "none" or side_only.startswith("|cff909090side|r"),
          "zones with only side quests are listed with their side quest count (%s)" % side_only)

    dungeon_rows = lua_do("""local ns = ...
        __faction, __race, __class = 'Horde', 2, 1 ns:UpdatePlayerInfo()
        ns.db.collapsedGroups[3] = false
        ns:ShowUI(718) ns:RefreshUI()
        local names, empty = {}, nil
        for _, item in ipairs(StorylinesFrame.zoneList.items) do
            if item.type == 'zone' and ns.Zones[item.areaID].group == 3 then
                names[#names + 1] = item.name
                if item.name == 'City of Dalaran' then empty = item end
            end
        end
        local text = 'not shown'
        ns:ShowUI(empty.areaID)
        for _, row in ipairs(StorylinesFrame.zoneList.rows) do
            if row:IsShown() and row.item and row.item.areaID == empty.areaID then text = row.right:GetText() end
        end
        local note = __visibleText(StorylinesFrame)
        text = text .. (note:find('No quests are known for this dungeon yet', 1, true) and ' +note' or '')
        __faction, __race = 'Alliance', 1 ns:UpdatePlayerInfo()
        return #names .. '#' .. text .. '#' .. table.concat(names, ',')""")
    count, empty_text, names = dungeon_rows.split("#", 2)
    check(count == "35", "the Dungeons & Raids group lists all 35 dungeons and raids (%s)" % count)
    for name in ("Onyxia's Lair", "Dire Maul", "City of Dalaran", "Alcaz Prison", "Shaper's Terrace"):
        check(name in names, "%s is listed" % name)
    check(names.count("Dire Maul") == 1, "Dire Maul is listed once")
    check("Deeprun Tram" not in names, "Deeprun Tram is not a dungeon")
    check("no quests yet" in empty_text, "dungeons without known quests say so in the list (%s)" % empty_text)
    check("+note" in empty_text, "and in the storyline panel")

    print("Settings:")
    lua_do("""local ns = ...
        __faction, __race, __class, __level = 'Alliance', 1, 1, 20 ns:UpdatePlayerInfo()
        ns:ShowUI(40) ns:RefreshUI()""")
    page = lua_do("""local ns = ...
        ns:OpenOptions()
        return __visibleText(StorylinesOptionsPanel)""")
    for needle in ("Background opacity", "Text size", "Details panel", "Lock window", "Reputation warnings",
                   "Hide gray (too low level) quests", "Sort storylines by", "Show quest IDs", "Ignored: 0 storylines",
                   "All Storylines settings", "Show minimap button", "Waypoints"):
        check(needle in page, "the options page shows " + needle)
    window = lua_do("""local ns = ...
        local db, f = ns.db, StorylinesFrame
        db.scale, db.bgAlpha, db.locked, db.escClose, db.textSize = 1.2, 0.4, true, false, 'large'
        ns:ApplySettings()
        local inEsc = false
        for _, name in ipairs(UISpecialFrames) do inEsc = inEsc or name == 'StorylinesFrame' end
        local _, size = StorylinesGameFontHighlight:GetFont()
        local out = { f:GetScale(), f.__bgAlpha, tostring(f.resizeGrip:IsShown()), tostring(inEsc), size }
        db.scale, db.bgAlpha, db.locked, db.escClose, db.textSize = 1, 1, false, true, 'normal'
        ns:ApplySettings()
        inEsc = false
        for _, name in ipairs(UISpecialFrames) do inEsc = inEsc or name == 'StorylinesFrame' end
        out[#out + 1] = tostring(inEsc)
        _, out[#out + 1] = StorylinesGameFontHighlight:GetFont()
        return table.concat(out, ' ')""")
    check(window == "1.2 0.4 false false 13.8 true 12",
          "scale, opacity, lock, Escape and text size apply to the window (%s)" % window)
    sized = lua_do("""local ns = ...
        local f = StorylinesFrame
        f:SetSize(900, 600)
        f.resizeGrip:GetScript('OnMouseUp')(f.resizeGrip)
        local saved = ns.db.size[1] .. 'x' .. ns.db.size[2]
        ns.db.size, ns.db.position = nil, nil
        ns:ApplySettings()
        return saved .. ' ' .. f:GetWidth() .. 'x' .. f:GetHeight()""")
    check(sized == "900x600 780x540", "the window size is remembered and can be reset (%s)" % sized)

    def story_names(setup):
        return lua_do("""local ns = ...
            %s
            ns:RefreshUI()
            local out = {}
            for _, item in ipairs(StorylinesFrame.storyList.items) do
                if item.type == 'story' then out[#out + 1] = item.story.name
                elseif item.type == 'note' then out[#out + 1] = 'NOTE:' .. item.text end
            end
            ns.db.hideTrivial, ns.db.maxLevelsAbove, ns.db.sortBy, __level = false, 0, 'level', 20
            return table.concat(out, '|')""" % setup)
    by_level = story_names("")
    check(by_level and "NOTE" not in by_level, "Westfall lists its storylines with no filter note")
    trivial = story_names("ns.db.hideTrivial, __level = true, 60")
    # The Defias Brotherhood was started by earlier checks: started storylines always stay listed.
    check(trivial.startswith("The Defias Brotherhood|NOTE:%d more storylines hidden by your level filters.|NOTE:" % (
          by_level.count("|"))) and "side quests hidden" in trivial,
          "gray storylines and side quests are hidden for a level 60, except started ones (%s)" % trivial[:120])
    above = story_names("ns.db.maxLevelsAbove, __level = 3, 6")
    check("hidden by your level filters" in above and above.count("|") < by_level.count("|"),
          "storylines far above your level are hidden (%s)" % above[:80])
    side = lua_do("""local ns = ...
        -- Westfall side quests: all listed normally, hidden at level 6 with a 3-level limit
        local function count(setup)
            ns.db.maxLevelsAbove, __level = setup[1], setup[2]
            ns:RefreshUI()
            local n, note = 0, ''
            for _, item in ipairs(StorylinesFrame.storyList.items) do
                if item.type == 'side' then n = n + 1 end
                if item.type == 'note' and item.text:find('side quest') then note = item.text end
            end
            return n, note
        end
        local before = count({ 0, 20 })
        local after, note = count({ 3, 6 })
        ns.db.maxLevelsAbove, __level = 0, 20
        return before .. '>' .. after .. ' ' .. note""")
    before, after = map(int, side.split(" ")[0].split(">"))
    check(after < before and "side quests hidden" in side,
          "the level filters hide side quests too (%s)" % side)
    by_name = [n for n in story_names("ns.db.sortBy = 'name'").split("|") if not n.startswith("NOTE")]
    check(by_name == sorted(by_name) and len(by_name) > 3, "storylines can be sorted by name")
    ids = lua_do("""local ns = ...
        ns.db.showQuestIDs = true
        local line = ns:FormatQuestLine(166)
        ns.db.showQuestIDs = false
        return line""")
    check("#166" in ids, "quest IDs are shown when enabled (%s)" % ids)
    finished = lua_do("""local ns = ...
        -- finish everything in Westfall, then select another zone: Westfall disappears from the list
        local function listed(areaID)
            for _, item in ipairs(StorylinesFrame.zoneList.items) do
                if item.areaID == areaID then return true end
            end
            return false
        end
        for _, story in ipairs(ns:GetZoneStories(40)) do
            for _, step in ipairs(story.steps) do for _, id in ipairs(ns.StepIDs(step)) do __completed[id] = true end end
        end
        for _, entry in ipairs(ns:GetZoneSideQuests(40)) do __completed[entry.questID] = true end
        ns:InvalidateProgress()
        ns.db.hideFinishedZones = true
        ns:ShowUI(12) ns:RefreshUI()
        local hidden = not listed(40)
        ns:ShowUI(40) ns:RefreshUI()
        local selectedShown = listed(40)
        ns.db.hideFinishedZones = false
        __completed = {} ns:InvalidateProgress()
        return tostring(hidden) .. ' ' .. tostring(selectedShown)""")
    check(finished == "true true", "finished zones can be hidden, except the selected one (%s)" % finished)
    warn = lua_do("""local ns = ...
        local before, errors = #__printed, #__errors
        ns.db.repWarnings = 'chat'
        ns:WarnReputation(999001, { factionID = 72, required = 9000, current = 0 }, 'x ', '')
        ns.db.repWarnings = 'screen'
        ns:WarnReputation(999002, { factionID = 72, required = 9000, current = 0 }, 'x ', '')
        ns.db.repWarnings = 'off'
        ns:WarnReputation(999003, { factionID = 72, required = 9000, current = 0 }, 'x ', '')
        ns.db.repWarnings = 'both'
        return (#__printed - before) .. ' ' .. (#__errors - errors)""")
    check(warn == "1 1", "reputation warnings can go to chat only, screen only, or nowhere (%s)" % warn)
    dropdown = lua_do("""local ns = ...
        -- open the "Sort storylines by" dropdown and pick Name
        local function find(f, text)
            for _, c in ipairs(f.__children or {}) do
                if c.text and c.text.__text == text and c.__shown then return c end
                local found = find(c, text) if found then return found end
            end
        end
        find(StorylinesOptionsPanel, 'Level'):GetScript('OnClick')(find(StorylinesOptionsPanel, 'Level'))
        find(StorylinesOptionsMenu, 'Name'):GetScript('OnClick')()
        local picked = ns.db.sortBy
        ns.db.sortBy = 'level'
        return picked""")
    check(dropdown == "name", "dropdowns on the options page change the setting (%s)" % dropdown)
    reset = lua_do("""local ns = ...
        ns.db.ignoredQuests[123] = true
        ns.db.scale, ns.db.minimap.hide, ns.db.minimap.angle = 1.3, true, 90
        ns:ResetSettings() ns:ApplySettings()
        local out = ns.db.scale .. ' ' .. tostring(ns.db.minimap.hide) .. ' ' .. ns.db.minimap.angle .. ' '
            .. tostring(ns.db.ignoredQuests[123])
        ns:ClearIgnored()
        return out""")
    check(reset == "1 false 90 true", "reset to defaults keeps ignored quests and the minimap position (%s)" % reset)

    print("Search:")
    found = lua_do("""local ns = ...
        __faction, __race, __class, __level = 'Alliance', 1, 1, 20 ns:UpdatePlayerInfo()
        SlashCmdList.STORYLINES('find defias brotherhood')
        local out = {}
        for _, item in ipairs(StorylinesFrame.storyList.items) do
            if item.search then
                out[#out + 1] = (item.questID and (item.questID .. ':' .. ns:GetQuestName(item.questID)) or item.story.name)
                    .. '@' .. (item.storyName or '-') .. '@' .. ns:GetZoneName(item.areaID)
            end
        end
        return StorylinesFrame.zoneTitle:GetText() .. '#' .. table.concat(out, ';')""")
    print("   " + found[:300])
    title, results = found.split("#", 1)
    check(title == "Search: |cffffffffdefias brotherhood|r", "/stl find shows a search (%s)" % title)
    check("The Defias Brotherhood@-@Westfall" in results, "storylines are found by name")
    check("166:The Defias Brotherhood@The Defias Brotherhood@Westfall" in results,
          "a quest result names its storyline and zone")
    opened = lua_do("""local ns = ...
        -- click the quest result: its zone opens, the storyline is expanded and the quest inspected
        local target
        for _, item in ipairs(StorylinesFrame.storyList.items) do
            if item.search and item.questID == 166 then target = item end
        end
        local row = StorylinesFrame.storyList.rows[1]
        row.item = target
        row:GetScript('OnClick')(row, 'LeftButton')
        local stepShown = false
        for _, item in ipairs(StorylinesFrame.storyList.items) do
            if item.type == 'step' and item.questID == 166 then stepShown = true end
        end
        return tostring(ns.searchText) .. ' ' .. ns:GetZoneName(ns.selectedArea) .. ' '
            .. tostring(ns:GetInspected().questID) .. ' ' .. tostring(stepShown) .. ' [' .. StorylinesFrame.search:GetText() .. ']'""")
    check(opened == "nil Westfall 166 true []", "clicking a result opens its zone, storyline and quest (%s)" % opened)
    none = lua_do("""local ns = ...
        ns:Search('zzzzqq')
        local note = StorylinesFrame.storyList.items[1].text
        ns:ClearSearch()
        return note""")
    check(none == "No zone, storyline or quest found for your character.", "an empty search says so")
    zone_hit = lua_do("""local ns = ...
        -- dungeons and zones are found by name; clicking one opens it
        ns:Search('wailing')
        local target, names = nil, {}
        for _, item in ipairs(StorylinesFrame.storyList.items) do
            if item.type == 'zoneResult' then
                names[#names + 1] = item.name
                if item.name == 'Wailing Caverns' then target = item end
            end
        end
        local row = StorylinesFrame.storyList.rows[1]
        row.item = target
        row:GetScript('OnClick')(row, 'LeftButton')
        return table.concat(names, ',') .. ' -> ' .. ns:GetZoneName(ns.selectedArea) .. ' ' .. tostring(ns.searchText)""")
    check(zone_hit == "Wailing Caverns -> Wailing Caverns nil", "dungeons are found by name and open on click (%s)" % zone_hit)
    westf = lua_do("""local ns = ...
        ns:Search('westf')
        local first = StorylinesFrame.storyList.items[2]
        ns:ClearSearch()
        return first.type .. ' ' .. first.name""")
    check(westf == "zoneResult Westfall", "zones are listed first in the results (%s)" % westf)
    other = lua_do("""local ns = ...
        -- Horde-only quests aren't found by an Alliance character
        ns:Search('Vile Familiars')
        local n = 0
        for _, item in ipairs(StorylinesFrame.storyList.items) do if item.search then n = n + 1 end end
        ns:ClearSearch()
        return n""")
    check(other == 0, "search only finds quests for your character (%s found)" % other)

    print("Professions:")
    prof = lua_do("""local ns = ...
        local function groupEntries()
            ns.db.collapsedGroups[6] = false
            ns:RefreshUI()
            local out = {}
            for _, item in ipairs(StorylinesFrame.zoneList.items) do
                if item.type == 'zone' and ns.Zones[item.areaID].group == 6 then out[#out + 1] = item.name end
            end
            return table.concat(out, ',')
        end
        local result = {}
        -- Classic skill list: no professions, then Cooking 40.
        __skills = {}
        ns:UpdateProfessions()
        result[#result + 1] = groupEntries() .. '/' .. tostring(ns:IsQuestForPlayer(90))
        __skills = { { 'Professions', true }, { 'Cooking', false, false, 40 } }
        ns:UpdateProfessions()
        result[#result + 1] = groupEntries() .. '/' .. tostring(ns:IsQuestForPlayer(90))
            .. '/' .. table.concat({ ns:GetQuestAvailability(90) and ns:GetQuestAvailability(90) }, '')
        local _, detail = ns:GetQuestAvailability(90)
        result[#result + 1] = detail and (detail.level .. '>' .. detail.rank) or 'nil'
        ns.db.showAllProfessions = true
        ns:InvalidateProgress()
        local all = groupEntries()
        result[#result + 1] = select(2, all:gsub(',', ',')) + 1
        ns.db.showAllProfessions = false
        __skills = {}
        ns:UpdateProfessions()
        return table.concat(result, ' ')""")
    print("   " + str(prof))
    parts = str(prof).split(" ")
    check(parts[0] == "/false", "no Professions entries and no profession quests without professions (%s)" % parts[0])
    check(parts[1] == "Cooking/true/skill", "a cook sees Cooking and its quests (%s)" % parts[1])
    check(parts[2] == "50>40", "a profession quest needs the skill level (%s)" % parts[2])
    check(parts[3] == "12", "all 12 professions can be shown (%s)" % parts[3])
    detail_text = lua_do("""local ns = ...
        __skills = { { 'Cooking', false, false, 40 } }
        ns:UpdateProfessions()
        ns:InspectQuest(90)
        local text = __visibleText(StorylinesInspector)
        __skills = {}
        ns:UpdateProfessions()
        ns:CloseInspector()
        return text""")
    check("Profession: Cooking 50 |cffff4040(you have 40)|r" in detail_text, "quest details show the profession requirement")
    modern = lua_do("""local ns = ...
        -- Modern clients: GetProfessions / GetProfessionInfo give skill line IDs directly.
        GetProfessions = function() return 3, nil, nil, nil, 5 end
        GetProfessionInfo = function(i) if i == 3 then return 'Blacksmithing', 0, 120, 150, 0, 0, 164 end
            return 'Cooking', 0, 60, 75, 0, 0, 185 end
        ns:UpdateProfessions()
        local out = tostring(ns:GetProfessionRank(164)) .. ',' .. tostring(ns:GetProfessionRank(185)) .. ','
            .. tostring(ns:GetProfessionRank(197))
        GetProfessions, GetProfessionInfo = nil, nil
        ns:UpdateProfessions()
        return out""")
    check(modern == "120,60,false", "professions are read from the modern API too (%s)" % modern)

    order = lua_do("""local ns = ...
        local story = ns.storyByKey[1062]
        local out = {}
        for i = 1, 3 do out[#out + 1] = ns.StepIDs(story.steps[i])[1] end
        return table.concat(out, ',')""")
    check(order == "1062,1068,1063", "a one-quest side branch is listed right after the quest that unlocks it (%s)" % order)
    tree = lua_do("""local ns = ...
        __faction, __race, __class = 'Horde', 6, 1 ns:UpdatePlayerInfo()
        local function show(story)
            local depth, start = ns:GetStoryTree(story)
            local out = {}
            for i, step in ipairs(story.steps) do
                if depth[i] then out[#out + 1] = (start[i] and '>' or '') .. depth[i] end
            end
            return table.concat(out, ' ')
        end
        local result = show(ns.storyByKey[1062])
        -- printed for a look at other branching storylines
        local samples = {}
        for _, key in ipairs({ 1102, 7, 1066 }) do
            local s = ns.storyByKey[key]
            if s then
                local depth, start = ns:GetStoryTree(s)
                local lines = {}
                for i, step in ipairs(s.steps) do
                    local q = ns:ResolveStep(step)
                    if q then lines[#lines + 1] = string.rep('  ', depth[i]) .. (start[i] and '+ ' or '') .. ns:GetQuestName(q) end
                end
                samples[#samples + 1] = s.name .. ': ' .. table.concat(lines, ' / ')
            end
        end
        __faction, __race, __class = 'Alliance', 1, 1 ns:UpdatePlayerInfo()
        return result .. '#' .. table.concat(samples, ' || ')""")
    collapse = lua_do("""local ns = ...
        -- The Elder Crone's line is one row you can open and close.
        __faction, __race, __class = 'Horde', 6, 1 ns:UpdatePlayerInfo()
        local function rows()
            local out = {}
            for _, item in ipairs(StorylinesFrame.storyList.items) do
                if item.story == ns.storyByKey[1062] then
                    if item.type == 'branch' then out[#out + 1] = 'B' .. item.depth .. (item.open and '-' or '+') .. item.count
                    elseif item.type == 'step' then out[#out + 1] = item.questID .. '@' .. item.depth end
                end
            end
            return table.concat(out, ' ')
        end
        ns:ShowUI(1638)
        for _, row in ipairs(StorylinesFrame.storyList.rows) do
            if row.item and row.item.type == 'story' and row.item.story.key == 1062 then
                row:GetScript('OnClick')(row, 'LeftButton') break
            end
        end
        local closed = rows()
        local branch
        for _, item in ipairs(StorylinesFrame.storyList.items) do if item.type == 'branch' then branch = item end end
        local row = StorylinesFrame.storyList.rows[1]
        row.item = branch
        row:GetScript('OnClick')(row, 'LeftButton')
        local opened = rows()
        __faction, __race, __class = 'Alliance', 1, 1 ns:UpdatePlayerInfo()
        return closed .. ' | ' .. opened""")
    check(collapse == "1062@0 1068@1 B1+6 | 1062@0 1068@1 B1-6 1063@2 1064@2 1065@2 1066@2 1067@2 1086@2",
          "a line of several quests is one row that opens to show its quests (%s)" % collapse)
    tree_result, samples = tree.split("#", 1)
    print("   " + samples)
    check(tree_result == "0 >1 >1 1 1 1 1 1",
          "a quest that opens two lines shows two indented branches (%s)" % tree_result)

    sweep = lua_do("""local ns = ...
        -- Every storyline, for characters of every faction, race and class: the tree must show each
        -- quest once (all lines open) in the storyline's order, number them 1..n, and closed lines
        -- must hide exactly their own quests.
        local chars = {}
        for _, race in ipairs({ 1, 3, 4, 7 }) do for _, cls in ipairs({ 1, 2, 3, 4, 5, 8, 9, 11 }) do
            chars[#chars + 1] = { 'Alliance', race, cls } end end
        for _, race in ipairs({ 2, 5, 6, 8 }) do for _, cls in ipairs({ 1, 3, 4, 5, 7, 8, 9, 11 }) do
            chars[#chars + 1] = { 'Horde', race, cls } end end
        local problems, views, withLines, deepest = {}, 0, {}, 0
        ns.db.showAllProfessions = true
        for _, c in ipairs(chars) do
            __faction, __race, __class = c[1], c[2], c[3]
            ns:UpdatePlayerInfo()
            for key, story in pairs(ns.storyByKey) do
                local expected = {}
                for _, step in ipairs(story.steps) do
                    local q = ns:ResolveStep(step)
                    if q then expected[#expected + 1] = q end
                end
                if #expected > 0 then
                    views = views + 1
                    local who = story.name .. ' (' .. c[1] .. ' race ' .. c[2] .. ' class ' .. c[3] .. ')'
                    local open, closed = {}, {}
                    ns.AddStorySteps(open, story, true)
                    ns.AddStorySteps(closed, story)
                    local shown = {}
                    for _, it in ipairs(open) do
                        if it.type == 'step' then
                            shown[#shown + 1] = it
                            deepest = math.max(deepest, it.depth)
                        else
                            withLines[key] = true
                        end
                    end
                    local ok = #shown == #expected
                    for i, it in ipairs(shown) do
                        ok = ok and it.questID == expected[i] and it.index == i
                    end
                    if not ok then problems[#problems + 1] = who .. ': open tree differs' end
                    local visible, hidden = 0, 0
                    for _, it in ipairs(closed) do
                        if it.type == 'step' then visible = visible + 1
                        elseif not it.open then hidden = hidden + it.count end
                    end
                    if visible + hidden ~= #expected then problems[#problems + 1] = who .. ': closed tree loses quests' end
                end
            end
        end
        ns.db.showAllProfessions = false
        __faction, __race, __class = 'Alliance', 1, 1 ns:UpdatePlayerInfo()
        local count = 0 for _ in pairs(withLines) do count = count + 1 end
        return #problems .. '#' .. views .. '#' .. count .. '#' .. deepest .. '#' .. table.concat(problems, '; ', 1, math.min(#problems, 5))""")
    n_problems, views, with_lines, deepest, examples = sweep.split("#", 4)
    print("   %s storyline views checked, %s storylines have lines to open and close, deepest indent %s" % (
        views, with_lines, deepest))
    check(n_problems == "0", "the tree shows every quest of every storyline once, for every character (%s)" % (
        examples or "no problems"))

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
