local ADDON_NAME, ns = ...

Storylines = ns -- global handle for other addons and /dump

ns.STATE_TODO, ns.STATE_ACTIVE, ns.STATE_READY, ns.STATE_DONE = 0, 1, 2, 3

ns.GROUP_NAMES = {
    [1] = "Eastern Kingdoms",
    [2] = "Kalimdor",
    [3] = "Dungeons & Raids",
    [4] = "Battlegrounds",
}

local CHAT_PREFIX = "|cff33ff99Storylines:|r "

local defaults = {
    hideCompleted = false,
    showSide = true,
    autoZone = true,
    announce = true,
    repWarnings = true,
    showIgnored = false,
    minimap = { angle = 215, hide = false },
    ignoredQuests = {},
    ignoredStories = {},
    collapsedGroups = { [3] = true, [4] = true },
}

local function applyDefaults(db, src)
    for k, v in pairs(src) do
        if db[k] == nil then
            if type(v) == "table" then
                db[k] = {}
                applyDefaults(db[k], v)
            else
                db[k] = v
            end
        elseif type(v) == "table" and type(db[k]) == "table" then
            applyDefaults(db[k], v)
        end
    end
end

function ns:Print(msg)
    DEFAULT_CHAT_FRAME:AddMessage(CHAT_PREFIX .. msg)
end

---------------------------------------------------------------------------
-- Data index
---------------------------------------------------------------------------

ns.storiesByQuest = {} -- questID -> { story, ... }
ns.storyByKey = {}     -- story key (lowest quest ID) -> story
ns.sideZoneByQuest = {} -- side quest ID -> areaID it is filed under
ns.areaByMap = {}      -- uiMapID -> areaID
ns.areaByName = {}     -- lower-case zone name -> areaID

local function stepIDs(step)
    if type(step) == "table" then
        return step
    end
    return { step }
end
ns.StepIDs = stepIDs

function ns:BuildIndex()
    for areaID, zone in pairs(self.Zones) do
        zone.id = areaID
        for i, raw in ipairs(zone.stories) do
            local story = { name = raw[1], steps = raw[2], zone = areaID }
            local key
            for _, step in ipairs(story.steps) do
                for _, questID in ipairs(stepIDs(step)) do
                    key = (not key or questID < key) and questID or key
                    local list = self.storiesByQuest[questID]
                    if not list then
                        list = {}
                        self.storiesByQuest[questID] = list
                    end
                    list[#list + 1] = story
                end
            end
            story.key = key
            zone.stories[i] = story
            self.storyByKey[key] = story
        end
        for _, step in ipairs(zone.side) do
            self.sideZoneByQuest[stepIDs(step)[1]] = areaID
        end
        if zone.uiMap and zone.uiMap > 0 then
            self.areaByMap[zone.uiMap] = areaID
        end
        self.areaByName[zone.name:lower()] = areaID
    end
    -- Storylines and side quests filed under another zone but picked up here (zone.also / zone.alsoSide)
    -- are listed in both places. Merge them into level order.
    local function firstLevel(step)
        local q = self.Quests[stepIDs(step)[1]]
        return q and q[2] or 0
    end
    for _, zone in pairs(self.Zones) do
        local all = {}
        for _, story in ipairs(zone.stories) do
            all[#all + 1] = story
        end
        for _, key in ipairs(zone.also or {}) do
            all[#all + 1] = self.storyByKey[key]
        end
        table.sort(all, function(a, b)
            local la, lb = firstLevel(a.steps[1]), firstLevel(b.steps[1])
            if la ~= lb then
                return la < lb
            end
            return a.key < b.key
        end)
        zone.allStories = all
        local side = {}
        for _, step in ipairs(zone.side) do
            side[#side + 1] = step
        end
        for _, step in ipairs(zone.alsoSide or {}) do
            side[#side + 1] = step
        end
        table.sort(side, function(a, b)
            local la, lb = firstLevel(a), firstLevel(b)
            if la ~= lb then
                return la < lb
            end
            return stepIDs(a)[1] < stepIDs(b)[1]
        end)
        zone.allSide = side
    end
end

-- Localized zone names (and their lookup) come from the client when available.
function ns:GetZoneName(areaID)
    local zone = self.Zones[areaID]
    if not zone then
        return "?"
    end
    if zone.localName == nil then
        zone.localName = false
        if zone.uiMap > 0 and C_Map and C_Map.GetMapInfo then
            local info = C_Map.GetMapInfo(zone.uiMap)
            if info and info.name and info.name ~= "" then
                zone.localName = info.name
                self.areaByName[info.name:lower()] = areaID
            end
        end
    end
    return zone.localName or zone.name
end

function ns:GetQuestName(questID)
    local title = C_QuestLog and C_QuestLog.GetTitleForQuestID and C_QuestLog.GetTitleForQuestID(questID)
    if title and title ~= "" then
        return title
    end
    local q = self.Quests[questID]
    return q and q[1] or ("Quest #" .. questID)
end

function ns:GetQuestLevel(questID)
    local q = self.Quests[questID]
    return q and q[2] or 0
end

---------------------------------------------------------------------------
-- Player / quest state
---------------------------------------------------------------------------

local playerFaction, playerRace
local completedCache = {}
local progressCache = {} -- story -> { done, total, started }; cleared whenever quest state may change

function ns:UpdatePlayerInfo()
    local faction = UnitFactionGroup("player")
    playerFaction = (faction == "Alliance" and 1) or (faction == "Horde" and 2) or 0
    playerRace = select(3, UnitRace("player"))
    self:InvalidateProgress()
end

--- Forget cached storyline progress. Call after anything that changes quest state or what is counted.
function ns:InvalidateProgress()
    wipe(progressCache)
end

function ns:IsQuestForPlayer(questID)
    local q = self.Quests[questID]
    if not q then
        return false
    end
    if not playerFaction then
        self:UpdatePlayerInfo()
    end
    if q[3] ~= 0 and playerFaction ~= 0 and q[3] ~= playerFaction then
        return false
    end
    local races = q[4]
    if races and playerRace then
        for _, raceID in ipairs(races) do
            if raceID == playerRace then
                return true
            end
        end
        -- Restricted to other races. Only trust that for the original races (IDs 1-8); for
        -- races the data may number differently (e.g. Forever's new race) the faction check decides.
        return playerRace > 8
    end
    return true
end

function ns:IsQuestCompleted(questID)
    if completedCache[questID] then
        return true
    end
    local isCompleted
    if C_QuestLog and C_QuestLog.IsQuestFlaggedCompleted then
        isCompleted = C_QuestLog.IsQuestFlaggedCompleted(questID)
    elseif IsQuestFlaggedCompleted then
        isCompleted = IsQuestFlaggedCompleted(questID)
    end
    if isCompleted then
        completedCache[questID] = true
    end
    return isCompleted and true or false
end

function ns:IsOnQuest(questID)
    if C_QuestLog then
        if C_QuestLog.IsOnQuest then
            return C_QuestLog.IsOnQuest(questID)
        elseif C_QuestLog.GetLogIndexForQuestID then
            return C_QuestLog.GetLogIndexForQuestID(questID) ~= nil
        end
    end
    return false
end

function ns:IsQuestReadyForTurnIn(questID)
    if C_QuestLog and C_QuestLog.ReadyForTurnIn then
        return C_QuestLog.ReadyForTurnIn(questID)
    elseif C_QuestLog and C_QuestLog.IsComplete then
        return C_QuestLog.IsComplete(questID)
    end
    return false
end

function ns:IsQuestIgnored(questID)
    return self.db.ignoredQuests[questID] and true or false
end

function ns:IsStoryIgnored(story)
    return self.db.ignoredStories[story.key] and true or false
end

--- Resolves a story step for the current character.
-- @return questID to show (nil when the step is not available to this character), state
function ns:ResolveStep(step)
    local shown, state = nil, nil
    for _, questID in ipairs(stepIDs(step)) do
        if self:IsQuestForPlayer(questID) then
            if self:IsQuestCompleted(questID) then
                return questID, self.STATE_DONE
            end
            if self:IsOnQuest(questID) then
                local s = self:IsQuestReadyForTurnIn(questID) and self.STATE_READY or self.STATE_ACTIVE
                if not state or s > state then
                    shown, state = questID, s
                end
            elseif not shown then
                shown, state = questID, self.STATE_TODO
            end
        end
    end
    return shown, state
end

--- Progress of a story for the current character.
-- @return done, total, started (true when a step is done or in the quest log)
function ns:GetStoryProgress(story)
    local cached = progressCache[story]
    if cached then
        return cached[1], cached[2], cached[3]
    end
    local done, total, started = 0, 0, false
    for _, step in ipairs(story.steps) do
        local questID, state = self:ResolveStep(step)
        if questID and not self:IsQuestIgnored(questID) then
            total = total + 1
            if state == self.STATE_DONE then
                done = done + 1
            end
            if state ~= self.STATE_TODO then
                started = true
            end
        end
    end
    progressCache[story] = { done, total, started }
    return done, total, started
end

function ns:SetQuestIgnored(questID, ignored)
    self.db.ignoredQuests[questID] = ignored or nil
    self:InvalidateProgress()
end

function ns:SetStoryIgnored(story, ignored)
    self.db.ignoredStories[story.key] = ignored or nil
    self:InvalidateProgress()
end

--- Stories of a zone that apply to the current character (faction, race), in display order.
function ns:GetZoneStories(areaID, includeIgnored)
    local list = {}
    local zone = self.Zones[areaID]
    if not zone then
        return list
    end
    for _, story in ipairs(zone.allStories) do
        local _, total = self:GetStoryProgress(story)
        if total > 0 and (includeIgnored or not self:IsStoryIgnored(story)) then
            list[#list + 1] = story
        end
    end
    return list
end

--- Side quests (quests that are not part of a chain) of a zone for the current character, including
-- the ones filed under another zone (e.g. a dungeon) but picked up here.
-- @return list of { questID, state, homeZone (areaID when filed under another zone) }
function ns:GetZoneSideQuests(areaID)
    local list = {}
    local zone = self.Zones[areaID]
    if not zone then
        return list
    end
    for _, step in ipairs(zone.allSide) do
        local questID, state = self:ResolveStep(step)
        if questID then
            local home = self.sideZoneByQuest[stepIDs(step)[1]]
            list[#list + 1] = { questID = questID, state = state, homeZone = home ~= areaID and home or nil }
        end
    end
    return list
end

--- @return storiesDone, storiesTotal, sideDone, sideTotal
function ns:GetZoneProgress(areaID)
    local storiesDone, storiesTotal = 0, 0
    for _, story in ipairs(self:GetZoneStories(areaID)) do
        local done, total = self:GetStoryProgress(story)
        storiesTotal = storiesTotal + 1
        if done == total then
            storiesDone = storiesDone + 1
        end
    end
    local sideDone, sideTotal = 0, 0
    for _, side in ipairs(self:GetZoneSideQuests(areaID)) do
        if not self:IsQuestIgnored(side.questID) then
            sideTotal = sideTotal + 1
            if side.state == self.STATE_DONE then
                sideDone = sideDone + 1
            end
        end
    end
    return storiesDone, storiesTotal, sideDone, sideTotal
end

function ns:GetStoryLevelRange(story)
    local low, high
    for _, step in ipairs(story.steps) do
        local questID = self:ResolveStep(step)
        local level = questID and self:GetQuestLevel(questID)
        if level and level > 0 then
            low = (not low or level < low) and level or low
            high = (not high or level > high) and level or high
        end
    end
    return low, high
end

---------------------------------------------------------------------------
-- Current zone
---------------------------------------------------------------------------

function ns:FindAreaForMap(mapID)
    local guard = 0
    while mapID and mapID > 0 and guard < 10 do
        local areaID = self.areaByMap[mapID]
        if areaID then
            return areaID
        end
        local info = C_Map and C_Map.GetMapInfo and C_Map.GetMapInfo(mapID)
        mapID = info and info.parentMapID
        guard = guard + 1
    end
end

function ns:FindAreaByName(name)
    if not name or name == "" then
        return nil
    end
    if not self.localNamesLoaded then
        self.localNamesLoaded = true
        for areaID in pairs(self.Zones) do
            self:GetZoneName(areaID)
        end
    end
    name = name:lower()
    if self.areaByName[name] then
        return self.areaByName[name]
    end
    -- Otherwise accept an unambiguous start of a zone name ("westf" -> Westfall).
    -- @return areaID, or nil plus the matching zone names when the name is ambiguous
    local found, matches = nil, {}
    for zoneName, areaID in pairs(self.areaByName) do
        if zoneName:sub(1, #name) == name and not matches[areaID] then
            matches[areaID] = true
            found = found and -1 or areaID
        end
    end
    if found ~= -1 then
        return found
    end
    local names = {}
    for areaID in pairs(matches) do
        names[#names + 1] = self:GetZoneName(areaID)
    end
    table.sort(names)
    return nil, names
end

function ns:GetCurrentArea()
    local inInstance = IsInInstance and IsInInstance()
    if inInstance then
        local instanceName = GetInstanceInfo()
        local areaID = self:FindAreaByName(instanceName) or self:FindAreaByName(GetRealZoneText())
        if areaID then
            return areaID
        end
    end
    local mapID = C_Map and C_Map.GetBestMapForUnit and C_Map.GetBestMapForUnit("player")
    return self:FindAreaForMap(mapID) or self:FindAreaByName(GetRealZoneText())
end

---------------------------------------------------------------------------
-- Announcements
---------------------------------------------------------------------------

local function storyLink(story)
    return "|cffffd100" .. story.name .. "|r"
end

function ns:OnQuestTurnedIn(questID)
    completedCache[questID] = true
    self:InvalidateProgress()
    local stories = self.storiesByQuest[questID]
    if not stories or not self.db.announce or not self:IsQuestForPlayer(questID) then
        return
    end
    for _, story in ipairs(stories) do
        if not self:IsStoryIgnored(story) then
            local done, total = self:GetStoryProgress(story)
            if total > 0 and done == total then
                self:Print(("Storyline complete: %s (%s)"):format(storyLink(story), self:GetZoneName(story.zone)))
                if PlaySound and SOUNDKIT and SOUNDKIT.IG_QUEST_LIST_COMPLETE then
                    PlaySound(SOUNDKIT.IG_QUEST_LIST_COMPLETE)
                end
                local zoneDone, zoneTotal = self:GetZoneProgress(story.zone)
                if zoneTotal > 0 and zoneDone == zoneTotal then
                    self:Print(("All %d storylines of %s are complete!"):format(zoneTotal, self:GetZoneName(story.zone)))
                end
            elseif total > 0 then
                self:Print(("Storyline progress: %s %d/%d"):format(storyLink(story), done, total))
            end
        end
    end
end

---------------------------------------------------------------------------
-- Events
---------------------------------------------------------------------------

local events = CreateFrame("Frame")
events:RegisterEvent("ADDON_LOADED")
events:RegisterEvent("PLAYER_LOGIN")
events:RegisterEvent("QUEST_TURNED_IN")
events:RegisterEvent("QUEST_ACCEPTED")
events:RegisterEvent("QUEST_REMOVED")
events:RegisterEvent("QUEST_LOG_UPDATE")
events:RegisterEvent("ZONE_CHANGED_NEW_AREA")
events:RegisterEvent("PLAYER_ENTERING_WORLD")
events:RegisterEvent("PLAYER_LEVEL_UP") -- difficulty colors and XP depend on the level
events:RegisterEvent("GOSSIP_SHOW")       -- talking to a quest giver: warn about reputation-locked quests
events:RegisterEvent("QUEST_GREETING")
events:RegisterEvent("UPDATE_FACTION")    -- reputation changes can unlock quests

local refreshPending = false
local function requestRefresh()
    if refreshPending or not ns.RefreshUI then
        return
    end
    refreshPending = true
    C_Timer.After(0.3, function()
        refreshPending = false
        ns:RefreshUI(true)
    end)
end
ns.RequestRefresh = requestRefresh

events:SetScript("OnEvent", function(_, event, arg1)
    if event == "ADDON_LOADED" then
        if arg1 == ADDON_NAME then
            StorylinesDB = StorylinesDB or {}
            applyDefaults(StorylinesDB, defaults)
            ns.db = StorylinesDB
            ns:BuildIndex()
        end
    elseif event == "PLAYER_LOGIN" then
        ns:UpdatePlayerInfo()
        if ns.InitMinimapButton then
            ns:InitMinimapButton()
        end
    elseif event == "QUEST_TURNED_IN" then
        ns:OnQuestTurnedIn(arg1)
        ns:CheckFollowUpReputation(arg1)
        requestRefresh()
    elseif event == "GOSSIP_SHOW" or event == "QUEST_GREETING" then
        ns:CheckQuestGiverReputation()
    elseif event == "ZONE_CHANGED_NEW_AREA" or event == "PLAYER_ENTERING_WORLD" then
        if ns.OnZoneChanged then
            ns:OnZoneChanged()
        end
    else
        -- QUEST_ACCEPTED / QUEST_REMOVED / QUEST_LOG_UPDATE / PLAYER_LEVEL_UP / UPDATE_FACTION
        ns:InvalidateProgress()
        requestRefresh()
    end
end)

---------------------------------------------------------------------------
-- Slash commands
---------------------------------------------------------------------------

--- Opens a zone by (partial) name. Returns false when nothing matched and quiet is set.
local function showZone(name, quiet)
    local areaID, candidates = ns:FindAreaByName(name)
    if areaID then
        ns:ShowUI(areaID)
    elseif candidates then
        ns:Print("Which zone? " .. table.concat(candidates, ", "))
    elseif quiet then
        return false
    else
        ns:Print("Unknown zone: " .. name)
    end
    return true
end

local function slashHandler(msg)
    msg = strtrim(msg or "")
    local cmd, rest = msg:match("^(%S*)%s*(.-)$")
    cmd = (cmd or ""):lower()
    if cmd == "" then
        ns:ToggleUI()
    elseif cmd == "minimap" then
        ns.db.minimap.hide = not ns.db.minimap.hide
        ns:UpdateMinimapButton()
        ns:Print("Minimap button " .. (ns.db.minimap.hide and "hidden." or "shown."))
    elseif cmd == "announce" then
        ns.db.announce = not ns.db.announce
        ns:Print("Chat announcements " .. (ns.db.announce and "enabled." or "disabled."))
    elseif cmd == "repwarn" then
        ns.db.repWarnings = not ns.db.repWarnings
        ns:Print("Reputation warnings " .. (ns.db.repWarnings and "enabled." or "disabled."))
    elseif cmd == "reset" then
        wipe(ns.db.ignoredQuests)
        wipe(ns.db.ignoredStories)
        ns:InvalidateProgress()
        ns:Print("All ignored quests and storylines were restored.")
        requestRefresh()
    elseif cmd == "zone" or cmd == "z" then
        showZone(rest)
    elseif cmd == "help" then
        ns:Print("Commands:")
        ns:Print("/storylines - toggle the window")
        ns:Print("/storylines zone <name> - show a zone (e.g. /stl zone westfall, or just /stl westf)")
        ns:Print("/storylines minimap - show/hide the minimap button")
        ns:Print("/storylines announce - toggle chat messages when you finish a storyline step")
        ns:Print("/storylines repwarn - toggle warnings when your reputation is too low for a quest")
        ns:Print("/storylines reset - restore all ignored quests and storylines")
    elseif not showZone(msg, true) then
        ns:Print("Unknown command. Type /storylines help")
    end
end

SLASH_STORYLINES1 = "/storylines"
SLASH_STORYLINES2 = "/stl"
SlashCmdList.STORYLINES = slashHandler
