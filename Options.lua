local ADDON_NAME, ns = ...

-- The "Storylines" page in the game's Options -> AddOns window. Built from plain frames so it works
-- with both the modern Settings window and the older Interface Options.

local COLUMN_WIDTH = 300
local ROW = 28
local LEFT_X, RIGHT_X = 16, 340

local panel, built
local refreshers = {} -- functions that show the current values

local function Refresh()
    for _, fn in ipairs(refreshers) do
        fn()
    end
end

local function ShowTip(owner, title, text)
    if not text then
        return
    end
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
    GameTooltip:SetText(title, 1, 1, 1)
    GameTooltip:AddLine(text, nil, nil, nil, true)
    GameTooltip:Show()
end

--- A column of settings; widgets are added top to bottom.
local function NewColumn(x, y)
    return { x = x, y = y }
end

local function Label(col, text, tooltip)
    local row = CreateFrame("Frame", nil, panel)
    row:SetPoint("TOPLEFT", col.x, col.y)
    row:SetSize(COLUMN_WIDTH, ROW)
    row:EnableMouse(tooltip ~= nil)
    row:SetScript("OnEnter", function(self)
        ShowTip(self, text, tooltip)
    end)
    row:SetScript("OnLeave", GameTooltip_Hide)
    row.label = row:CreateFontString(nil, "ARTWORK", "GameFontHighlight")
    row.label:SetPoint("LEFT", 0, 0)
    row.label:SetJustifyH("LEFT")
    row.label:SetWordWrap(true)
    row.label:SetText(text)
    col.y = col.y - ROW
    return row
end

local function Header(col, text)
    col.y = col.y - 8
    local fs = panel:CreateFontString(nil, "ARTWORK", "GameFontNormal")
    fs:SetPoint("TOPLEFT", col.x, col.y)
    fs:SetText(text)
    local line = panel:CreateTexture(nil, "ARTWORK")
    line:SetColorTexture(1, 0.82, 0, 0.25)
    line:SetHeight(1)
    line:SetPoint("TOPLEFT", col.x, col.y - 17)
    line:SetWidth(COLUMN_WIDTH)
    col.y = col.y - 24
end

local function Note(col, text)
    local fs = panel:CreateFontString(nil, "ARTWORK", "GameFontDisableSmall")
    fs:SetPoint("TOPLEFT", col.x, col.y + 4)
    fs:SetWidth(COLUMN_WIDTH)
    fs:SetJustifyH("LEFT")
    fs:SetText(text)
    col.y = col.y - 16
end

--- A setting is a key in ns.db, or { get = fn, set = fn } for one stored elsewhere.
local function GetSetting(key)
    if type(key) == "table" then
        return key.get()
    end
    return ns.db[key]
end

local function SetSetting(key, value)
    if type(key) == "table" then
        key.set(value)
    else
        ns.db[key] = value
    end
end

local function Check(col, key, text, tooltip)
    local row = Label(col, text, tooltip)
    row.label:SetPoint("RIGHT", -30, 0)
    local cb = CreateFrame("CheckButton", nil, row)
    cb:SetSize(26, 26)
    cb:SetPoint("RIGHT", 0, 0)
    cb:SetNormalTexture("Interface\\Buttons\\UI-CheckBox-Up")
    cb:SetPushedTexture("Interface\\Buttons\\UI-CheckBox-Down")
    cb:SetHighlightTexture("Interface\\Buttons\\UI-CheckBox-Highlight", "ADD")
    cb:SetCheckedTexture("Interface\\Buttons\\UI-CheckBox-Check")
    cb:SetScript("OnClick", function(self)
        SetSetting(key, self:GetChecked() and true or false)
        ns:ApplySettings()
    end)
    cb:SetScript("OnEnter", function(self)
        ShowTip(self, text, tooltip)
    end)
    cb:SetScript("OnLeave", GameTooltip_Hide)
    table.insert(refreshers, function()
        cb:SetChecked(GetSetting(key) and true or false)
    end)
    return cb
end

local function Slider(col, key, text, tooltip, min, max, step, format)
    local row = Label(col, text, tooltip)
    local value = row:CreateFontString(nil, "ARTWORK", "GameFontHighlightSmall")
    value:SetPoint("RIGHT", 0, 0)
    value:SetWidth(34)
    value:SetJustifyH("RIGHT")
    local slider = CreateFrame("Slider", nil, row, BackdropTemplateMixin and "BackdropTemplate")
    slider:SetOrientation("HORIZONTAL")
    slider:SetSize(100, 16)
    slider:SetPoint("RIGHT", value, "LEFT", -8, 0)
    row.label:SetPoint("RIGHT", slider, "LEFT", -8, 0)
    if not slider.SetBackdrop then
        Mixin(slider, BackdropTemplateMixin)
    end
    slider:SetBackdrop({
        bgFile = "Interface\\Buttons\\UI-SliderBar-Background",
        edgeFile = "Interface\\Buttons\\UI-SliderBar-Border",
        tile = true, tileSize = 8, edgeSize = 8,
        insets = { left = 3, right = 3, top = 6, bottom = 6 },
    })
    slider:SetThumbTexture("Interface\\Buttons\\UI-SliderBar-Button-Horizontal")
    slider:SetMinMaxValues(min, max)
    slider:SetValueStep(step)
    slider:SetObeyStepOnDrag(true)
    slider:EnableMouseWheel(true)
    local updating
    slider:SetScript("OnValueChanged", function(_, v)
        v = math.floor(v / step + 0.5) * step
        value:SetText(format(v))
        if updating then
            return
        end
        if ns.db[key] ~= v then
            ns.db[key] = v
            ns:ApplySettings()
        end
    end)
    slider:SetScript("OnMouseWheel", function(self, delta)
        self:SetValue(math.max(min, math.min(max, self:GetValue() + delta * step)))
    end)
    slider:SetScript("OnEnter", function(self)
        ShowTip(self, text, tooltip)
    end)
    slider:SetScript("OnLeave", GameTooltip_Hide)
    table.insert(refreshers, function()
        updating = true
        slider:SetValue(ns.db[key] or min)
        value:SetText(format(ns.db[key] or min))
        updating = false
    end)
    return slider
end

-- One shared pop-up list for all dropdowns.
local menu
local function ShowMenu(owner, choices, current, onPick)
    if not menu then
        menu = CreateFrame("Frame", "StorylinesOptionsMenu", UIParent, BackdropTemplateMixin and "BackdropTemplate")
        menu:SetFrameStrata("FULLSCREEN_DIALOG")
        menu:SetClampedToScreen(true)
        menu:EnableMouse(true)
        if not menu.SetBackdrop then
            Mixin(menu, BackdropTemplateMixin)
        end
        menu:SetBackdrop({
            bgFile = "Interface\\Tooltips\\UI-Tooltip-Background",
            edgeFile = "Interface\\Tooltips\\UI-Tooltip-Border",
            tile = true, tileSize = 16, edgeSize = 14,
            insets = { left = 3, right = 3, top = 3, bottom = 3 },
        })
        menu:SetBackdropColor(0.05, 0.05, 0.05, 0.95)
        menu.buttons = {}
        menu:Hide()
    end
    if menu:IsShown() and menu.owner == owner then
        menu:Hide()
        return
    end
    menu.owner = owner
    for i, choice in ipairs(choices) do
        local b = menu.buttons[i]
        if not b then
            b = CreateFrame("Button", nil, menu)
            b:SetHeight(20)
            b:SetPoint("TOPLEFT", 6, -6 - (i - 1) * 20)
            b:SetPoint("RIGHT", -6, 0)
            b:SetHighlightTexture("Interface\\QuestFrame\\UI-QuestTitleHighlight", "ADD")
            b.text = b:CreateFontString(nil, "ARTWORK", "GameFontHighlightSmall")
            b.text:SetPoint("LEFT", 18, 0)
            b.check = b:CreateTexture(nil, "ARTWORK")
            b.check:SetSize(14, 14)
            b.check:SetPoint("LEFT", 2, 0)
            b.check:SetTexture("Interface\\Buttons\\UI-CheckBox-Check")
            menu.buttons[i] = b
        end
        b.text:SetText(choice[2])
        b.check:SetShown(choice[1] == current)
        b:SetScript("OnClick", function()
            menu:Hide()
            onPick(choice[1])
        end)
        b:Show()
    end
    for i = #choices + 1, #menu.buttons do
        menu.buttons[i]:Hide()
    end
    menu:SetSize(math.max(owner:GetWidth(), 160), #choices * 20 + 12)
    menu:ClearAllPoints()
    menu:SetPoint("TOPLEFT", owner, "BOTTOMLEFT", 0, -2)
    menu:Show()
end

local function Choice(col, key, text, tooltip, choices)
    local row = Label(col, text, tooltip)
    local button = CreateFrame("Button", nil, row, BackdropTemplateMixin and "BackdropTemplate")
    button:SetSize(150, 22)
    button:SetPoint("RIGHT", 0, 0)
    row.label:SetPoint("RIGHT", button, "LEFT", -8, 0)
    if not button.SetBackdrop then
        Mixin(button, BackdropTemplateMixin)
    end
    button:SetBackdrop({
        bgFile = "Interface\\Tooltips\\UI-Tooltip-Background",
        edgeFile = "Interface\\Tooltips\\UI-Tooltip-Border",
        tile = true, tileSize = 16, edgeSize = 12,
        insets = { left = 3, right = 3, top = 3, bottom = 3 },
    })
    button:SetBackdropColor(0, 0, 0, 0.8)
    button:SetBackdropBorderColor(0.6, 0.6, 0.6, 1)
    button:SetHighlightTexture("Interface\\QuestFrame\\UI-QuestTitleHighlight", "ADD")
    button.text = button:CreateFontString(nil, "ARTWORK", "GameFontHighlightSmall")
    button.text:SetPoint("LEFT", 8, 0)
    button.text:SetPoint("RIGHT", -20, 0)
    button.text:SetJustifyH("LEFT")
    local arrow = button:CreateTexture(nil, "ARTWORK")
    arrow:SetSize(14, 14)
    arrow:SetPoint("RIGHT", -4, 0)
    arrow:SetTexture("Interface\\ChatFrame\\ChatFrameExpandArrow")
    arrow:SetRotation(-math.pi / 2)
    local function show()
        for _, choice in ipairs(choices) do
            if choice[1] == ns.db[key] then
                button.text:SetText(choice[2])
                return
            end
        end
        button.text:SetText(choices[1][2])
    end
    button:SetScript("OnClick", function(self)
        ShowMenu(self, choices, ns.db[key], function(v)
            ns.db[key] = v
            show()
            ns:ApplySettings()
        end)
    end)
    button:SetScript("OnEnter", function(self)
        ShowTip(self, text, tooltip)
    end)
    button:SetScript("OnLeave", GameTooltip_Hide)
    table.insert(refreshers, show)
    return button
end

local function Button(col, text, tooltip, buttonText, onClick)
    local row = Label(col, text, tooltip)
    local b = CreateFrame("Button", nil, row, "UIPanelButtonTemplate")
    b:SetSize(text == "" and 170 or 120, 22)
    b:SetPoint("RIGHT", 0, 0)
    row.label:SetPoint("RIGHT", b, "LEFT", -8, 0)
    b:SetText(buttonText)
    b:SetScript("OnClick", onClick)
    return b, row
end

local function percent(v)
    return math.floor(v * 100 + 0.5) .. "%"
end

local function IgnoredText()
    local stories, quests = 0, 0
    for _ in pairs(ns.db.ignoredStories) do
        stories = stories + 1
    end
    for _ in pairs(ns.db.ignoredQuests) do
        quests = quests + 1
    end
    return ("Ignored: %d storyline%s, %d quest%s"):format(stories, stories == 1 and "" or "s",
        quests, quests == 1 and "" or "s")
end

local function Build()
    built = true
    local title = panel:CreateFontString(nil, "ARTWORK", "GameFontNormalLarge")
    title:SetPoint("TOPLEFT", 16, -16)
    title:SetText("Storylines")
    local getMetadata = (C_AddOns and C_AddOns.GetAddOnMetadata) or GetAddOnMetadata
    local version = getMetadata and getMetadata(ADDON_NAME, "Version")
    local versionText = panel:CreateFontString(nil, "ARTWORK", "GameFontDisableSmall")
    versionText:SetPoint("LEFT", title, "RIGHT", 10, -1)
    versionText:SetText(version and ("Version " .. version) or "")
    local open = CreateFrame("Button", nil, panel, "UIPanelButtonTemplate")
    open:SetSize(140, 22)
    open:SetPoint("TOPRIGHT", -16, -14)
    open:SetText("Open Storylines")
    open:SetScript("OnClick", function()
        if SettingsPanel and SettingsPanel:IsShown() and HideUIPanel then
            HideUIPanel(SettingsPanel)
        elseif InterfaceOptionsFrame and InterfaceOptionsFrame:IsShown() and HideUIPanel then
            HideUIPanel(InterfaceOptionsFrame)
        end
        ns:ShowUI()
    end)

    -- Left column
    local col = NewColumn(LEFT_X, -48)
    Header(col, "Window")
    Slider(col, "scale", "Scale", "Size of the whole window and its details panel.", 0.7, 1.5, 0.05, percent)
    Slider(col, "bgAlpha", "Background opacity", "How see-through the window's background is. Text and icons always "
        .. "stay fully visible.", 0, 1, 0.05, percent)
    Choice(col, "textSize", "Text size", "Size of the text in the lists and the details panel.",
        { { "small", "Small" }, { "normal", "Normal" }, { "large", "Large" } })
    Choice(col, "detailsSide", "Details panel", "Where the details panel opens next to the window.",
        { { "auto", "Side with room" }, { "right", "Right of the window" }, { "left", "Left of the window" } })
    Check(col, "locked", "Lock window", "Stops the window from being moved or resized.")
    Check(col, "escClose", "Close with Escape", "Pressing Escape closes the window.")
    Note(col, "Drag the bottom-right corner of the window to resize it.")
    Button(col, "", nil, "Reset size and position", function()
        ns.db.size, ns.db.position = nil, nil
        ns:ApplySettings()
    end)

    Header(col, "Notifications")
    Check(col, "announce", "Storyline progress in chat", "A chat message when you finish a quest of a storyline, "
        .. "and when a storyline or a whole zone is complete.")
    Choice(col, "repWarnings", "Reputation warnings", "Warn when you talk to a quest giver, or finish a quest, "
        .. "whose quest your reputation is too low for.",
        { { "both", "Chat and screen" }, { "chat", "Chat only" }, { "screen", "Screen only" }, { "off", "Off" } })
    Check(col, "completeSound", "Sound when a storyline is completed", "Plays the quest-complete sound when you "
        .. "finish the last quest of a storyline.")

    Header(col, "Map and minimap")
    Check(col, {
        get = function() return not ns.db.minimap.hide end,
        set = function(v) ns.db.minimap.hide = not v end,
    }, "Show minimap button", "The Storylines button on the minimap.")
    Choice(col, "waypoints", "Waypoints", "What clicking a quest giver's location in the details panel uses.",
        { { "tomtom", "TomTom if installed" }, { "map", "Game map pin" } })

    -- Right column
    col = NewColumn(RIGHT_X, -48)
    Header(col, "Lists")
    Check(col, "hideCompleted", "Hide completed storylines", "Hide storylines and quests you have already completed.")
    Check(col, "showSide", "Show side quests", "List quests that are not part of any storyline below the storylines.")
    Check(col, "showIgnored", "Show ignored quests and storylines", "Show what you have ignored with right-click.")
    Check(col, "autoZone", "Follow my zone", "Switch to the zone you are in whenever you open the window or "
        .. "change zones.")
    Check(col, "hideTrivial", "Hide gray (too low level) quests", "Hide storylines and side quests that are all too "
        .. "low level to give much experience. Ones you have started are always shown.")
    Slider(col, "maxLevelsAbove", "Hide far above my level", "Hide storylines and side quests that start more than "
        .. "this many levels above you. Ones you have started are always shown.", 0, 20, 1, function(v)
            return v == 0 and "Off" or ("+" .. v)
        end)
    Choice(col, "sortBy", "Sort storylines by", "Order of the storylines in a zone. Progress lists the ones you are "
        .. "on first, then new ones, then finished ones.",
        { { "level", "Level" }, { "name", "Name" }, { "progress", "Progress" } })
    Check(col, "hideFinishedZones", "Hide finished zones", "Hide zones in the zone list where you have finished "
        .. "everything. Group totals still count them.")
    Check(col, "showAllProfessions", "Show professions you haven't learned", "List the quests of every profession "
        .. "under Professions, not only the ones this character has learned.")
    Check(col, "showQuestIDs", "Show quest IDs", "Show each quest's ID next to its name, handy for reporting "
        .. "wrong data.")

    Header(col, "Maintenance")
    local _, ignoredRow = Button(col, IgnoredText(), "Quests and storylines you ignored with right-click.",
        "Clear ignored", function()
            ns:ClearIgnored()
            Refresh()
        end)
    table.insert(refreshers, function()
        ignoredRow.label:SetText(IgnoredText())
    end)
    Button(col, "All Storylines settings", "Puts every setting back to its default. Your ignored quests are kept.",
        "Reset to defaults", function()
            ns:ResetSettings()
            ns:ApplySettings()
            Refresh()
        end)
end

panel = CreateFrame("Frame", "StorylinesOptionsPanel")
panel.name = "Storylines"
panel:Hide()
panel:SetScript("OnShow", function()
    if not ns.db then
        return
    end
    if not built then
        Build()
    end
    Refresh()
end)
panel:SetScript("OnHide", function()
    if menu then
        menu:Hide()
    end
end)

if Settings and Settings.RegisterCanvasLayoutCategory and Settings.RegisterAddOnCategory then
    local category = Settings.RegisterCanvasLayoutCategory(panel, "Storylines")
    Settings.RegisterAddOnCategory(category)
    ns.optionsCategory = category
elseif InterfaceOptions_AddCategory then
    InterfaceOptions_AddCategory(panel)
end

function ns:OpenOptions()
    local category = self.optionsCategory
    if category and Settings and Settings.OpenToCategory then
        Settings.OpenToCategory(category.GetID and category:GetID() or category.ID)
    elseif InterfaceOptionsFrame_OpenToCategory then
        -- Called twice: the first call may only open the window on older clients.
        InterfaceOptionsFrame_OpenToCategory(panel)
        InterfaceOptionsFrame_OpenToCategory(panel)
    else
        self:Print("Options: type /stl help for the commands.")
    end
end
