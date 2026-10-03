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

--- @return table|nil { requiredLevel, tag, objectives, giver = {kind, id}, turnIn = {kind, id}, xp, reputation, items, pre }
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

local nextQuests
--- Quests that require this quest (from the prerequisite data), for "leads to".
function ns:GetNextQuests(questID)
    if not nextQuests then
        nextQuests = {}
        for id, d in pairs(self.QuestDetails or EMPTY) do
            for _, pre in ipairs(d[11] or EMPTY) do
                nextQuests[pre] = nextQuests[pre] or {}
                table.insert(nextQuests[pre], id)
            end
        end
    end
    return nextQuests[questID] or EMPTY
end

---------------------------------------------------------------------------
-- Difficulty colors (like the quest log: red / orange / yellow / green / gray)
---------------------------------------------------------------------------

local function grayLevel(playerLevel)
    if playerLevel <= 5 then
        return 0
    elseif playerLevel <= 39 then
        return playerLevel - 5 - math.floor(playerLevel / 10)
    elseif playerLevel <= 59 then
        return playerLevel - 1 - math.floor(playerLevel / 5)
    end
    return playerLevel - 9
end

function ns:GetLevelColor(level)
    if not level or level <= 0 then
        return 1, 1, 1
    end
    if GetQuestDifficultyColor then
        local c = GetQuestDifficultyColor(level)
        if type(c) == "table" and c.r then
            return c.r, c.g, c.b
        end
    end
    local playerLevel = UnitLevel("player") or 1
    local diff = level - playerLevel
    if diff >= 5 then
        return 1, 0.1, 0.1
    elseif diff >= 3 then
        return 1, 0.5, 0.25
    elseif diff >= -2 then
        return 1, 0.82, 0
    elseif level > grayLevel(playerLevel) then
        return 0.25, 0.75, 0.25
    end
    return 0.5, 0.5, 0.5
end

function ns:ColorLevel(level, text)
    local r, g, b = self:GetLevelColor(level)
    return ("|cff%02x%02x%02x%s|r"):format(r * 255, g * 255, b * 255, text or tostring(level))
end

function ns:GetDifficultyName(level)
    local playerLevel = UnitLevel("player") or 1
    local diff = level - playerLevel
    if diff >= 5 then
        return "Very difficult"
    elseif diff >= 3 then
        return "Difficult"
    elseif diff >= -2 then
        return "Standard"
    elseif level > grayLevel(playerLevel) then
        return "Easy"
    end
    return "Trivial"
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
    local maxLevel = (GetMaxLevelForPlayerExpansion and GetMaxLevelForPlayerExpansion())
        or (GetMaxPlayerLevel and GetMaxPlayerLevel()) or 60
    if playerLevel >= maxLevel then
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
    if TomTom and TomTom.AddWaypoint then
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
    if TomTom and TomTom.AddWaypoint then
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
