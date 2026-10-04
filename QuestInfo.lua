local _, ns = ...

-- Quest details (from Data/QuestDetails.lua), difficulty colors, quest type icons, rewards, waypoints.

ns.TAG_ELITE, ns.TAG_PVP, ns.TAG_RAID, ns.TAG_DUNGEON, ns.TAG_ESCORT = 1, 41, 62, 81, 84

local TAGS = {
    [1] = { name = "Elite", atlas = "nameplates-icon-elite-gold", file = "Interface\\TargetingFrame\\UI-TargetingFrame-Skull" },
    [41] = { name = "PvP", atlas = "questlog-questtypeicon-pvp", file = "Interface\\Icons\\INV_BannerPVP_02" },
    [62] = { name = "Raid", atlas = "questlog-questtypeicon-raid", file = "Interface\\Icons\\INV_Misc_Head_Dragon_01" },
    [81] = { name = "Dungeon", atlas = "questlog-questtypeicon-dungeon", file = "Interface\\Icons\\INV_Misc_Key_03" },
    [84] = { name = "Escort", atlas = "questlog-questtypeicon-group", file = "Interface\\Icons\\Ability_Warrior_RallyingCry" },
}
ns.TAG_ORDER = { 81, 62, 1, 84, 41 }

-- Fallback reputation names, used when the client cannot name a faction.
local FACTION_NAMES = {
    [21] = "Booty Bay", [47] = "Ironforge", [54] = "Gnomeregan Exiles", [59] = "Thorium Brotherhood",
    [68] = "Undercity", [69] = "Darnassus", [70] = "Syndicate", [72] = "Stormwind", [76] = "Orgrimmar",
    [81] = "Thunder Bluff", [87] = "Bloodsail Buccaneers", [92] = "Gelkis Clan Centaur", [93] = "Magram Clan Centaur",
    [169] = "Steamwheedle Cartel", [270] = "Zandalar Tribe", [349] = "Ravenholdt", [369] = "Gadgetzan",
    [470] = "Ratchet", [471] = "Wildhammer Clan", [509] = "The League of Arathor", [510] = "The Defilers",
    [529] = "Argent Dawn", [530] = "Darkspear Trolls", [576] = "Timbermaw Hold", [577] = "Everlook",
    [589] = "Wintersaber Trainers", [609] = "Cenarion Circle", [729] = "Frostwolf Clan", [730] = "Stormpike Guard",
    [749] = "Hydraxian Waterlords", [889] = "Warsong Outriders", [890] = "Silverwing Sentinels",
    [909] = "Darkmoon Faire", [910] = "Brood of Nozdormu",
}

---------------------------------------------------------------------------
-- Details
---------------------------------------------------------------------------

local EMPTY = {}

--- @return table|nil { requiredLevel, tag, objectives, giverKind, giverID, turnInKind, turnInID, xp, reputation,
--   items, pre (all must be completed), preAny (any one must be completed), minRep / maxRep ({factionID, value} or nil) }
function ns:GetQuestDetails(questID)
    local d = self.QuestDetails and self.QuestDetails[questID]
    if not d then
        return nil
    end
    return {
        requiredLevel = d[1],
        tag = d[2],
        objectives = d[3],
        giverKind = d[4],
        giverID = d[5],
        turnInKind = d[6],
        turnInID = d[7],
        xp = d[8],
        reputation = d[9] or EMPTY,
        items = d[10] or EMPTY,
        pre = d[11] or EMPTY,
        preAny = d[12] or EMPTY,
        minRep = d[13] and d[13][1] and d[13] or nil,
        maxRep = d[14] and d[14][1] and d[14] or nil,
    }
end

function ns:GetQuestTag(questID)
    local d = self.QuestDetails and self.QuestDetails[questID]
    if d and d[2] and d[2] ~= 0 then
        return d[2]
    end
    return nil
end

function ns:GetTagName(tag)
    return TAGS[tag] and TAGS[tag].name
end

local atlasExists = {}
local function hasAtlas(atlas)
    if atlasExists[atlas] == nil then
        atlasExists[atlas] = (C_Texture and C_Texture.GetAtlasInfo and C_Texture.GetAtlasInfo(atlas)) and true or false
    end
    return atlasExists[atlas]
end

--- Inline texture markup for a quest type icon (to put inside a FontString).
function ns:GetTagMarkup(tag, size)
    local info = TAGS[tag]
    if not info then
        return ""
    end
    size = size or 14
    if hasAtlas(info.atlas) then
        return ("|A:%s:%d:%d|a"):format(info.atlas, size, size)
    end
    return ("|T%s:%d:%d|t"):format(info.file, size, size)
end

--- Sets a Texture widget to a quest type icon.
function ns:SetTagTexture(texture, tag)
    local info = TAGS[tag]
    if not info then
        texture:SetTexture(nil)
        return
    end
    if hasAtlas(info.atlas) then
        texture:SetAtlas(info.atlas)
    else
        texture:SetTexture(info.file)
        texture:SetTexCoord(0, 1, 0, 1)
    end
end

--- Distinct quest types in a story (in TAG_ORDER), for the icons next to its name.
function ns:GetStoryTags(story)
    local found = {}
    for _, step in ipairs(story.steps) do
        local questID = self:ResolveStep(step)
        local tag = questID and self:GetQuestTag(questID)
        if tag then
            found[tag] = true
        end
    end
    local list = {}
    for _, tag in ipairs(self.TAG_ORDER) do
        if found[tag] then
            list[#list + 1] = tag
        end
    end
    return list
end

function ns:GetStoryTagMarkup(story, size)
    local out = ""
    for _, tag in ipairs(self:GetStoryTags(story)) do
        out = out .. " " .. self:GetTagMarkup(tag, size)
    end
    return out
end

---------------------------------------------------------------------------
-- Reputation
---------------------------------------------------------------------------

-- Reputation needed for each standing, counted from the start of Neutral (standing IDs 1-8).
local STANDING_THRESHOLDS = { -42000, -6000, -3000, 0, 3000, 9000, 21000, 42000 }
local STANDING_NAMES = { "Hated", "Hostile", "Unfriendly", "Neutral", "Friendly", "Honored", "Revered", "Exalted" }

local function standingOf(value)
    for id = #STANDING_THRESHOLDS, 1, -1 do
        if value >= STANDING_THRESHOLDS[id] then
            return id
        end
    end
    return 1
end

--- "Honored", or "Friendly +1,200" when the value is past the start of the standing.
function ns:FormatReputation(value)
    local id = standingOf(value)
    local name = _G["FACTION_STANDING_LABEL" .. id] or STANDING_NAMES[id]
    local extra = value - STANDING_THRESHOLDS[id]
    if extra > 0 and id < #STANDING_THRESHOLDS then
        return ("%s +%s"):format(name, self:FormatNumber(extra))
    end
    return name
end

--- This character's reputation with a faction, counted from the start of Neutral.
-- @return value, or nil when the client does not report the faction (not met yet)
function ns:GetReputation(factionID)
    if C_Reputation and C_Reputation.GetFactionDataByID then
        local data = C_Reputation.GetFactionDataByID(factionID)
        if data and data.currentStanding then
            return data.currentStanding
        end
    end
    if GetFactionInfoByID then
        local name, _, _, _, _, barValue = GetFactionInfoByID(factionID)
        if name and barValue then
            return barValue
        end
    end
    return nil
end

--- Checks a quest's reputation requirement.
-- @return nil when there is no problem, otherwise a table
--   { factionID, required, current (nil if unknown), tooHigh (true for a maximum that was exceeded) }
function ns:GetReputationProblem(questID)
    local d = self.QuestDetails and self.QuestDetails[questID]
    if not d then
        return nil
    end
    local minRep, maxRep = d[13], d[14]
    if minRep and minRep[1] then
        local current = self:GetReputation(minRep[1])
        -- A faction you have not met counts as the start of Neutral.
        if (current or 0) < minRep[2] then
            return { factionID = minRep[1], required = minRep[2], current = current }
        end
    end
    if maxRep and maxRep[1] then
        local current = self:GetReputation(maxRep[1])
        if current and current > maxRep[2] then
            return { factionID = maxRep[1], required = maxRep[2], current = current, tooHigh = true }
        end
    end
    return nil
end

--- Quests of a storyline that this character has not done yet and that reputation keeps out of reach
-- (regardless of other prerequisites, so you can plan ahead).
-- @return list of { questID = id, problem = GetReputationProblem table }
function ns:GetStoryReputationProblems(story)
    local list = {}
    for _, step in ipairs(story.steps) do
        local questID, state = self:ResolveStep(step)
        if questID and state == self.STATE_TODO and not self:IsQuestIgnored(questID) then
            local problem = self:GetReputationProblem(questID)
            if problem then
                list[#list + 1] = { questID = questID, problem = problem }
            end
        end
    end
    return list
end

ns.WARNING_ICON = "Interface\\DialogFrame\\UI-Dialog-Icon-AlertNew"

--- "Requires Honored with Ironforge (you are Friendly +1,200)"
function ns:DescribeReputationProblem(problem)
    local faction = self:GetFactionName(problem.factionID)
    local you = problem.current and self:FormatReputation(problem.current) or "not met yet"
    if problem.tooHigh then
        return ("Only available up to %s with %s (you are %s)"):format(
            self:FormatReputation(problem.required), faction, you)
    end
    return ("Requires %s with %s (you are %s)"):format(self:FormatReputation(problem.required), faction, you)
end

--- Whether this character can pick the quest up now, from the quest's real requirements.
-- @return "available", "locked" (earlier quests needed), "reputation" (also returns the problem table, see
--   GetReputationProblem), "level" (also returns the required level) or "skill" (profession skill too low;
--   also returns { skill, level, rank })
function ns:GetQuestAvailability(questID)
    local d = self.QuestDetails and self.QuestDetails[questID]
    if not d then
        return "available"
    end
    for _, pre in ipairs(d[11] or EMPTY) do
        if self:IsQuestForPlayer(pre) and not self:IsQuestCompleted(pre) then
            return "locked"
        end
    end
    local relevant, met = false, false
    for _, pre in ipairs(d[12] or EMPTY) do
        if self:IsQuestForPlayer(pre) then
            relevant = true
            if self:IsQuestCompleted(pre) then
                met = true
                break
            end
        end
    end
    if relevant and not met then
        return "locked"
    end
    local repProblem = self:GetReputationProblem(questID)
    if repProblem then
        return "reputation", repProblem
    end
    local required = d[1] or 0
    if required > (UnitLevel("player") or 1) then
        return "level", required
    end
    local q = self.Quests[questID]
    if q and q[6] and (q[7] or 0) > 0 then
        local rank = self:GetProfessionRank(q[6])
        if rank ~= nil and (rank or 0) < q[7] then
            return "skill", { skill = q[6], level = q[7], rank = rank or 0 }
        end
    end
    return "available"
end

local nextQuests
--- Quests that require this quest (from the prerequisite data), for "leads to".
function ns:GetNextQuests(questID)
    if not nextQuests then
        nextQuests = {}
        for id, d in pairs(self.QuestDetails or EMPTY) do
            for _, list in ipairs({ d[11] or EMPTY, d[12] or EMPTY }) do
                for _, pre in ipairs(list) do
                    nextQuests[pre] = nextQuests[pre] or {}
                    table.insert(nextQuests[pre], id)
                end
            end
        end
    end
    return nextQuests[questID] or EMPTY
end

---------------------------------------------------------------------------
-- Difficulty colors (like the quest log: red / orange / yellow / green / gray)
---------------------------------------------------------------------------

-- Same categories as the game's QuestDifficultyColors table.
local DIFFICULTY_LABELS = {
    impossible = "Very hard",
    verydifficult = "Hard",
    difficult = "Normal",
    standard = "Easy",
    trivial = "Trivial",
}
local FALLBACK_COLORS = {
    impossible = { r = 1, g = 0.1, b = 0.1 },
    verydifficult = { r = 1, g = 0.5, b = 0.25 },
    difficult = { r = 1, g = 0.82, b = 0 },
    standard = { r = 0.25, g = 0.75, b = 0.25 },
    trivial = { r = 0.5, g = 0.5, b = 0.5 },
}

-- How many levels below you a quest stays green (Classic rules when the client has no API for it).
local function greenRange(playerLevel)
    if GetQuestGreenRange then
        local range = GetQuestGreenRange()
        if range then
            return range
        end
    end
    local gray
    if playerLevel <= 5 then
        gray = 0
    elseif playerLevel <= 39 then
        gray = playerLevel - 5 - math.floor(playerLevel / 10)
    elseif playerLevel <= 59 then
        gray = playerLevel - 1 - math.floor(playerLevel / 5)
    else
        gray = playerLevel - 9
    end
    return playerLevel - gray - 1
end

--- Difficulty of a quest level for this character, the way the quest log colors it.
-- @return category key (see DIFFICULTY_LABELS), r, g, b
function ns:GetLevelDifficulty(level)
    if GetQuestDifficultyColor and QuestDifficultyColors then
        local color = GetQuestDifficultyColor(level)
        for key, c in pairs(QuestDifficultyColors) do
            if c == color and DIFFICULTY_LABELS[key] then
                return key, c.r, c.g, c.b
            end
        end
    end
    local playerLevel = UnitLevel("player") or 1
    local diff = level - playerLevel
    local key
    if diff >= 5 then
        key = "impossible"
    elseif diff >= 3 then
        key = "verydifficult"
    elseif diff >= -2 then
        key = "difficult"
    elseif -diff <= greenRange(playerLevel) then
        key = "standard"
    else
        key = "trivial"
    end
    local c = (QuestDifficultyColors and QuestDifficultyColors[key]) or FALLBACK_COLORS[key]
    return key, c.r, c.g, c.b
end

function ns:GetLevelColor(level)
    if not level or level <= 0 then
        return 1, 1, 1
    end
    local _, r, g, b = self:GetLevelDifficulty(level)
    return r, g, b
end

function ns:ColorLevel(level, text)
    local r, g, b = self:GetLevelColor(level)
    return ("|cff%02x%02x%02x%s|r"):format(r * 255, g * 255, b * 255, text or tostring(level))
end

function ns:GetDifficultyName(level)
    return DIFFICULTY_LABELS[(self:GetLevelDifficulty(level))]
end

---------------------------------------------------------------------------
-- Rewards and text
---------------------------------------------------------------------------

--- Experience for this character: base XP reduced when you out-level the quest (Classic rules).
-- @return xp for this character, base xp
function ns:GetQuestXP(questID)
    local d = self.QuestDetails and self.QuestDetails[questID]
    local base = d and d[8] or 0
    if base <= 0 then
        return 0, 0
    end
    local playerLevel = UnitLevel("player") or 1
    local atMax
    if IsPlayerAtEffectiveMaxLevel then
        atMax = IsPlayerAtEffectiveMaxLevel()
    else
        atMax = playerLevel >= ((GetMaxPlayerLevel and GetMaxPlayerLevel()) or 60)
    end
    if atMax then
        return 0, base
    end
    local diff = playerLevel - self:GetQuestLevel(questID)
    local factor = (diff <= 5 and 1) or (diff == 6 and 0.8) or (diff == 7 and 0.6) or (diff == 8 and 0.4)
        or (diff == 9 and 0.2) or 0.1
    if factor == 1 then
        return base, base
    end
    return math.floor(base * factor / 5 + 0.5) * 5, base
end

function ns:FormatNumber(n)
    if BreakUpLargeNumbers then
        return BreakUpLargeNumbers(n)
    end
    local s = tostring(n)
    while true do
        local replaced
        s, replaced = s:gsub("^(-?%d+)(%d%d%d)", "%1,%2")
        if replaced == 0 then
            return s
        end
    end
end

function ns:GetFactionName(factionID)
    if C_Reputation and C_Reputation.GetFactionDataByID then
        local data = C_Reputation.GetFactionDataByID(factionID)
        if data and data.name then
            return data.name
        end
    end
    if GetFactionInfoByID then
        local name = GetFactionInfoByID(factionID)
        if name then
            return name
        end
    end
    return FACTION_NAMES[factionID] or ("Faction " .. factionID)
end

--- Item name, link, quality, icon. The name is the database name until the client has the item cached.
function ns:GetItem(itemID)
    local getInfo = (C_Item and C_Item.GetItemInfo) or GetItemInfo
    local name, link, quality, _, _, _, _, _, _, icon
    if getInfo then
        name, link, quality, _, _, _, _, _, _, icon = getInfo(itemID)
    end
    if not name then
        if C_Item and C_Item.RequestLoadItemDataByID then
            C_Item.RequestLoadItemDataByID(itemID)
        end
        name = self.ItemNames and self.ItemNames[itemID] or ("Item " .. itemID)
    end
    if not icon then
        icon = (C_Item and C_Item.GetItemIconByID and C_Item.GetItemIconByID(itemID))
            or (GetItemIcon and GetItemIcon(itemID)) or "Interface\\Icons\\INV_Misc_QuestionMark"
    end
    return name, link, quality, icon
end

--- Replaces the $N / $C / $R / $B / $G placeholders used in quest texts.
function ns:FormatQuestText(text)
    if not text or text == "" then
        return text
    end
    local name = UnitName("player") or "you"
    local class = UnitClass("player") or ""
    local race = UnitRace("player") or ""
    local female = UnitSex and UnitSex("player") == 3
    text = text:gsub("%$[Gg]%s*([^:;]*):([^;]*);", function(male, fem)
        return female and fem or male
    end)
    text = text:gsub("%$[Nn]", name):gsub("%$[Cc]", class:lower()):gsub("%$[Rr]", race):gsub("%$[Bb]", "\n")
    return text
end

---------------------------------------------------------------------------
-- Quest givers and waypoints
---------------------------------------------------------------------------

--- @return name, title, areaID, x, y (title only for NPCs; x/y nil when unknown)
function ns:GetGiver(kind, id)
    if kind == 1 and self.NPCs[id] then
        local n = self.NPCs[id]
        return n[1], n[2] or nil, n[3], n[4], n[5]
    elseif kind == 2 and self.Objects[id] then
        local o = self.Objects[id]
        return o[1], nil, o[2], o[3], o[4]
    elseif kind == 3 then
        return (self:GetItem(id)), nil, nil, nil, nil
    end
end

function ns:GetAreaName(areaID)
    if not areaID or areaID == 0 then
        return nil
    end
    if self.Zones[areaID] then
        return self:GetZoneName(areaID)
    end
    local area = self.Areas and self.Areas[areaID]
    if area and area[2] > 0 and C_Map and C_Map.GetMapInfo then
        local info = C_Map.GetMapInfo(area[2])
        if info and info.name and info.name ~= "" then
            return info.name
        end
    end
    return area and area[1]
end

function ns:FormatLocation(areaID, x, y)
    local zone = self:GetAreaName(areaID)
    if not zone then
        return nil
    end
    if x and y then
        return ("%s (%.1f, %.1f)"):format(zone, x, y)
    end
    return zone
end

function ns:CanSetWaypoint(areaID, x, y)
    local area = self.Areas and self.Areas[areaID]
    if not (area and area[2] > 0 and x and y) then
        return false
    end
    if TomTom and TomTom.AddWaypoint and self.db.waypoints ~= "map" then
        return true
    end
    return C_Map and C_Map.SetUserWaypoint and UiMapPoint and UiMapPoint.CreateFromCoordinates and true or false
end

function ns:SetWaypoint(areaID, x, y, title)
    local area = self.Areas and self.Areas[areaID]
    local uiMap = area and area[2]
    if not self:CanSetWaypoint(areaID, x, y) then
        self:Print("Can't set a waypoint there.")
        return
    end
    local where = self:FormatLocation(areaID, x, y)
    if TomTom and TomTom.AddWaypoint and self.db.waypoints ~= "map" then
        TomTom:AddWaypoint(uiMap, x / 100, y / 100, { title = title, from = "Storylines" })
    else
        if C_Map.CanSetUserWaypointOnMap and not C_Map.CanSetUserWaypointOnMap(uiMap) then
            self:Print(("Can't set a waypoint on this map. %s is at %s."):format(title, where))
            return
        end
        C_Map.SetUserWaypoint(UiMapPoint.CreateFromCoordinates(uiMap, x / 100, y / 100))
        if C_SuperTrack and C_SuperTrack.SetSuperTrackedUserWaypoint then
            C_SuperTrack.SetSuperTrackedUserWaypoint(true)
        end
    end
    self:Print(("Waypoint set: %s, %s"):format(title, where))
end

---------------------------------------------------------------------------
-- Reputation warnings
---------------------------------------------------------------------------

local warned = {} -- questID -> true, so each quest is reported once per session
local questsByGiver -- "npc:ID" / "object:ID" -> { questID, ... }

local function giverIndex()
    if not questsByGiver then
        questsByGiver = {}
        for questID, d in pairs(ns.QuestDetails or EMPTY) do
            local kind = (d[4] == 1 and "npc") or (d[4] == 2 and "object")
            if kind then
                local key = kind .. ":" .. d[5]
                questsByGiver[key] = questsByGiver[key] or {}
                table.insert(questsByGiver[key], questID)
            end
        end
    end
    return questsByGiver
end

--- Tells the player (chat + red on-screen text) that a quest is out of reach because of reputation.
-- The chat line is before .. [quest] .. after .. ": <requirement>."
function ns:WarnReputation(questID, problem, before, after)
    local mode = self.db.repWarnings
    if warned[questID] or mode == "off" then
        return
    end
    warned[questID] = true
    local quest = "|cffffd100[" .. self:GetQuestName(questID) .. "]|r"
    if mode ~= "screen" then
        self:Print(before .. quest .. after .. ": " .. self:DescribeReputationProblem(problem) .. ".")
    end
    if mode ~= "chat" and UIErrorsFrame and UIErrorsFrame.AddMessage then
        UIErrorsFrame:AddMessage(("Reputation too low for %s"):format(self:GetQuestName(questID)), 1, 0.1, 0.1, 1)
    end
end

--- Quests from storylines or side quests that this character could take now if not for reputation.
local function blockedByReputation(questID)
    if not ns:IsQuestForPlayer(questID) or ns:IsQuestIgnored(questID) or ns:IsQuestCompleted(questID)
        or ns:IsOnQuest(questID) then
        return nil
    end
    local availability, problem = ns:GetQuestAvailability(questID)
    return availability == "reputation" and problem or nil
end

--- The NPC or object the player is talking to (gossip / quest greeting window).
-- @return "npc" | "object", id   or nil when unknown (e.g. hidden by the client)
local function currentGiver()
    local ok, guid = pcall(UnitGUID, "npc")
    if not ok or guid == nil or (issecretvalue and issecretvalue(guid)) or type(guid) ~= "string" then
        return nil
    end
    local unitType, _, _, _, _, id = strsplit("-", guid)
    id = tonumber(id)
    if not id then
        return nil
    end
    if unitType == "Creature" or unitType == "Vehicle" then
        return "npc", id
    elseif unitType == "GameObject" then
        return "object", id
    end
end

--- Called when a gossip or quest greeting window opens.
function ns:CheckQuestGiverReputation()
    local kind, id = currentGiver()
    if not kind then
        return
    end
    for _, questID in ipairs(giverIndex()[kind .. ":" .. id] or EMPTY) do
        local problem = blockedByReputation(questID)
        if problem then
            local name = kind == "npc" and self.NPCs[id] and self.NPCs[id][1] or "This quest giver"
            self:WarnReputation(questID, problem, name .. " has ", " for you, but your reputation is not high enough")
        end
    end
end

--- Called after a quest is turned in: warn about follow-up quests that reputation keeps out of reach.
function ns:CheckFollowUpReputation(questID)
    for _, nextID in ipairs(self:GetNextQuests(questID)) do
        local problem = blockedByReputation(nextID)
        if problem then
            self:WarnReputation(nextID, problem, "Your reputation is not high enough for the next quest, ", "")
        end
    end
end
