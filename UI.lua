local _, ns = ...

local BASE_ROW_HEIGHT = 20
local ROW_HEIGHT = BASE_ROW_HEIGHT -- changes with the "Text size" setting
local ZONE_LIST_WIDTH = 230
local FRAME_WIDTH, FRAME_HEIGHT = 780, 540
local MIN_WIDTH, MIN_HEIGHT = 700, 400

local ICON_DONE = "Interface\\RaidFrame\\ReadyCheck-Ready"
local ICON_ACTIVE = "Interface\\GossipFrame\\ActiveQuestIcon"
local ICON_AVAILABLE = "Interface\\GossipFrame\\AvailableQuestIcon"
local ICON_WAITING = "Interface\\RaidFrame\\ReadyCheck-Waiting"
local ICON_IGNORED = "Interface\\RaidFrame\\ReadyCheck-NotReady"
local ICON_EXPAND = "Interface\\Buttons\\UI-PlusButton-Up"
local ICON_COLLAPSE = "Interface\\Buttons\\UI-MinusButton-Up"
local ICON_HERE = "Interface\\ChatFrame\\ChatFrameExpandArrow"

local COLOR_DONE = { 0.5, 0.5, 0.5 }
local COLOR_GREEN = { 0.25, 1, 0.25 }
local COLOR_GOLD = { 1, 0.82, 0 }
local COLOR_WHITE = { 1, 1, 1 }
local COLOR_LOCKED = { 0.75, 0.75, 0.75 }

local frame
local expandedStories = {}
local sideCollapsed = false

---------------------------------------------------------------------------
-- Text size: the lists use their own copies of the game fonts, scaled by the setting
---------------------------------------------------------------------------

local TEXT_SCALE = { small = 0.9, normal = 1, large = 1.15 }
local fonts, fontBase = {}, {}

function ns:TextScale()
    return TEXT_SCALE[self.db and self.db.textSize] or 1
end

--- The scaled copy of a game font object (by name), e.g. ns:Font("GameFontHighlightSmall").
function ns:Font(name)
    local font = fonts[name]
    if font then
        return font
    end
    local base = _G[name]
    if not (base and base.GetFont and CreateFont) then
        return base or name
    end
    font = CreateFont("Storylines" .. name)
    font:CopyFontObject(base)
    fontBase[name] = { base:GetFont() }
    fonts[name] = font
    local file, size, flags = unpack(fontBase[name])
    if file and size then
        font:SetFont(file, size * self:TextScale(), flags or "")
    end
    return font
end

function ns:ApplyTextSize()
    local scale = self:TextScale()
    for name, font in pairs(fonts) do
        local file, size, flags = unpack(fontBase[name])
        if file and size then
            font:SetFont(file, size * scale, flags or "")
        end
    end
    ROW_HEIGHT = math.floor(BASE_ROW_HEIGHT * scale + 0.5)
end

---------------------------------------------------------------------------
-- Small widget helpers (plain frames only, so they work on any client UI)
---------------------------------------------------------------------------

local function SetBackdropSafe(f, bg, edge, edgeSize, insets)
    if not f.SetBackdrop then
        Mixin(f, BackdropTemplateMixin)
    end
    f:SetBackdrop({
        bgFile = bg,
        edgeFile = edge,
        tile = true,
        tileSize = 16,
        edgeSize = edgeSize or 16,
        insets = { left = insets or 4, right = insets or 4, top = insets or 4, bottom = insets or 4 },
    })
end

local function CreateCheckbox(parent, label, tooltip, onClick)
    local cb = CreateFrame("CheckButton", nil, parent)
    cb:SetSize(24, 24)
    cb:SetNormalTexture("Interface\\Buttons\\UI-CheckBox-Up")
    cb:SetPushedTexture("Interface\\Buttons\\UI-CheckBox-Down")
    cb:SetHighlightTexture("Interface\\Buttons\\UI-CheckBox-Highlight", "ADD")
    cb:SetCheckedTexture("Interface\\Buttons\\UI-CheckBox-Check")
    cb.label = cb:CreateFontString(nil, "ARTWORK", "GameFontHighlightSmall")
    cb.label:SetPoint("LEFT", cb, "RIGHT", 0, 1)
    cb.label:SetText(label)
    cb:SetHitRectInsets(0, -cb.label:GetStringWidth() - 4, 0, 0)
    cb:SetScript("OnClick", function(self)
        onClick(self:GetChecked() and true or false)
    end)
    cb:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_TOP")
        GameTooltip:SetText(label, 1, 1, 1)
        GameTooltip:AddLine(tooltip, nil, nil, nil, true)
        GameTooltip:Show()
    end)
    cb:SetScript("OnLeave", GameTooltip_Hide)
    return cb
end

--- A virtual scrolling list of fixed-height rows.
local function CreateList(parent, initRow, updateRow)
    local list = CreateFrame("Frame", nil, parent)
    list.items = {}
    list.rows = {}
    list.offset = 0

    local bar = CreateFrame("Slider", nil, list)
    bar:SetOrientation("VERTICAL")
    bar:SetWidth(12)
    bar:SetPoint("TOPRIGHT", 0, -2)
    bar:SetPoint("BOTTOMRIGHT", 0, 2)
    bar:SetThumbTexture("Interface\\Buttons\\UI-ScrollBar-Knob")
    bar:GetThumbTexture():SetSize(16, 24)
    local track = bar:CreateTexture(nil, "BACKGROUND")
    track:SetAllPoints()
    track:SetColorTexture(0, 0, 0, 0.35)
    bar:SetValueStep(1)
    bar:SetObeyStepOnDrag(true)
    bar:SetScript("OnValueChanged", function(_, value)
        value = math.floor(value + 0.5)
        if value ~= list.offset then
            list.offset = value
            list:Update()
        end
    end)
    list.bar = bar

    list:EnableMouseWheel(true)
    list:SetScript("OnMouseWheel", function(self, delta)
        local _, max = bar:GetMinMaxValues()
        local value = math.max(0, math.min(max, self.offset - delta * 3))
        bar:SetValue(value)
    end)
    list:SetScript("OnSizeChanged", function(self)
        self:Update()
    end)

    function list:NumVisible()
        return math.max(1, math.floor((self:GetHeight() or 0) / ROW_HEIGHT))
    end

    function list:SetItems(items, keepOffset)
        self.items = items
        if not keepOffset then
            self.offset = 0
        end
        self:Update()
    end

    function list:Update()
        local visible = self:NumVisible()
        local maxOffset = math.max(0, #self.items - visible)
        if self.offset > maxOffset then
            self.offset = maxOffset
        end
        bar:SetMinMaxValues(0, maxOffset)
        bar:SetValue(self.offset)
        bar:SetShown(maxOffset > 0)
        for i = 1, visible do
            local row = self.rows[i]
            if not row then
                row = CreateFrame("Button", nil, self)
                row:RegisterForClicks("LeftButtonUp", "RightButtonUp")
                row:SetHighlightTexture("Interface\\QuestFrame\\UI-QuestTitleHighlight", "ADD")
                initRow(row)
                self.rows[i] = row
            end
            if row.height ~= ROW_HEIGHT then
                row.height = ROW_HEIGHT
                row:SetHeight(ROW_HEIGHT)
                row:ClearAllPoints()
                row:SetPoint("TOPLEFT", 0, -(i - 1) * ROW_HEIGHT)
                row:SetPoint("RIGHT", bar, "LEFT", -2, 0)
            end
            local item = self.items[self.offset + i]
            row.item = item
            if item then
                updateRow(row, item)
                row:Show()
            else
                row:Hide()
            end
        end
        for i = visible + 1, #self.rows do
            self.rows[i]:Hide()
        end
    end

    return list
end

local function InitRow(row)
    row.selected = row:CreateTexture(nil, "BACKGROUND")
    row.selected:SetAllPoints()
    row.selected:SetColorTexture(1, 0.82, 0, 0.15)
    row.selected:Hide()

    row.icon = row:CreateTexture(nil, "ARTWORK")
    row.icon:SetSize(14, 14)
    row.icon:SetPoint("LEFT", 4, 0)

    row.right = row:CreateFontString(nil, "ARTWORK")
    row.right:SetFontObject(ns:Font("GameFontHighlightSmall"))
    row.right:SetPoint("RIGHT", -4, 0)
    row.right:SetJustifyH("RIGHT")

    row.text = row:CreateFontString(nil, "ARTWORK")
    row.text:SetFontObject(ns:Font("GameFontHighlight"))
    row.text:SetPoint("LEFT", row.icon, "RIGHT", 4, 0)
    row.text:SetPoint("RIGHT", row.right, "LEFT", -6, 0)
    row.text:SetJustifyH("LEFT")
    row.text:SetWordWrap(false)

    row.strike = row:CreateTexture(nil, "OVERLAY")
    row.strike:SetHeight(1)
    row.strike:SetColorTexture(0.75, 0.75, 0.75, 0.9)
    row.strike:SetPoint("LEFT", row.text, "LEFT", -1, 0)
    row.strike:Hide()
end

local function SetRow(row, opts)
    row.icon:ClearAllPoints()
    row.icon:SetPoint("LEFT", 4 + (opts.indent or 0), 0)
    if opts.icon then
        row.icon:SetTexture(opts.icon)
        row.icon:SetDesaturated(opts.desaturate or false)
        row.icon:SetSize(opts.iconSize or 14, opts.iconSize or 14)
        row.icon:SetTexCoord(0, 1, 0, 1)
        row.icon:Show()
    else
        row.icon:SetTexture(nil)
        row.icon:SetSize(1, 14)
    end
    row.text:SetFontObject(ns:Font(opts.font or "GameFontHighlight"))
    row.text:SetText(opts.text or "")
    local c = opts.color or COLOR_WHITE
    row.text:SetTextColor(c[1], c[2], c[3])
    row.right:SetText(opts.right or "")
    if opts.strike then
        local width = row.text:GetStringWidth()
        local maxWidth = row.text:GetWidth()
        if maxWidth and maxWidth > 0 then
            width = math.min(width, maxWidth)
        end
        row.strike:SetWidth(width + 2)
        row.strike:Show()
    else
        row.strike:Hide()
    end
    row.selected:SetShown(opts.selected or false)
end

---------------------------------------------------------------------------
-- Zone list (left)
---------------------------------------------------------------------------

local function progressColor(done, total)
    if total > 0 and done == total then
        return "|cff40ff40"
    elseif done > 0 then
        return "|cffffd100"
    end
    return "|cffb0b0b0"
end

local function BuildZoneItems()
    local byGroup, groupDone, groupTotal, counted = {}, {}, {}, {}
    for areaID, zone in pairs(ns.Zones) do
        local done, total, sideDone, sideTotal = ns:GetZoneProgress(areaID)
        -- Zones with only side quests are listed too, and every dungeon and raid is listed even before
        -- any quest is known for it (e.g. WoW Forever's new dungeons).
        if total > 0 or sideTotal > 0 or zone.group == 3 then
            local group = zone.group
            byGroup[group] = byGroup[group] or {}
            local finished = (total > 0 or sideTotal > 0) and done == total
                and (sideDone == sideTotal or not ns.db.showSide)
            if not (ns.db.hideFinishedZones and finished and areaID ~= ns.selectedArea) then
                table.insert(byGroup[group], { type = "zone", areaID = areaID, done = done, total = total,
                    sideDone = sideDone, sideTotal = sideTotal, name = ns:GetZoneName(areaID) })
            end
            -- A storyline can be listed in two zones (where it is picked up and where it happens);
            -- count it once in the group total. Hidden finished zones still count.
            counted[group] = counted[group] or {}
            for _, story in ipairs(ns:GetZoneStories(areaID)) do
                if not counted[group][story] then
                    counted[group][story] = true
                    local d, t = ns:GetStoryProgress(story)
                    groupTotal[group] = (groupTotal[group] or 0) + 1
                    groupDone[group] = (groupDone[group] or 0) + ((d == t) and 1 or 0)
                end
            end
        end
    end
    local items = {}
    for group = 1, #ns.GROUP_NAMES do
        local zones = byGroup[group]
        if zones then
            table.sort(zones, function(a, b) return a.name < b.name end)
            local done, total = groupDone[group] or 0, groupTotal[group] or 0
            local collapsed = ns.db.collapsedGroups[group]
            table.insert(items, { type = "group", group = group, done = done, total = total, collapsed = collapsed })
            if not collapsed then
                for _, z in ipairs(zones) do
                    table.insert(items, z)
                end
            end
        end
    end
    return items
end

local function UpdateZoneRow(row, item)
    if item.type == "group" then
        SetRow(row, {
            icon = item.collapsed and ICON_EXPAND or ICON_COLLAPSE,
            text = ns.GROUP_NAMES[item.group],
            font = "GameFontNormal",
            color = COLOR_GOLD,
            right = progressColor(item.done, item.total) .. item.done .. "/" .. item.total .. "|r",
        })
    else
        local isCurrent = item.areaID == ns.currentArea
        local done, total, right = item.done, item.total, nil
        if total == 0 and item.sideTotal == 0 then
            right = "|cff707070no quests yet|r"
        elseif total == 0 then
            -- Only side quests here: show those instead.
            done, total = item.sideDone, item.sideTotal
            right = "|cff909090side|r " .. progressColor(done, total) .. done .. "/" .. total .. "|r"
        end
        SetRow(row, {
            indent = 8,
            icon = isCurrent and ICON_HERE or nil,
            iconSize = 14,
            text = item.name,
            color = (total == 0 and COLOR_DONE) or ((done == total) and COLOR_GREEN) or COLOR_WHITE,
            right = right or (progressColor(done, total) .. done .. "/" .. total .. "|r"),
            selected = item.areaID == ns.selectedArea,
        })
    end
end

local function OnZoneRowClick(row)
    local item = row.item
    if not item then
        return
    end
    if item.type == "group" then
        -- Store false (not nil) so groups that are collapsed by default remember being expanded.
        ns.db.collapsedGroups[item.group] = not ns.db.collapsedGroups[item.group]
        frame.zoneList:SetItems(BuildZoneItems(), true)
    else
        ns:ClearSearch()
        ns:SelectArea(item.areaID)
    end
end

local function OnZoneRowEnter(row)
    local item = row.item
    if not item or item.type ~= "zone" then
        return
    end
    local done, total, sideDone, sideTotal = ns:GetZoneProgress(item.areaID)
    GameTooltip:SetOwner(row, "ANCHOR_RIGHT")
    GameTooltip:SetText(item.name, 1, 1, 1)
    if total == 0 and sideTotal == 0 then
        GameTooltip:AddLine("No quests are known for this dungeon yet.", 0.6, 0.6, 0.6)
    end
    GameTooltip:AddDoubleLine("Storylines", done .. " / " .. total, nil, nil, nil, 1, 1, 1)
    if sideTotal > 0 then
        GameTooltip:AddDoubleLine("Side quests", sideDone .. " / " .. sideTotal, nil, nil, nil, 1, 1, 1)
    end
    if item.areaID == ns.currentArea then
        GameTooltip:AddLine("You are here.", 0.5, 0.8, 1)
    end
    GameTooltip:Show()
end

---------------------------------------------------------------------------
-- Story list (right)
---------------------------------------------------------------------------

--- Whether the level filters ("Hide gray", "Hide far above my level") hide something whose quests
-- range from level low to high. Callers never pass storylines or quests you have started.
local function HiddenByLevel(low, high)
    local db = ns.db
    if not low or low <= 0 or (not db.hideTrivial and (db.maxLevelsAbove or 0) <= 0) then
        return false
    end
    if db.hideTrivial and ns:GetLevelDifficulty(high) == "trivial" then
        return true
    end
    return db.maxLevelsAbove > 0 and low - (UnitLevel("player") or 1) > db.maxLevelsAbove
end

--- Orders a zone's storylines by the "Sort storylines by" setting (they come in level order).
local function SortStories(stories)
    local by = ns.db.sortBy
    if by ~= "name" and by ~= "progress" then
        return stories
    end
    local info = {}
    for i, story in ipairs(stories) do
        local done, total, started = ns:GetStoryProgress(story)
        local complete = total > 0 and done == total
        -- progress: storylines you are on first (furthest along first), then new ones, then finished ones
        info[story] = { index = i, rank = complete and 3 or (started and 1 or 2), share = total > 0 and done / total or 0 }
    end
    table.sort(stories, function(a, b)
        local ia, ib = info[a], info[b]
        if by == "name" then
            if a.name ~= b.name then
                return a.name < b.name
            end
        elseif ia.rank ~= ib.rank then
            return ia.rank < ib.rank
        elseif ia.rank == 1 and ia.share ~= ib.share then
            return ia.share > ib.share
        end
        return ia.index < ib.index
    end)
    return stories
end

local function BuildStoryItems(areaID)
    local items = {}
    local db = ns.db
    local stories = SortStories(ns:GetZoneStories(areaID, db.showIgnored))
    local shownStories, filtered = 0, 0
    for _, story in ipairs(stories) do
        local done, total, started = ns:GetStoryProgress(story)
        local complete = total > 0 and done == total
        local ignored = ns:IsStoryIgnored(story)
        local hidden = db.hideCompleted and complete
        if not hidden and not started and not complete and HiddenByLevel(ns:GetStoryLevelRange(story)) then
            hidden, filtered = true, filtered + 1
        end
        if not hidden then
            shownStories = shownStories + 1
            local expanded = expandedStories[story.key]
            table.insert(items, { type = "story", story = story, done = done, total = total, started = started,
                complete = complete, ignored = ignored, expanded = expanded,
                elsewhere = story.zone ~= areaID and story.zone or nil,
                repProblems = not complete and ns:GetStoryReputationProblems(story) or nil })
            if expanded then
                local index = 0
                for _, step in ipairs(story.steps) do
                    local questID, state = ns:ResolveStep(step)
                    if questID then
                        index = index + 1
                        table.insert(items, { type = "step", questID = questID, state = state, index = index,
                            step = step, story = story })
                    end
                end
            end
        end
    end
    if #stories == 0 then
        local anyIgnored = #ns:GetZoneStories(areaID, true) > 0
        local hasSide = #ns:GetZoneSideQuests(areaID) > 0
        local isDungeon = ns.Zones[areaID].group == 3
        table.insert(items, { type = "note", text = (anyIgnored and "You are ignoring every storyline here.")
            or (hasSide and "No storylines here, only side quests (below).")
            or (isDungeon and "No quests are known for this dungeon yet. They will appear in an update.")
            or "No storylines in this zone for your character." })
    elseif shownStories == 0 and filtered > 0 then
        table.insert(items, { type = "note", text = "All storylines left here are hidden by your level filters." })
    elseif shownStories == 0 then
        table.insert(items, { type = "note", text = "All storylines here are complete!" })
    elseif filtered > 0 then
        table.insert(items, { type = "note", text = ("%d more storyline%s hidden by your level filters."):format(
            filtered, filtered == 1 and "" or "s") })
    end

    if db.showSide then
        local side = ns:GetZoneSideQuests(areaID)
        local list, done, total, sideFiltered = {}, 0, 0, 0
        for _, entry in ipairs(side) do
            local ignored = ns:IsQuestIgnored(entry.questID)
            if not ignored then
                total = total + 1
                if entry.state == ns.STATE_DONE then
                    done = done + 1
                end
            end
            if (db.showIgnored or not ignored) and not (db.hideCompleted and entry.state == ns.STATE_DONE) then
                local level = ns:GetQuestLevel(entry.questID)
                if entry.state == ns.STATE_TODO and HiddenByLevel(level, level) then
                    sideFiltered = sideFiltered + 1
                else
                    table.insert(list, entry)
                end
            end
        end
        if total > 0 or #list > 0 then
            table.insert(items, { type = "spacer" })
            table.insert(items, { type = "sideHeader", done = done, total = total })
            if not sideCollapsed then
                for _, entry in ipairs(list) do
                    table.insert(items, { type = "side", questID = entry.questID, state = entry.state,
                        elsewhere = entry.homeZone })
                end
                if sideFiltered > 0 then
                    table.insert(items, { type = "note", text = ("%d more side quest%s hidden by your level filters."):format(
                        sideFiltered, sideFiltered == 1 and "" or "s") })
                end
            end
        end
    end
    return items
end

---------------------------------------------------------------------------
-- Search: storylines and quests by name
---------------------------------------------------------------------------

local MAX_SEARCH_RESULTS = 200

local function BuildSearchItems(text)
    local zones, stories, quests = {}, {}, {}
    -- Zones, dungeons, battlegrounds and your class and profession entries.
    for areaID, zone in pairs(ns.Zones) do
        local name = ns:GetZoneName(areaID)
        if (name:lower():find(text, 1, true) or zone.name:lower():find(text, 1, true)) and ns:IsZoneForPlayer(zone) then
            local done, total, sideDone, sideTotal = ns:GetZoneProgress(areaID)
            if total > 0 or sideTotal > 0 or zone.group == 3 then
                zones[#zones + 1] = { type = "zoneResult", search = true, areaID = areaID, name = name,
                    done = done, total = total, sideDone = sideDone, sideTotal = sideTotal }
            end
        end
    end
    for _, story in pairs(ns.storyByKey) do
        if story.name:lower():find(text, 1, true) then
            local done, total, started = ns:GetStoryProgress(story)
            if total > 0 then
                stories[#stories + 1] = { type = "story", search = true, story = story, done = done, total = total,
                    started = started, complete = done == total, ignored = ns:IsStoryIgnored(story),
                    elsewhere = story.zone, areaID = story.zone }
            end
        end
    end
    for questID, q in pairs(ns.Quests) do
        local name = ns:GetQuestName(questID)
        if (name:lower():find(text, 1, true) or q[1]:lower():find(text, 1, true)) and ns:IsQuestForPlayer(questID) then
            local list = ns.storiesByQuest[questID]
            local story = list and list[1]
            local areaID = story and story.zone or ns.sideZoneByQuest[questID]
            if areaID then
                quests[#quests + 1] = { type = "side", search = true, questID = questID, story = story,
                    storyName = story and story.name or "side quest", elsewhere = areaID, areaID = areaID,
                    state = select(2, ns:ResolveStep(questID)), sortName = name }
            end
        end
    end
    table.sort(zones, function(a, b) return a.name < b.name end)
    table.sort(stories, function(a, b) return a.story.name < b.story.name end)
    table.sort(quests, function(a, b)
        if a.sortName ~= b.sortName then
            return a.sortName < b.sortName
        end
        return a.questID < b.questID
    end)
    local items = {}
    if #zones > 0 then
        items[#items + 1] = { type = "header", text = "Zones", count = #zones }
        for _, zone in ipairs(zones) do
            items[#items + 1] = zone
        end
    end
    if #stories > 0 then
        if #items > 0 then
            items[#items + 1] = { type = "spacer" }
        end
        items[#items + 1] = { type = "header", text = "Storylines", count = #stories }
        for i = 1, math.min(#stories, MAX_SEARCH_RESULTS) do
            items[#items + 1] = stories[i]
        end
    end
    if #quests > 0 then
        if #items > 0 then
            items[#items + 1] = { type = "spacer" }
        end
        items[#items + 1] = { type = "header", text = "Quests", count = #quests }
        for i = 1, math.min(#quests, MAX_SEARCH_RESULTS) do
            items[#items + 1] = quests[i]
        end
    end
    if #stories > MAX_SEARCH_RESULTS or #quests > MAX_SEARCH_RESULTS then
        items[#items + 1] = { type = "note", text = ("Showing the first %d of each. Type more of the name."):format(
            MAX_SEARCH_RESULTS) }
    end
    if #items == 0 then
        items[#items + 1] = { type = "note", text = "No zone, storyline or quest found for your character." }
    end
    return items, #zones, #stories, #quests
end

--- Quest icon like the game's: yellow "?" ready to turn in, grey "?" in progress,
-- yellow "!" can be picked up now, grey "!" not available yet.
-- @return icon, desaturated, availability ("available" / "locked" / "reputation" / "level" / "skill" for quests
--   not started),
--   and the availability detail (required level, or the reputation problem)
function ns:GetQuestIcon(questID, state)
    if state == ns.STATE_DONE then
        return ICON_DONE, false
    elseif state == ns.STATE_READY then
        return ICON_ACTIVE, false
    elseif state == ns.STATE_ACTIVE then
        return ICON_ACTIVE, true
    end
    local availability, detail = ns:GetQuestAvailability(questID)
    return ICON_AVAILABLE, availability ~= "available", availability, detail
end

local function isInspected(item)
    local view = ns:GetInspected()
    if item.type == "story" then
        return view.kind == "story" and view.story == item.story
    end
    return view.kind == "quest" and view.questID == item.questID
end

local function UpdateStoryRow(row, item)
    if item.type == "story" then
        local low, high = ns:GetStoryLevelRange(item.story)
        local levels = ""
        if low then
            levels = "|cff909090Lvl|r " .. (low == high and ns:ColorLevel(low) or (ns:ColorLevel(low) .. "|cff909090-|r" .. ns:ColorLevel(high))) .. "   "
        end
        local icon, desat
        if item.ignored then
            icon, desat = ICON_IGNORED, false
        elseif item.complete then
            icon, desat = ICON_DONE, false
        elseif item.started then
            icon, desat = ICON_WAITING, false
        else
            icon, desat = ICON_AVAILABLE, true
        end
        SetRow(row, {
            icon = icon,
            desaturate = desat,
            text = (item.expanded and "- " or "+ ") .. item.story.name .. ns:GetStoryTagMarkup(item.story, 14)
                .. ((item.repProblems and #item.repProblems > 0) and (" |T" .. ns.WARNING_ICON .. ":14:14|t") or "")
                .. (item.elsewhere and (" |cff909090(" .. ns:GetZoneName(item.elsewhere) .. ")|r") or "")
                .. (item.ignored and " |cffff6060(ignored)|r" or ""),
            font = "GameFontNormal",
            color = (item.complete or item.ignored) and COLOR_DONE or COLOR_GOLD,
            strike = item.complete,
            selected = isInspected(item),
            right = levels .. progressColor(item.done, item.total) .. item.done .. "/" .. item.total .. "|r",
        })
    elseif item.type == "step" or item.type == "side" then
        local icon, desat, availability, detail = ns:GetQuestIcon(item.questID, item.state)
        local ignored = ns:IsQuestIgnored(item.questID)
        local color = COLOR_WHITE
        if ignored or item.state == ns.STATE_DONE then
            color = COLOR_DONE
        elseif availability and availability ~= "available" then
            color = COLOR_LOCKED
        end
        local right = ""
        if ignored then
            right = "|cffff6060ignored|r"
        elseif item.state == ns.STATE_READY then
            right = "|cff40ff40turn in|r"
        elseif item.state == ns.STATE_ACTIVE then
            right = "|cffffd100in log|r"
        elseif availability == "level" then
            right = "|cffff4040level " .. detail .. "|r"
        elseif availability == "skill" then
            right = "|cffff4040" .. ns:GetProfessionName(detail.skill) .. " " .. detail.level .. "|r"
        elseif availability == "reputation" then
            right = "|cffff4040" .. (detail.tooHigh and "rep too high" or ("needs " .. ns:FormatReputation(detail.required)))
                .. "|r"
        elseif availability == "available" and item.type == "step" then
            right = "|cffffd100available|r"
        end
        SetRow(row, {
            indent = item.type == "step" and 18 or 6,
            icon = ignored and ICON_IGNORED or icon,
            desaturate = desat and not ignored,
            text = ns:FormatQuestLine(item.questID, item.type == "step" and (item.index .. ". ") or nil, item.state)
                .. (item.storyName and ("  |cffffd100" .. item.storyName .. "|r") or "")
                .. (item.elsewhere and (" |cff909090(" .. ns:GetZoneName(item.elsewhere) .. ")|r") or ""),
            font = "GameFontHighlightSmall",
            color = color,
            strike = item.state == ns.STATE_DONE,
            selected = isInspected(item),
            right = right,
        })
    elseif item.type == "sideHeader" then
        SetRow(row, {
            icon = sideCollapsed and ICON_EXPAND or ICON_COLLAPSE,
            text = "Side Quests",
            font = "GameFontNormal",
            color = COLOR_GOLD,
            right = progressColor(item.done, item.total) .. item.done .. "/" .. item.total .. "|r",
        })
    elseif item.type == "zoneResult" then
        local zone = ns.Zones[item.areaID]
        local where = ns.GROUP_NAMES[zone.group]
        if zone.parent and zone.parent > 0 and ns.Zones[zone.parent] then
            where = ns:GetZoneName(zone.parent)
        end
        local done, total, right = item.done, item.total, nil
        if total == 0 and item.sideTotal == 0 then
            right = "|cff707070no quests yet|r"
        elseif total == 0 then
            done, total = item.sideDone, item.sideTotal
            right = "|cff909090side|r " .. progressColor(done, total) .. done .. "/" .. total .. "|r"
        end
        SetRow(row, {
            icon = item.areaID == ns.currentArea and ICON_HERE or nil,
            text = item.name .. " |cff909090(" .. where .. ")|r",
            font = "GameFontNormal",
            color = (total > 0 and done == total) and COLOR_GREEN or COLOR_WHITE,
            right = right or (progressColor(done, total) .. done .. "/" .. total .. "|r"),
        })
    elseif item.type == "header" then
        SetRow(row, { text = item.text, font = "GameFontNormal", color = COLOR_GOLD, right = tostring(item.count) })
    elseif item.type == "note" then
        SetRow(row, { text = item.text, font = "GameFontDisable", color = COLOR_DONE })
    else
        SetRow(row, {})
    end
end

local function ScrollStoryListTo(match)
    local list = frame.storyList
    for i, item in ipairs(list.items) do
        if match(item) then
            local visible = list:NumVisible()
            if i <= list.offset or i > list.offset + visible then
                list.offset = math.max(0, i - 2)
                list:Update()
            end
            return
        end
    end
end

--- Clicking a search result: show its zone with the storyline open, and its details.
local function OpenSearchResult(item)
    local story = item.story
    ns:ClearSearch()
    if story then
        expandedStories[story.key] = true
    end
    ns:SelectArea(item.areaID)
    if item.type == "zoneResult" then
        return
    elseif item.questID then
        ns:InspectQuest(item.questID, story)
        ScrollStoryListTo(function(i) return i.questID == item.questID end)
    else
        ns:InspectStory(story)
        ScrollStoryListTo(function(i) return i.type == "story" and i.story == story end)
    end
end

local function OnStoryRowClick(row, button)
    local item = row.item
    if not item then
        return
    end
    if item.search and button ~= "RightButton" then
        OpenSearchResult(item)
    elseif item.type == "story" then
        if button == "RightButton" then
            local ignored = not ns:IsStoryIgnored(item.story)
            ns:SetStoryIgnored(item.story, ignored)
            ns:Print((ignored and "Ignoring storyline %s. Tick \"Show ignored\" to see it again."
                or "Storyline %s is no longer ignored."):format("|cffffd100" .. item.story.name .. "|r"))
        else
            local view = ns:GetInspected()
            if view.kind == "story" and view.story == item.story then
                -- Second click on the inspected storyline collapses it again.
                expandedStories[item.story.key] = not expandedStories[item.story.key] or nil
            else
                expandedStories[item.story.key] = true
            end
            ns:InspectStory(item.story)
        end
        ns:RefreshUI(true)
    elseif item.type == "step" or item.type == "side" then
        if button == "RightButton" then
            ns:SetQuestIgnored(item.questID, not ns:IsQuestIgnored(item.questID))
            ns:RefreshUI(true)
        elseif IsShiftKeyDown() and ChatEdit_GetActiveWindow and ChatEdit_GetActiveWindow() then
            ChatEdit_GetActiveWindow():Insert(("[%s] (%d)"):format(ns:GetQuestName(item.questID), item.questID))
        else
            ns:InspectQuest(item.questID, item.story)
        end
    elseif item.type == "sideHeader" then
        sideCollapsed = not sideCollapsed
        ns:RefreshUI(true)
    end
end

local function OnStoryRowEnter(row)
    local item = row.item
    if not item then
        return
    end
    if item.type == "story" then
        GameTooltip:SetOwner(row, "ANCHOR_RIGHT")
        GameTooltip:SetText(item.story.name, 1, 0.82, 0)
        GameTooltip:AddLine(("%d of %d quests completed"):format(item.done, item.total), 1, 1, 1)
        if item.elsewhere and not item.search then
            GameTooltip:AddLine(("Also listed here because it starts or continues here; it belongs to %s."):format(
                ns:GetZoneName(item.elsewhere)), 0.6, 0.8, 1, true)
        end
        if item.complete then
            GameTooltip:AddLine("Storyline complete!", 0.25, 1, 0.25)
        end
        if item.repProblems and #item.repProblems > 0 then
            GameTooltip:AddLine(" ")
            GameTooltip:AddLine(("|T%s:14:14|t Your reputation is too low for %d quest%s here:"):format(ns.WARNING_ICON,
                #item.repProblems, #item.repProblems == 1 and "" or "s"), 1, 0.4, 0.4)
            for _, entry in ipairs(item.repProblems) do
                GameTooltip:AddLine("  " .. ns:GetQuestName(entry.questID) .. ": "
                    .. ns:DescribeReputationProblem(entry.problem), 1, 1, 1, true)
            end
        end
        GameTooltip:AddLine(" ")
        GameTooltip:AddLine("Click to inspect the storyline and show its quests.", 0.6, 0.6, 0.6)
        GameTooltip:AddLine(item.ignored and "Right-click to stop ignoring this storyline."
            or "Right-click to ignore this storyline.", 0.6, 0.6, 0.6)
        GameTooltip:Show()
    elseif item.type == "step" or item.type == "side" then
        local questID = item.questID
        GameTooltip:SetOwner(row, "ANCHOR_RIGHT")
        GameTooltip:SetText(ns:GetQuestName(questID), 1, 0.82, 0)
        local level = ns:GetQuestLevel(questID)
        if level > 0 then
            local r, g, b = ns:GetLevelColor(level)
            GameTooltip:AddLine("Level " .. level .. " - " .. ns:GetDifficultyName(level), r, g, b)
        end
        local tag = ns:GetQuestTag(questID)
        if tag then
            GameTooltip:AddLine(ns:GetTagMarkup(tag, 14) .. " " .. ns:GetTagName(tag) .. " quest", 1, 1, 1)
        end
        GameTooltip:AddLine(ns:GetQuestStatusText(questID, item.state))
        if item.step and type(item.step) == "table" then
            GameTooltip:AddLine("Any one of these completes this step:", 0.8, 0.8, 0.8)
            for _, alt in ipairs(item.step) do
                if ns:IsQuestForPlayer(alt) then
                    GameTooltip:AddLine("  " .. ns:GetQuestName(alt) .. " |cff909090(" .. alt .. ")|r", 1, 1, 1)
                end
            end
        end
        GameTooltip:AddLine("Quest ID: " .. questID, 0.6, 0.6, 0.6)
        GameTooltip:AddLine(" ")
        GameTooltip:AddLine("Click for quest details.", 0.6, 0.6, 0.6)
        GameTooltip:AddLine(ns:IsQuestIgnored(questID) and "Right-click to count this quest again."
            or "Right-click to ignore this quest (if it is not available to you).", 0.6, 0.6, 0.6)
        GameTooltip:Show()
    end
end

---------------------------------------------------------------------------
-- Main frame
---------------------------------------------------------------------------

local function CreateMainFrame()
    local f = CreateFrame("Frame", "StorylinesFrame", UIParent, BackdropTemplateMixin and "BackdropTemplate")
    f:SetSize(FRAME_WIDTH, FRAME_HEIGHT)
    f:SetPoint("CENTER")
    f:SetFrameStrata("HIGH")
    f:SetToplevel(true)
    f:SetClampedToScreen(true)
    f:SetMovable(true)
    f:SetResizable(true)
    if f.SetResizeBounds then
        f:SetResizeBounds(MIN_WIDTH, MIN_HEIGHT)
    elseif f.SetMinResize then
        f:SetMinResize(MIN_WIDTH, MIN_HEIGHT)
    end
    f:EnableMouse(true)
    f:RegisterForDrag("LeftButton")

    local function saveGeometry(self)
        self:StopMovingOrSizing()
        local point, _, relPoint, x, y = self:GetPoint()
        ns.db.position = { point, relPoint, x, y }
        ns.db.size = { math.floor(self:GetWidth() + 0.5), math.floor(self:GetHeight() + 0.5) }
        if ns.RefreshInspector then
            ns:RefreshInspector(true) -- re-dock on the side that has room
        end
    end
    f:SetScript("OnDragStart", function(self)
        if not ns.db.locked then
            self:StartMoving()
        end
    end)
    f:SetScript("OnDragStop", saveGeometry)
    SetBackdropSafe(f, "Interface\\DialogFrame\\UI-DialogBox-Background-Dark",
        "Interface\\DialogFrame\\UI-DialogBox-Border", 32, 11)
    f:Hide()

    -- Resize grip in the bottom-right corner.
    local grip = CreateFrame("Button", nil, f)
    grip:SetSize(16, 16)
    grip:SetPoint("BOTTOMRIGHT", -5, 5)
    grip:SetNormalTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Up")
    grip:SetHighlightTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Highlight")
    grip:SetPushedTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Down")
    grip:SetScript("OnMouseDown", function()
        if not ns.db.locked then
            f:StartSizing("BOTTOMRIGHT")
        end
    end)
    grip:SetScript("OnMouseUp", function()
        saveGeometry(f)
    end)
    grip:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:SetText("Drag to resize", 1, 1, 1)
        GameTooltip:Show()
    end)
    grip:SetScript("OnLeave", GameTooltip_Hide)
    f.resizeGrip = grip

    local title = f:CreateFontString(nil, "ARTWORK", "GameFontNormalLarge")
    title:SetPoint("TOP", 0, -18)
    title:SetText("Storylines")

    -- Search box (top left): storylines and quests by name.
    local search = CreateFrame("EditBox", "StorylinesSearchBox", f, "InputBoxTemplate")
    search:SetSize(190, 20)
    search:SetPoint("TOPLEFT", 26, -15)
    search:SetAutoFocus(false)
    search:SetMaxLetters(60)
    search.hint = search:CreateFontString(nil, "ARTWORK", "GameFontDisableSmall")
    search.hint:SetPoint("LEFT", 2, 0)
    search.hint:SetText("Search zones, storylines, quests")
    local clear = CreateFrame("Button", nil, search)
    clear:SetSize(14, 14)
    clear:SetPoint("RIGHT", -2, 0)
    clear:SetNormalTexture("Interface\\FriendsFrame\\ClearBroadcastIcon")
    clear:SetScript("OnClick", function()
        ns:ClearSearch()
    end)
    clear:Hide()
    search.clear = clear
    search:SetScript("OnTextChanged", function(self)
        local text = self:GetText() or ""
        self.hint:SetShown(text == "" and not self:HasFocus())
        clear:SetShown(text ~= "")
        ns:SetSearch(text)
    end)
    search:SetScript("OnEditFocusGained", function(self)
        self.hint:Hide()
    end)
    search:SetScript("OnEditFocusLost", function(self)
        self.hint:SetShown((self:GetText() or "") == "")
    end)
    search:SetScript("OnEscapePressed", function(self)
        if (self:GetText() or "") ~= "" then
            ns:ClearSearch()
        end
        self:ClearFocus()
    end)
    search:SetScript("OnEnterPressed", search.ClearFocus)
    f.search = search

    local close = CreateFrame("Button", nil, f, "UIPanelCloseButton")
    close:SetPoint("TOPRIGHT", -6, -6)

    -- Left: zones
    local zonePanel = CreateFrame("Frame", nil, f, BackdropTemplateMixin and "BackdropTemplate")
    zonePanel:SetPoint("TOPLEFT", 16, -44)
    zonePanel:SetPoint("BOTTOMLEFT", 16, 48)
    zonePanel:SetWidth(ZONE_LIST_WIDTH)
    SetBackdropSafe(zonePanel, "Interface\\Tooltips\\UI-Tooltip-Background", "Interface\\Tooltips\\UI-Tooltip-Border", 14, 3)
    zonePanel:SetBackdropBorderColor(0.6, 0.6, 0.6, 0.8)
    f.zonePanel = zonePanel

    f.zoneList = CreateList(zonePanel, function(row)
        InitRow(row)
        row:SetScript("OnClick", OnZoneRowClick)
        row:SetScript("OnEnter", OnZoneRowEnter)
        row:SetScript("OnLeave", GameTooltip_Hide)
    end, UpdateZoneRow)
    f.zoneList:SetPoint("TOPLEFT", 5, -5)
    f.zoneList:SetPoint("BOTTOMRIGHT", -5, 5)

    -- Right: header + stories
    local detail = CreateFrame("Frame", nil, f, BackdropTemplateMixin and "BackdropTemplate")
    detail:SetPoint("TOPLEFT", zonePanel, "TOPRIGHT", 8, 0)
    detail:SetPoint("BOTTOMRIGHT", -16, 48)
    SetBackdropSafe(detail, "Interface\\Tooltips\\UI-Tooltip-Background", "Interface\\Tooltips\\UI-Tooltip-Border", 14, 3)
    detail:SetBackdropBorderColor(0.6, 0.6, 0.6, 0.8)
    f.detailPanel = detail

    f.zoneTitle = detail:CreateFontString(nil, "ARTWORK", "GameFontNormalLarge")
    f.zoneTitle:SetPoint("TOPLEFT", 12, -10)
    f.zoneTitle:SetJustifyH("LEFT")

    f.zoneSummary = detail:CreateFontString(nil, "ARTWORK", "GameFontHighlightSmall")
    f.zoneSummary:SetPoint("TOPRIGHT", -12, -14)
    f.zoneSummary:SetJustifyH("RIGHT")

    local bar = CreateFrame("StatusBar", nil, detail)
    bar:SetPoint("TOPLEFT", 12, -34)
    bar:SetPoint("TOPRIGHT", -12, -34)
    bar:SetHeight(10)
    bar:SetStatusBarTexture("Interface\\TargetingFrame\\UI-StatusBar")
    bar:SetStatusBarColor(0.95, 0.75, 0.1)
    bar:SetMinMaxValues(0, 1)
    local barBg = bar:CreateTexture(nil, "BACKGROUND")
    barBg:SetAllPoints()
    barBg:SetColorTexture(0, 0, 0, 0.6)
    f.progressBar = bar

    f.storyList = CreateList(detail, function(row)
        InitRow(row)
        row:SetScript("OnClick", OnStoryRowClick)
        row:SetScript("OnEnter", OnStoryRowEnter)
        row:SetScript("OnLeave", GameTooltip_Hide)
    end, UpdateStoryRow)
    f.storyList:SetPoint("TOPLEFT", 6, -52)
    f.storyList:SetPoint("BOTTOMRIGHT", -5, 5)

    -- Bottom: options
    local hideCompleted = CreateCheckbox(f, "Hide completed", "Hide storylines and quests you have already completed.",
        function(checked)
            ns.db.hideCompleted = checked
            ns:RefreshUI()
        end)
    hideCompleted:SetPoint("BOTTOMLEFT", 18, 16)
    hideCompleted:SetChecked(ns.db.hideCompleted)

    local showSide = CreateCheckbox(f, "Side quests", "List quests that are not part of any storyline below the storylines.",
        function(checked)
            ns.db.showSide = checked
            ns:RefreshUI()
        end)
    showSide:SetPoint("LEFT", hideCompleted.label, "RIGHT", 16, -1)
    showSide:SetChecked(ns.db.showSide)

    local showIgnored = CreateCheckbox(f, "Show ignored", "Show storylines and quests you have ignored with right-click.",
        function(checked)
            ns.db.showIgnored = checked
            ns:RefreshUI()
        end)
    showIgnored:SetPoint("LEFT", showSide.label, "RIGHT", 16, -1)
    showIgnored:SetChecked(ns.db.showIgnored)

    local autoZone = CreateCheckbox(f, "Follow my zone", "Switch to the zone you are in whenever you open the window or change zones.",
        function(checked)
            ns.db.autoZone = checked
            if checked then
                ns:SelectArea(ns:GetCurrentArea() or ns.selectedArea)
            end
        end)
    autoZone:SetPoint("LEFT", showIgnored.label, "RIGHT", 16, -1)
    autoZone:SetChecked(ns.db.autoZone)
    -- Kept in sync with the options page (see ApplyWindowSettings).
    f.checks = { hideCompleted = hideCompleted, showSide = showSide, showIgnored = showIgnored, autoZone = autoZone }

    local currentButton = CreateFrame("Button", nil, f, "UIPanelButtonTemplate")
    currentButton:SetSize(120, 22)
    currentButton:SetPoint("BOTTOMRIGHT", -24, 16)
    currentButton:SetText("Current Zone")
    currentButton:SetScript("OnClick", function()
        local areaID = ns:GetCurrentArea()
        if areaID then
            ns:SelectArea(areaID)
        else
            ns:Print("There are no storylines for your current zone.")
        end
    end)

    f:SetScript("OnShow", function()
        ns:RefreshUI()
    end)
    return f
end

local function SetEscapeCloses(enabled)
    for i = #UISpecialFrames, 1, -1 do
        if UISpecialFrames[i] == "StorylinesFrame" then
            table.remove(UISpecialFrames, i)
        end
    end
    if enabled then
        tinsert(UISpecialFrames, "StorylinesFrame")
    end
end

--- Applies the window settings (size, position, scale, opacity, lock, Escape) to the main window.
function ns:ApplyWindowSettings()
    if not frame then
        return
    end
    local db = self.db
    frame:SetScale(db.scale or 1)
    local size = db.size
    frame:SetSize(math.max(MIN_WIDTH, size and size[1] or FRAME_WIDTH), math.max(MIN_HEIGHT, size and size[2] or FRAME_HEIGHT))
    frame:ClearAllPoints()
    local p = db.position
    if p then
        frame:SetPoint(p[1], UIParent, p[2], p[3], p[4])
    else
        frame:SetPoint("CENTER")
    end
    local alpha = db.bgAlpha or 1
    frame:SetBackdropColor(1, 1, 1, alpha)
    frame.zonePanel:SetBackdropColor(0, 0, 0, 0.5 * alpha)
    frame.detailPanel:SetBackdropColor(0, 0, 0, 0.5 * alpha)
    frame.resizeGrip:SetShown(not db.locked)
    SetEscapeCloses(db.escClose)
    for key, check in pairs(frame.checks) do
        check:SetChecked(db[key])
    end
end

--- Applies every setting after it changed (options page, reset).
function ns:ApplySettings()
    self:ApplyTextSize()
    self:ApplyWindowSettings()
    if self.UpdateMinimapButton then
        self:UpdateMinimapButton()
    end
    if frame and frame:IsShown() then
        -- Rows are re-laid out with the new text size.
        frame.zoneList:Update()
        self:RefreshUI(true)
    end
end

---------------------------------------------------------------------------
-- Public functions
---------------------------------------------------------------------------

local function ScrollZoneIntoView(areaID)
    local list = frame.zoneList
    for i, item in ipairs(list.items) do
        if item.areaID == areaID then
            local visible = list:NumVisible()
            if i <= list.offset or i > list.offset + visible then
                list.offset = math.max(0, i - math.floor(visible / 2))
                list:Update()
            end
            return
        end
    end
end

function ns:SelectArea(areaID)
    if not areaID or not self.Zones[areaID] then
        return
    end
    local changed = self.selectedArea ~= areaID
    self.selectedArea = areaID
    if frame and frame:IsShown() then
        self:RefreshUI(not changed)
    end
end

function ns:RefreshUI(keepStoryOffset, skipInspector)
    if not frame or not frame:IsShown() then
        return
    end
    self.currentArea = self:GetCurrentArea()
    if not self.selectedArea or not self.Zones[self.selectedArea] then
        self.selectedArea = self.currentArea or next(self.Zones)
    end
    local areaChanged = self.renderedArea ~= self.selectedArea
    if areaChanged then
        keepStoryOffset = false
        self.renderedArea = self.selectedArea
        -- Make sure the newly selected zone is listed and scrolled into view.
        self.db.collapsedGroups[self.Zones[self.selectedArea].group] = false
    end
    frame.zoneList:SetItems(BuildZoneItems(), true)
    if areaChanged then
        ScrollZoneIntoView(self.selectedArea)
    end

    if self.searchText then
        local items, zoneCount, storyCount, questCount = BuildSearchItems(self.searchText)
        frame.zoneTitle:SetText(("Search: |cffffffff%s|r"):format(self.searchRaw))
        frame.zoneSummary:SetText(("Zones: |cffffffff%d|r    Storylines: |cffffffff%d|r    Quests: |cffffffff%d|r"):format(
            zoneCount, storyCount, questCount))
        frame.progressBar:SetValue(0)
        frame.storyList:SetItems(items, keepStoryOffset)
        if not skipInspector and self.RefreshInspector then
            self:RefreshInspector(true)
        end
        return
    end

    local areaID = self.selectedArea
    local zone = self.Zones[areaID]
    local title = self:GetZoneName(areaID)
    if zone.parent and zone.parent > 0 and self.Zones[zone.parent] then
        title = title .. " |cff909090(" .. self:GetZoneName(zone.parent) .. ")|r"
    end
    frame.zoneTitle:SetText(title)
    local done, total, sideDone, sideTotal = self:GetZoneProgress(areaID)
    local summary = ("Storylines: |cffffffff%d / %d|r"):format(done, total)
    if self.db.showSide and sideTotal > 0 then
        summary = summary .. ("    Side quests: |cffffffff%d / %d|r"):format(sideDone, sideTotal)
    end
    frame.zoneSummary:SetText(summary)
    frame.progressBar:SetValue(total > 0 and done / total or 0)
    if total > 0 and done == total then
        frame.progressBar:SetStatusBarColor(0.25, 0.9, 0.25)
    else
        frame.progressBar:SetStatusBarColor(0.95, 0.75, 0.1)
    end
    frame.storyList:SetItems(BuildStoryItems(areaID), keepStoryOffset)
    if not skipInspector and self.RefreshInspector then
        self:RefreshInspector(true)
    end
end

--- Shows storylines and quests whose name contains the text (2 letters or more) instead of the zone.
function ns:SetSearch(text)
    text = strtrim(text or "")
    local search = #text >= 2 and text:lower() or nil
    if search == self.searchText then
        return
    end
    self.searchText, self.searchRaw = search, text
    if frame and frame:IsShown() then
        self:RefreshUI(false)
    end
end

--- Opens the window with a search (/stl find <name>).
function ns:Search(text)
    self:ShowUI()
    frame.search:SetText(text or "")
    frame.search.hint:SetShown((text or "") == "")
    frame.search.clear:SetShown((text or "") ~= "")
    self:SetSearch(text)
end

function ns:ClearSearch()
    if frame and frame.search then
        frame.search:SetText("")
        frame.search:ClearFocus()
        frame.search.clear:Hide()
        frame.search.hint:Show()
    end
    self:SetSearch("")
end

function ns:ShowUI(areaID)
    if not frame then
        frame = CreateMainFrame()
        self:ApplyTextSize()
        self:ApplyWindowSettings()
    end
    if not areaID then
        -- Prefer the zone shown on an open world map, then the player's zone.
        if WorldMapFrame and WorldMapFrame:IsShown() and WorldMapFrame.GetMapID then
            areaID = self:FindAreaForMap(WorldMapFrame:GetMapID())
        end
        if not areaID and (self.db.autoZone or not self.selectedArea) then
            areaID = self:GetCurrentArea()
        end
    end
    if areaID then
        self.selectedArea = areaID
    end
    if frame:IsShown() then
        self:RefreshUI()
    else
        frame:Show() -- OnShow refreshes
    end
end

function ns:ToggleUI()
    if frame and frame:IsShown() then
        frame:Hide()
    else
        self:ShowUI()
    end
end

function ns:OnZoneChanged()
    if not frame or not frame:IsShown() then
        return
    end
    if self.db.autoZone then
        local areaID = self:GetCurrentArea()
        if areaID then
            self.selectedArea = areaID
        end
    end
    self:RefreshUI(true)
end
