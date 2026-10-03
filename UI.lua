local _, ns = ...

local ROW_HEIGHT = 20
local ZONE_LIST_WIDTH = 230
local FRAME_WIDTH, FRAME_HEIGHT = 780, 540

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
local COLOR_RED = { 1, 0.35, 0.35 }

local frame
local expandedStories = {}
local sideCollapsed = false

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
                row:SetHeight(ROW_HEIGHT)
                row:SetPoint("TOPLEFT", 0, -(i - 1) * ROW_HEIGHT)
                row:SetPoint("RIGHT", bar, "LEFT", -2, 0)
                row:RegisterForClicks("LeftButtonUp", "RightButtonUp")
                row:SetHighlightTexture("Interface\\QuestFrame\\UI-QuestTitleHighlight", "ADD")
                initRow(row)
                self.rows[i] = row
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

    row.right = row:CreateFontString(nil, "ARTWORK", "GameFontHighlightSmall")
    row.right:SetPoint("RIGHT", -4, 0)
    row.right:SetJustifyH("RIGHT")

    row.text = row:CreateFontString(nil, "ARTWORK", "GameFontHighlight")
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
    local font = opts.font or "GameFontHighlight"
    row.text:SetFontObject(_G[font] or font)
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
    local byGroup = {}
    for areaID, zone in pairs(ns.Zones) do
        local done, total = ns:GetZoneProgress(areaID)
        if total > 0 then
            byGroup[zone.group] = byGroup[zone.group] or {}
            table.insert(byGroup[zone.group], { type = "zone", areaID = areaID, done = done, total = total,
                name = ns:GetZoneName(areaID) })
        end
    end
    local items = {}
    for group = 1, #ns.GROUP_NAMES do
        local zones = byGroup[group]
        if zones then
            table.sort(zones, function(a, b) return a.name < b.name end)
            local done, total = 0, 0
            for _, z in ipairs(zones) do
                done, total = done + z.done, total + z.total
            end
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
        SetRow(row, {
            indent = 8,
            icon = isCurrent and ICON_HERE or nil,
            iconSize = 14,
            text = item.name,
            color = (item.done == item.total) and COLOR_GREEN or COLOR_WHITE,
            right = progressColor(item.done, item.total) .. item.done .. "/" .. item.total .. "|r",
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
        ns.db.collapsedGroups[item.group] = not ns.db.collapsedGroups[item.group] or nil
        frame.zoneList:SetItems(BuildZoneItems(), true)
    else
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

local STATE_TEXT = {
    [ns.STATE_DONE] = "|cff40ff40Completed|r",
    [ns.STATE_READY] = "|cff40ff40Ready to turn in|r",
    [ns.STATE_ACTIVE] = "|cffffd100In your quest log|r",
    [ns.STATE_TODO] = "|cffb0b0b0Not completed|r",
}

local function BuildStoryItems(areaID)
    local items = {}
    local db = ns.db
    local stories = ns:GetZoneStories(areaID, db.showIgnored)
    local shownStories = 0
    for _, story in ipairs(stories) do
        local done, total, started = ns:GetStoryProgress(story)
        local complete = total > 0 and done == total
        local ignored = ns:IsStoryIgnored(story)
        if not (db.hideCompleted and complete) then
            shownStories = shownStories + 1
            local expanded = expandedStories[story.key]
            table.insert(items, { type = "story", story = story, done = done, total = total, started = started,
                complete = complete, ignored = ignored, expanded = expanded })
            if expanded then
                local nextFound = false
                local index = 0
                for _, step in ipairs(story.steps) do
                    local questID, state = ns:ResolveStep(step)
                    if questID then
                        index = index + 1
                        local isNext = false
                        if state ~= ns.STATE_DONE and not nextFound and not ns:IsQuestIgnored(questID) then
                            nextFound = true
                            isNext = true
                        end
                        table.insert(items, { type = "step", questID = questID, state = state, index = index,
                            isNext = isNext, step = step, story = story })
                    end
                end
            end
        end
    end
    if #stories == 0 then
        table.insert(items, { type = "note", text = "No storylines in this zone for your character." })
    elseif shownStories == 0 then
        table.insert(items, { type = "note", text = "All storylines here are complete!" })
    end

    if db.showSide then
        local side = ns:GetZoneSideQuests(areaID)
        local list, done, total = {}, 0, 0
        for _, entry in ipairs(side) do
            local ignored = ns:IsQuestIgnored(entry.questID)
            if not ignored then
                total = total + 1
                if entry.state == ns.STATE_DONE then
                    done = done + 1
                end
            end
            if (db.showIgnored or not ignored) and not (db.hideCompleted and entry.state == ns.STATE_DONE) then
                table.insert(list, entry)
            end
        end
        if total > 0 or #list > 0 then
            table.insert(items, { type = "spacer" })
            table.insert(items, { type = "sideHeader", done = done, total = total })
            if not sideCollapsed then
                for _, entry in ipairs(list) do
                    table.insert(items, { type = "side", questID = entry.questID, state = entry.state })
                end
            end
        end
    end
    return items
end

local function stateIcon(state, isNext)
    if state == ns.STATE_DONE then
        return ICON_DONE, false
    elseif state == ns.STATE_READY then
        return ICON_ACTIVE, false
    elseif state == ns.STATE_ACTIVE then
        return ICON_ACTIVE, true
    end
    return ICON_AVAILABLE, not isNext
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
                .. (item.ignored and " |cffff6060(ignored)|r" or ""),
            font = "GameFontNormal",
            color = (item.complete or item.ignored) and COLOR_DONE or COLOR_GOLD,
            strike = item.complete,
            selected = isInspected(item),
            right = levels .. progressColor(item.done, item.total) .. item.done .. "/" .. item.total .. "|r",
        })
    elseif item.type == "step" or item.type == "side" then
        local icon, desat = stateIcon(item.state, item.type == "side" or item.isNext)
        local ignored = ns:IsQuestIgnored(item.questID)
        local color = COLOR_WHITE
        if ignored or item.state == ns.STATE_DONE then
            color = COLOR_DONE
        elseif item.type == "step" and not item.isNext and item.state == ns.STATE_TODO then
            color = { 0.75, 0.75, 0.75 }
        end
        local right = ""
        if ignored then
            right = "|cffff6060ignored|r"
        elseif item.state == ns.STATE_READY then
            right = "|cff40ff40turn in|r"
        elseif item.state == ns.STATE_ACTIVE then
            right = "|cffffd100in log|r"
        elseif item.isNext then
            right = "|cffffd100next|r"
        end
        SetRow(row, {
            indent = item.type == "step" and 18 or 6,
            icon = ignored and ICON_IGNORED or icon,
            desaturate = desat and not ignored,
            text = ns:FormatQuestLine(item.questID, item.type == "step" and (item.index .. ". ") or nil, item.state),
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
    elseif item.type == "note" then
        SetRow(row, { text = item.text, font = "GameFontDisable", color = COLOR_DONE })
    else
        SetRow(row, {})
    end
end

local function OnStoryRowClick(row, button)
    local item = row.item
    if not item then
        return
    end
    if item.type == "story" then
        if button == "RightButton" then
            local key = item.story.key
            ns.db.ignoredStories[key] = not ns.db.ignoredStories[key] or nil
            ns:Print((ns.db.ignoredStories[key] and "Ignoring storyline %s. Tick \"Show ignored\" to see it again."
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
            local id = item.questID
            ns.db.ignoredQuests[id] = not ns.db.ignoredQuests[id] or nil
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
        if item.complete then
            GameTooltip:AddLine("Storyline complete!", 0.25, 1, 0.25)
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
        GameTooltip:AddLine(STATE_TEXT[item.state] or "")
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
    f:EnableMouse(true)
    f:RegisterForDrag("LeftButton")
    f:SetScript("OnDragStart", f.StartMoving)
    f:SetScript("OnDragStop", function(self)
        self:StopMovingOrSizing()
        local point, _, relPoint, x, y = self:GetPoint()
        ns.db.position = { point, relPoint, x, y }
    end)
    SetBackdropSafe(f, "Interface\\DialogFrame\\UI-DialogBox-Background-Dark",
        "Interface\\DialogFrame\\UI-DialogBox-Border", 32, 11)
    f:Hide()
    tinsert(UISpecialFrames, "StorylinesFrame")

    if ns.db.position then
        local p = ns.db.position
        f:ClearAllPoints()
        f:SetPoint(p[1], UIParent, p[2], p[3], p[4])
    end

    local title = f:CreateFontString(nil, "ARTWORK", "GameFontNormalLarge")
    title:SetPoint("TOP", 0, -18)
    title:SetText("Storylines")

    local close = CreateFrame("Button", nil, f, "UIPanelCloseButton")
    close:SetPoint("TOPRIGHT", -6, -6)

    -- Left: zones
    local zonePanel = CreateFrame("Frame", nil, f, BackdropTemplateMixin and "BackdropTemplate")
    zonePanel:SetPoint("TOPLEFT", 16, -44)
    zonePanel:SetPoint("BOTTOMLEFT", 16, 48)
    zonePanel:SetWidth(ZONE_LIST_WIDTH)
    SetBackdropSafe(zonePanel, "Interface\\Tooltips\\UI-Tooltip-Background", "Interface\\Tooltips\\UI-Tooltip-Border", 14, 3)
    zonePanel:SetBackdropColor(0, 0, 0, 0.5)
    zonePanel:SetBackdropBorderColor(0.6, 0.6, 0.6, 0.8)

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
    detail:SetBackdropColor(0, 0, 0, 0.5)
    detail:SetBackdropBorderColor(0.6, 0.6, 0.6, 0.8)

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

    local currentButton = CreateFrame("Button", nil, f, "UIPanelButtonTemplate")
    currentButton:SetSize(120, 22)
    currentButton:SetPoint("BOTTOMRIGHT", -18, 16)
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

---------------------------------------------------------------------------
-- Public functions
---------------------------------------------------------------------------

function ns:SelectArea(areaID)
    if not areaID or not self.Zones[areaID] then
        return
    end
    local changed = self.selectedArea ~= areaID
    self.selectedArea = areaID
    -- Make sure the zone is visible in the list.
    local group = self.Zones[areaID].group
    if self.db.collapsedGroups[group] then
        self.db.collapsedGroups[group] = nil
    end
    if frame and frame:IsShown() then
        self:RefreshUI(not changed)
        if changed then
            for i, item in ipairs(frame.zoneList.items) do
                if item.areaID == areaID then
                    local visible = frame.zoneList:NumVisible()
                    if i <= frame.zoneList.offset or i > frame.zoneList.offset + visible then
                        frame.zoneList.offset = math.max(0, i - math.floor(visible / 2))
                        frame.zoneList:Update()
                    end
                    break
                end
            end
        end
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
    if self.renderedArea ~= self.selectedArea then
        keepStoryOffset = false
        self.renderedArea = self.selectedArea
    end
    frame.zoneList:SetItems(BuildZoneItems(), true)

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

function ns:ShowUI(areaID)
    if not frame then
        frame = CreateMainFrame()
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
    frame:Show()
    self:RefreshUI()
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
