local _, ns = ...

local button

local function UpdatePosition()
    local angle = math.rad(ns.db.minimap.angle or 215)
    local radius = (Minimap:GetWidth() / 2) + 5
    button:ClearAllPoints()
    button:SetPoint("CENTER", Minimap, "CENTER", math.cos(angle) * radius, math.sin(angle) * radius)
end

local function OnDragUpdate()
    local mx, my = Minimap:GetCenter()
    local scale = Minimap:GetEffectiveScale()
    local cx, cy = GetCursorPosition()
    cx, cy = cx / scale, cy / scale
    ns.db.minimap.angle = math.deg(math.atan2(cy - my, cx - mx)) % 360
    UpdatePosition()
end

local function ShowTooltip(owner, anchor)
    GameTooltip:SetOwner(owner, anchor or "ANCHOR_LEFT")
    GameTooltip:SetText("Storylines", 1, 0.82, 0)
    local areaID = ns:GetCurrentArea()
    if areaID then
        local done, total, sideDone, sideTotal = ns:GetZoneProgress(areaID)
        GameTooltip:AddLine(ns:GetZoneName(areaID), 1, 1, 1)
        GameTooltip:AddDoubleLine("Storylines", done .. " / " .. total, nil, nil, nil, 1, 1, 1)
        if sideTotal > 0 then
            GameTooltip:AddDoubleLine("Side quests", sideDone .. " / " .. sideTotal, nil, nil, nil, 1, 1, 1)
        end
    end
    GameTooltip:AddLine(" ")
    GameTooltip:AddLine("Click to open. Right-click for options. Drag to move.", 0.6, 0.6, 0.6)
    GameTooltip:Show()
end

function ns:InitMinimapButton()
    if button then
        return
    end
    button = CreateFrame("Button", "StorylinesMinimapButton", Minimap)
    button:SetSize(31, 31)
    button:SetFrameStrata("MEDIUM")
    button:SetFrameLevel(8)
    button:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    button:RegisterForDrag("LeftButton")
    button:SetHighlightTexture("Interface\\Minimap\\UI-Minimap-ZoomButton-Highlight")

    local overlay = button:CreateTexture(nil, "OVERLAY")
    overlay:SetSize(53, 53)
    overlay:SetTexture("Interface\\Minimap\\MiniMap-TrackingBorder")
    overlay:SetPoint("TOPLEFT")

    local background = button:CreateTexture(nil, "BACKGROUND")
    background:SetSize(20, 20)
    background:SetTexture("Interface\\Minimap\\UI-Minimap-Background")
    background:SetPoint("TOPLEFT", 7, -5)

    local icon = button:CreateTexture(nil, "ARTWORK")
    icon:SetSize(17, 17)
    icon:SetTexture("Interface\\Icons\\INV_Misc_Book_09")
    icon:SetTexCoord(0.05, 0.95, 0.05, 0.95)
    icon:SetPoint("TOPLEFT", 7, -6)

    button:SetScript("OnClick", function(_, mouseButton)
        if mouseButton == "RightButton" then
            ns:OpenOptions()
        else
            ns:ToggleUI()
        end
    end)
    button:SetScript("OnDragStart", function(self)
        self:SetScript("OnUpdate", OnDragUpdate)
    end)
    button:SetScript("OnDragStop", function(self)
        self:SetScript("OnUpdate", nil)
    end)
    button:SetScript("OnEnter", function(self)
        ShowTooltip(self)
    end)
    button:SetScript("OnLeave", GameTooltip_Hide)

    UpdatePosition()
    self:UpdateMinimapButton()
end

function ns:UpdateMinimapButton()
    if button then
        button:SetShown(not self.db.minimap.hide)
    end
end

-- Addon compartment (the addon list button on the minimap, when the client has one).
function Storylines_OnAddonCompartmentClick(_, mouseButton)
    if mouseButton == "RightButton" then
        ns:OpenOptions()
    else
        ns:ToggleUI()
    end
end

function Storylines_OnAddonCompartmentEnter(_, menuButton)
    ShowTooltip(menuButton, "ANCHOR_LEFT")
end

function Storylines_OnAddonCompartmentLeave()
    GameTooltip:Hide()
end
