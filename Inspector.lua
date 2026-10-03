local _, ns = ...

-- Inspector: a panel docked to the right of the main window that shows a storyline overview
-- or the full details of one quest.

local WIDTH = 340
local PADDING = 14
local LINE_HEIGHT = 18

local ICON_DONE = "Interface\\RaidFrame\\ReadyCheck-Ready"
local ICON_ACTIVE = "Interface\\GossipFrame\\ActiveQuestIcon"
local ICON_AVAILABLE = "Interface\\GossipFrame\\AvailableQuestIcon"
local ICON_PIN = "Interface\\Icons\\INV_Misc_Map_01"

local panel
local view = {} -- { kind = "story" | "quest", story = story, questID = id }

local STATUS_TEXT = {
    [ns.STATE_DONE] = "|cff40ff40Completed|r",
    [ns.STATE_READY] = "|cff40ff40Ready to turn in|r",
    [ns.STATE_ACTIVE] = "|cffffd100In your quest log|r",
    [ns.STATE_TODO] = "|cffb0b0b0Not completed|r",
}

---------------------------------------------------------------------------
-- Layout: a scrollable column of text blocks and clickable lines
---------------------------------------------------------------------------

local content, cursor
local textPool, linePool = {}, {}
local textUsed, lineUsed = 0, 0

local function contentWidth()
    return WIDTH - 2 * PADDING - 14
end

local function AddText(text, font, color, indent, gap)
    textUsed = textUsed + 1
    local fs = textPool[textUsed]
    if not fs then
        fs = content:CreateFontString(nil, "ARTWORK")
        fs:SetJustifyH("LEFT")
        fs:SetJustifyV("TOP")
        fs:SetWordWrap(true)
        textPool[textUsed] = fs
    end
    indent = indent or 0
    local fontName = font or "GameFontHighlight"
    fs:SetFontObject(_G[fontName] or fontName)
    fs:ClearAllPoints()
    fs:SetPoint("TOPLEFT", indent, cursor)
    fs:SetWidth(contentWidth() - indent)
    fs:SetText(text)
    local c = color or { 1, 1, 1 }
    fs:SetTextColor(c[1], c[2], c[3])
    fs:Show()
    cursor = cursor - (fs:GetStringHeight() or 12) - (gap or 4)
    return fs
end

local function AddGap(height)
    cursor = cursor - (height or 8)
end

local function AddHeader(text)
    AddGap(6)
    AddText(text, "GameFontNormal", { 1, 0.82, 0 }, 0, 3)
end

--- A clickable line with an icon. opts: icon, iconTag, desaturate, text, color, font, right, onClick, onEnter, indent
local function AddLine(opts)
    lineUsed = lineUsed + 1
    local line = linePool[lineUsed]
    if not line then
        line = CreateFrame("Button", nil, content)
        line:SetHeight(LINE_HEIGHT)
        line:RegisterForClicks("LeftButtonUp")
        line:SetHighlightTexture("Interface\\QuestFrame\\UI-QuestTitleHighlight", "ADD")
        line.icon = line:CreateTexture(nil, "ARTWORK")
        line.icon:SetSize(14, 14)
        line.right = line:CreateFontString(nil, "ARTWORK", "GameFontHighlightSmall")
        line.right:SetPoint("RIGHT", -2, 0)
        line.text = line:CreateFontString(nil, "ARTWORK", "GameFontHighlightSmall")
        line.text:SetPoint("LEFT", line.icon, "RIGHT", 4, 0)
        line.text:SetPoint("RIGHT", line.right, "LEFT", -4, 0)
        line.text:SetJustifyH("LEFT")
        line.text:SetWordWrap(false)
        line:SetScript("OnLeave", GameTooltip_Hide)
        linePool[lineUsed] = line
    end
    local indent = opts.indent or 0
    line:ClearAllPoints()
    line:SetPoint("TOPLEFT", indent, cursor)
    line:SetWidth(contentWidth() - indent)
    line.icon:ClearAllPoints()
    line.icon:SetPoint("LEFT", 2, 0)
    line.icon:SetTexCoord(0, 1, 0, 1)
    if opts.iconTag then
        ns:SetTagTexture(line.icon, opts.iconTag)
    else
        line.icon:SetTexture(opts.icon)
    end
    line.icon:SetDesaturated(opts.desaturate or false)
    line.text:SetFontObject(opts.font and _G[opts.font] or GameFontHighlightSmall)
    line.text:SetText(opts.text or "")
    local c = opts.color or { 1, 1, 1 }
    line.text:SetTextColor(c[1], c[2], c[3])
    line.right:SetText(opts.right or "")
    line:SetScript("OnClick", opts.onClick)
    line:SetScript("OnEnter", opts.onEnter)
    line:EnableMouse(opts.onClick ~= nil or opts.onEnter ~= nil)
    line:Show()
    cursor = cursor - LINE_HEIGHT - 1
    return line
end

local function BeginLayout()
    for i = 1, textUsed do
        textPool[i]:Hide()
    end
    for i = 1, lineUsed do
        linePool[i]:Hide()
    end
    textUsed, lineUsed = 0, 0
    cursor = 0
end

local function EndLayout(keepScroll)
    local height = -cursor + 8
    content:SetHeight(height)
    local maxScroll = math.max(0, height - panel.scroll:GetHeight())
    panel.bar:SetMinMaxValues(0, maxScroll)
    panel.bar:SetShown(maxScroll > 0)
    if not keepScroll then
        panel.bar:SetValue(0)
    else
        panel.bar:SetValue(math.min(panel.bar:GetValue(), maxScroll))
    end
end

---------------------------------------------------------------------------
-- Shared bits
---------------------------------------------------------------------------

local function stateIcon(state, highlight)
    if state == ns.STATE_DONE then
        return ICON_DONE, false
    elseif state == ns.STATE_READY or state == ns.STATE_ACTIVE then
        return ICON_ACTIVE, state == ns.STATE_ACTIVE
    end
    return ICON_AVAILABLE, not highlight
end

--- "[18] Quest name <type icon>" with the level colored by difficulty.
function ns:FormatQuestLine(questID, prefix, state)
    local level = self:GetQuestLevel(questID)
    local levelText = ""
    if level > 0 then
        levelText = (state == self.STATE_DONE) and ("|cff808080[" .. level .. "]|r ")
            or (self:ColorLevel(level, "[" .. level .. "]") .. " ")
    end
    local tag = self:GetQuestTag(questID)
    local tagText = tag and (" " .. self:GetTagMarkup(tag, 13)) or ""
    return (prefix or "") .. levelText .. self:GetQuestName(questID) .. tagText
end

local function questTooltip(questID)
    return function(self)
        GameTooltip:SetOwner(self, "ANCHOR_LEFT")
        GameTooltip:SetText(ns:GetQuestName(questID), 1, 0.82, 0)
        local level = ns:GetQuestLevel(questID)
        if level > 0 then
            local r, g, b = ns:GetLevelColor(level)
            GameTooltip:AddLine("Level " .. level .. " - " .. ns:GetDifficultyName(level), r, g, b)
        end
        local tag = ns:GetQuestTag(questID)
        if tag then
            GameTooltip:AddLine(ns:GetTagName(tag) .. " quest", 1, 1, 1)
        end
        GameTooltip:AddLine("Click for details.", 0.6, 0.6, 0.6)
        GameTooltip:Show()
    end
end

local function AddQuestLine(questID, prefix, indent)
    local _, state = ns:ResolveStep(questID)
    local icon, desat = stateIcon(state, true)
    return AddLine({
        icon = icon,
        desaturate = desat,
        indent = indent,
        text = ns:FormatQuestLine(questID, prefix, state),
        color = (state == ns.STATE_DONE or ns:IsQuestIgnored(questID)) and { 0.55, 0.55, 0.55 } or nil,
        right = (state == ns.STATE_ACTIVE and "|cffffd100in log|r") or (state == ns.STATE_READY and "|cff40ff40turn in|r") or "",
        onClick = function()
            ns:InspectQuest(questID, view.story)
        end,
        onEnter = questTooltip(questID),
    })
end

local function AddGiver(kind, id, label)
    local name, title, areaID, x, y = ns:GetGiver(kind, id)
    if not name then
        AddText("Unknown", "GameFontDisableSmall", { 0.6, 0.6, 0.6 }, 4)
        return
    end
    local who = name
    if title then
        who = who .. " |cff909090<" .. title .. ">|r"
    end
    if kind == 2 then
        who = who .. " |cff909090(object)|r"
    elseif kind == 3 then
        who = "|cff909090Starts from the item|r " .. name
    end
    AddText(who, "GameFontHighlight", nil, 4, 1)
    local where = ns:FormatLocation(areaID, x, y)
    if where then
        if ns:CanSetWaypoint(areaID, x, y) then
            AddLine({
                icon = ICON_PIN,
                indent = 4,
                text = "|cff8ab4ff" .. where .. "|r",
                onClick = function()
                    ns:SetWaypoint(areaID, x, y, name)
                end,
                onEnter = function(self)
                    GameTooltip:SetOwner(self, "ANCHOR_LEFT")
                    GameTooltip:SetText(label .. ": " .. name, 1, 0.82, 0)
                    GameTooltip:AddLine(where, 1, 1, 1)
                    GameTooltip:AddLine("Click to set a map waypoint.", 0.6, 0.6, 0.6)
                    GameTooltip:Show()
                end,
            })
        else
            AddText(where, "GameFontHighlightSmall", { 0.7, 0.7, 0.7 }, 4)
        end
    end
end

---------------------------------------------------------------------------
-- Views
---------------------------------------------------------------------------

local function RenderStory(story)
    local done, total = ns:GetStoryProgress(story)
    local complete = total > 0 and done == total
    AddText(story.name .. ns:GetStoryTagMarkup(story, 16), "GameFontNormalLarge", { 1, 0.82, 0 }, 0, 6)
    AddText(ns:GetZoneName(story.zone), "GameFontHighlightSmall", { 0.7, 0.7, 0.7 }, 0, 8)

    local low, high = ns:GetStoryLevelRange(story)
    if low then
        local levels = (low == high) and ns:ColorLevel(low) or (ns:ColorLevel(low) .. " - " .. ns:ColorLevel(high))
        AddText("Levels: " .. levels, "GameFontHighlight", nil, 0, 2)
    end
    local status = complete and "|cff40ff40Complete!|r" or (done > 0 and "|cffffd100In progress|r" or "|cffb0b0b0Not started|r")
    AddText(("Progress: %d / %d quests   %s"):format(done, total, status), "GameFontHighlight", nil, 0, 2)

    local xpLeft = 0
    local first, nextQuest
    for _, step in ipairs(story.steps) do
        local questID, state = ns:ResolveStep(step)
        if questID then
            first = first or questID
            if state ~= ns.STATE_DONE then
                xpLeft = xpLeft + ns:GetQuestXP(questID)
                nextQuest = nextQuest or questID
            end
        end
    end
    if xpLeft > 0 then
        AddText(("Experience left: %s XP"):format(ns:FormatNumber(xpLeft)), "GameFontHighlight", nil, 0, 2)
    end
    local tags = ns:GetStoryTags(story)
    if #tags > 0 then
        local names = {}
        for _, tag in ipairs(tags) do
            names[#names + 1] = ns:GetTagMarkup(tag, 14) .. " " .. ns:GetTagName(tag)
        end
        AddText("Includes: " .. table.concat(names, "   "), "GameFontHighlight", nil, 0, 2)
    end

    local startQuest = nextQuest or first
    local details = startQuest and ns:GetQuestDetails(startQuest)
    if details and details.giverKind > 0 then
        AddHeader(nextQuest and nextQuest ~= first and "Continue with" or "Starts with")
        AddQuestLine(startQuest)
        AddGiver(details.giverKind, details.giverID, "Quest giver")
    end

    AddHeader("Quests")
    local index = 0
    for _, step in ipairs(story.steps) do
        local questID = ns:ResolveStep(step)
        if questID then
            index = index + 1
            AddQuestLine(questID, index .. ". ")
        end
    end
end

local function RenderQuest(questID, story)
    local details = ns:GetQuestDetails(questID) or {}
    local _, state = ns:ResolveStep(questID)
    if story then
        AddLine({
            icon = "Interface\\Buttons\\UI-SpellbookIcon-PrevPage-Up",
            text = "|cffffd100" .. story.name .. "|r",
            onClick = function()
                ns:InspectStory(story)
            end,
        })
        AddGap(4)
    end

    local tag = details.tag and details.tag ~= 0 and details.tag
    AddText(ns:GetQuestName(questID) .. (tag and (" " .. ns:GetTagMarkup(tag, 16)) or ""), "GameFontNormalLarge",
        { 1, 0.82, 0 }, 0, 6)

    local level = ns:GetQuestLevel(questID)
    local levelLine = ""
    if level > 0 then
        levelLine = "Level " .. ns:ColorLevel(level) .. "  |cff909090(" .. ns:GetDifficultyName(level) .. ")|r"
    end
    if details.requiredLevel and details.requiredLevel > 0 then
        local playerLevel = UnitLevel("player") or 1
        local req = tostring(details.requiredLevel)
        if playerLevel < details.requiredLevel then
            req = "|cffff4040" .. req .. "|r"
        end
        levelLine = levelLine .. "    Requires level " .. req
    end
    if levelLine ~= "" then
        AddText(levelLine, "GameFontHighlight", nil, 0, 2)
    end
    if tag then
        AddText(ns:GetTagMarkup(tag, 14) .. " " .. ns:GetTagName(tag) .. " quest"
            .. ((tag == ns.TAG_ELITE or tag == ns.TAG_DUNGEON or tag == ns.TAG_RAID) and " |cff909090- bring a group|r" or ""),
            "GameFontHighlight", nil, 0, 2)
    end
    AddText("Status: " .. (STATUS_TEXT[state] or ""), "GameFontHighlight", nil, 0, 2)
    if ns:IsQuestIgnored(questID) then
        AddText("You are ignoring this quest.", "GameFontHighlightSmall", { 1, 0.4, 0.4 }, 0, 2)
    end
    if story then
        local index, total = 0, 0
        for _, step in ipairs(story.steps) do
            local id = ns:ResolveStep(step)
            if id then
                total = total + 1
                for _, alt in ipairs(ns.StepIDs(step)) do
                    if alt == questID then
                        index = total
                    end
                end
            end
        end
        if index > 0 then
            AddText(("Quest %d of %d in this storyline"):format(index, total), "GameFontHighlightSmall", { 0.7, 0.7, 0.7 }, 0, 2)
        end
    end

    if details.objectives and details.objectives ~= "" then
        AddHeader("Objectives")
        AddText(ns:FormatQuestText(details.objectives), "GameFontHighlight", { 0.95, 0.95, 0.95 }, 4, 4)
    end

    if details.giverKind and details.giverKind > 0 then
        AddHeader("Quest giver")
        AddGiver(details.giverKind, details.giverID, "Quest giver")
    end
    if details.turnInKind and details.turnInKind > 0 then
        AddHeader("Turn in")
        AddGiver(details.turnInKind, details.turnInID, "Turn in")
    end

    local xp, baseXP = ns:GetQuestXP(questID)
    local hasRewards = baseXP > 0 or #(details.reputation or {}) > 0 or #(details.items or {}) > 0
    if hasRewards then
        AddHeader("Rewards")
        if baseXP > 0 then
            local text = ns:FormatNumber(xp) .. " XP"
            if xp == 0 then
                text = "No XP at your level |cff909090(" .. ns:FormatNumber(baseXP) .. " below max level)|r"
            elseif xp ~= baseXP then
                -- Reduced XP is estimated (the game rounds it), so mark it as approximate.
                text = "~" .. text .. " |cff909090(" .. ns:FormatNumber(baseXP) .. " at quest level)|r"
            end
            AddText(text, "GameFontHighlight", nil, 4, 2)
        end
        local rep = details.reputation or {}
        for i = 1, #rep - 1, 2 do
            local amount = rep[i + 1]
            AddText(("%s%d|r %s reputation"):format(amount > 0 and "|cff40ff40+" or "|cffff4040", amount,
                ns:GetFactionName(rep[i])), "GameFontHighlight", nil, 4, 2)
        end
        for _, itemID in ipairs(details.items or {}) do
            local name, link, quality, icon = ns:GetItem(itemID)
            local text = name
            if quality and ITEM_QUALITY_COLORS and ITEM_QUALITY_COLORS[quality] then
                text = ITEM_QUALITY_COLORS[quality].hex .. name .. "|r"
            end
            local line = AddLine({
                icon = icon,
                indent = 4,
                text = text,
                font = "GameFontHighlight",
                onClick = function()
                    if link and IsModifiedClick and IsModifiedClick("CHATLINK") and ChatEdit_InsertLink then
                        ChatEdit_InsertLink(link)
                    end
                end,
                onEnter = function(self)
                    GameTooltip:SetOwner(self, "ANCHOR_LEFT")
                    if GameTooltip.SetItemByID then
                        GameTooltip:SetItemByID(itemID)
                    else
                        GameTooltip:SetHyperlink("item:" .. itemID)
                    end
                    GameTooltip:Show()
                end,
            })
            line.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        end
        if #(details.items or {}) > 1 then
            AddText("Item rewards may be a choice of one.", "GameFontDisableSmall", { 0.6, 0.6, 0.6 }, 4, 2)
        end
    end

    local pre = {}
    for _, id in ipairs(details.pre or {}) do
        if ns:IsQuestForPlayer(id) then
            pre[#pre + 1] = id
        end
    end
    if #pre > 0 then
        AddHeader("Requires")
        for _, id in ipairs(pre) do
            AddQuestLine(id)
        end
    end
    local nextList = {}
    for _, id in ipairs(ns:GetNextQuests(questID)) do
        if ns:IsQuestForPlayer(id) then
            nextList[#nextList + 1] = id
        end
    end
    if #nextList > 0 then
        table.sort(nextList)
        AddHeader("Leads to")
        for _, id in ipairs(nextList) do
            AddQuestLine(id)
        end
    end

    AddGap(10)
    AddText("Quest ID " .. questID, "GameFontDisableSmall", { 0.5, 0.5, 0.5 }, 0, 2)
end

---------------------------------------------------------------------------
-- Panel
---------------------------------------------------------------------------

local function CreatePanel()
    local main = StorylinesFrame
    local f = CreateFrame("Frame", "StorylinesInspector", main, BackdropTemplateMixin and "BackdropTemplate")
    f:SetWidth(WIDTH)
    f:EnableMouse(true)
    if not f.SetBackdrop then
        Mixin(f, BackdropTemplateMixin)
    end
    f:SetBackdrop({
        bgFile = "Interface\\DialogFrame\\UI-DialogBox-Background-Dark",
        edgeFile = "Interface\\DialogFrame\\UI-DialogBox-Border",
        tile = true, tileSize = 16, edgeSize = 32,
        insets = { left = 11, right = 11, top = 11, bottom = 11 },
    })

    local title = f:CreateFontString(nil, "ARTWORK", "GameFontNormal")
    title:SetPoint("TOP", 0, -18)
    title:SetText("Details")

    local close = CreateFrame("Button", nil, f, "UIPanelCloseButton")
    close:SetPoint("TOPRIGHT", -6, -6)
    close:SetScript("OnClick", function()
        ns:CloseInspector()
    end)

    local scroll = CreateFrame("ScrollFrame", nil, f)
    scroll:SetPoint("TOPLEFT", PADDING, -40)
    scroll:SetPoint("BOTTOMRIGHT", -PADDING, 18)
    f.scroll = scroll

    content = CreateFrame("Frame", nil, scroll)
    content:SetSize(contentWidth(), 10)
    scroll:SetScrollChild(content)

    local bar = CreateFrame("Slider", nil, f)
    bar:SetOrientation("VERTICAL")
    bar:SetWidth(10)
    bar:SetPoint("TOPRIGHT", scroll, "TOPRIGHT", 0, 0)
    bar:SetPoint("BOTTOMRIGHT", scroll, "BOTTOMRIGHT", 0, 0)
    bar:SetThumbTexture("Interface\\Buttons\\UI-ScrollBar-Knob")
    bar:GetThumbTexture():SetSize(14, 22)
    local track = bar:CreateTexture(nil, "BACKGROUND")
    track:SetAllPoints()
    track:SetColorTexture(0, 0, 0, 0.35)
    bar:SetMinMaxValues(0, 0)
    bar:SetValue(0)
    bar:SetScript("OnValueChanged", function(_, value)
        scroll:SetVerticalScroll(value)
    end)
    f.bar = bar

    -- The scroll range depends on the panel height, which is only known after layout.
    scroll:SetScript("OnSizeChanged", function()
        if cursor then
            EndLayout(true)
        end
    end)
    scroll:EnableMouseWheel(true)
    scroll:SetScript("OnMouseWheel", function(_, delta)
        local _, max = bar:GetMinMaxValues()
        bar:SetValue(math.max(0, math.min(max, bar:GetValue() - delta * 40)))
    end)

    -- Item names arrive asynchronously; redraw when they do.
    f:RegisterEvent("GET_ITEM_INFO_RECEIVED")
    f:SetScript("OnEvent", function()
        if f:IsShown() and not f.pending then
            f.pending = true
            C_Timer.After(0.2, function()
                f.pending = false
                ns:RefreshInspector(true)
            end)
        end
    end)
    f:Hide()
    return f
end

function ns:InspectStory(story)
    view = { kind = "story", story = story }
    self:RefreshInspector()
end

local function storyContains(story, questID)
    for _, step in ipairs(story.steps) do
        for _, id in ipairs(ns.StepIDs(step)) do
            if id == questID then
                return true
            end
        end
    end
    return false
end

function ns:InspectQuest(questID, story)
    -- Following "Requires" / "Leads to" can reach a quest of another storyline: show that one.
    if not story or not storyContains(story, questID) then
        local stories = self.storiesByQuest[questID]
        story = stories and stories[1] or nil
    end
    view = { kind = "quest", questID = questID, story = story }
    self:RefreshInspector()
end

function ns:GetInspected()
    return view
end

function ns:CloseInspector()
    view = {}
    if panel then
        panel:Hide()
    end
    if self.RefreshUI then
        self:RefreshUI(true)
    end
end

function ns:RefreshInspector(keepScroll)
    if not view.kind or not StorylinesFrame or not StorylinesFrame:IsShown() then
        if panel then
            panel:Hide()
        end
        return
    end
    panel = panel or CreatePanel()
    -- Dock on the side of the main window that has room.
    local main = StorylinesFrame
    panel:ClearAllPoints()
    if (main:GetRight() or 0) + WIDTH > (UIParent:GetRight() or math.huge) then
        panel:SetPoint("TOPRIGHT", main, "TOPLEFT", 6, 0)
        panel:SetPoint("BOTTOMRIGHT", main, "BOTTOMLEFT", 6, 0)
    else
        panel:SetPoint("TOPLEFT", main, "TOPRIGHT", -6, 0)
        panel:SetPoint("BOTTOMLEFT", main, "BOTTOMRIGHT", -6, 0)
    end
    panel:Show()
    BeginLayout()
    if view.kind == "story" then
        RenderStory(view.story)
    else
        RenderQuest(view.questID, view.story)
    end
    EndLayout(keepScroll)
    if self.RefreshUI and not keepScroll then
        self:RefreshUI(true, true)
    end
end
