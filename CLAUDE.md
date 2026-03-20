# PYMPLE / pimpleHUB

Roblox script hub hosted on GitHub (`pympleHUB/obfuscatedPYMPLE`). Users execute `MainLoaderUI` in a Roblox executor — it routes to a game-specific script based on `game.PlaceId`.

---

## How scripts link together

```
MainLoaderUI
  └─ loads TrapDoor (key verification + builds S table)
       └─ calls GameRouter (routes by PlaceId)
            └─ loads game script e.g. SailorPiece
                 └─ receives S via (...)
```

The `S` table is the **shared backbone** — it's built in MainScript/TrapDoor and passed to every game script as `...`. Game scripts always start with `local S = ...`.

**S always contains:**
- `S.Hub` — the UI library (from TemplateUI / MainScript)
- `S.Notify` — notification system
- `S.ICON` — `"rbxthumb://type=AvatarHeadShot&id=583572860&w=420&h=420"`
- `S.DISCORD` — Discord invite URL
- `S.Win` — the main hub window (if already created upstream)

---

## Adding a new game (most common task)

**Step 1** — Add the PlaceId in `MainLoaderUI`:
```lua
local GAMES = {
    [77747658251236]  = BASE .. "SailorPiece",
    [107457593564828] = BASE .. "CraftwarsRedux",
    [NEW_PLACE_ID]    = BASE .. "NewScriptName",  -- add here
}
```

**Step 2** — Add in `GameRouter`:
```lua
local GAMES = {
    [77747658251236]  = BASE .. "SailorPiece",
    [107457593564828] = BASE .. "CraftwarsRedux",
    [NEW_PLACE_ID]    = BASE .. "NewScriptName",  -- add here
}
```

**Step 3** — Create the new script file (e.g. `NewScriptName`) using the standard structure below.

---

## Standard game script structure

```lua
local S = ...

local Players        = game:GetService("Players")
local RunService     = game:GetService("RunService")
local UserInputService = game:GetService("UserInputService")
local VirtualUser    = game:GetService("VirtualUser")
local RS             = game:GetService("ReplicatedStorage")
local TweenService   = game:GetService("TweenService")
local LP             = Players.LocalPlayer

local S_local = {}  -- game-specific state/constants
local fn      = {}  -- all functions
local R       = {}  -- remote paths (arrays of strings)
local F       = {}  -- feature flags and settings

-- Remote paths: navigate RS with table of strings
R.TP         = { "Remotes", "TeleportToPortal" }
R.QuestAccept = { "RemoteEvents", "QuestAccept" }
-- etc.

-- Feature flags: all toggleable settings with defaults
F.AutoFarmLevel = false
F.AntiAFK       = true
F.MoveMode      = "Tween"  -- "Tween" | "Teleport"
-- etc.

-- Game-specific constants
S_local.NPC_FOLDER = "NPCs"
S_local.Islands = {
    { Portal = "Starter", FarmUntil = 250, Enemies = { "Thief" }, QuestNPC = "QuestNPC1" },
    -- ...
}
S_local.Bosses = {
    { Name = "BossModelName", Display = "Display Name", Island = "IslandPortalName" },
    -- ...
}

-- UI using S.Hub
local Win = S.Hub.new({
    Name     = '<font size="22">GAMENAME</font>\n<font size="10">PYMPLE</font>',
    Keybind  = "RightAlt",
    Logo     = S.ICON,
    TextSize = 18,
    Font     = Enum.Font.GothamBold,
})

Win:DrawCategory({ Name = "CATEGORY NAME" })
local Tab = Win:DrawTab({ Name = "Tab Name", Icon = "iconkey", EnableScrolling = true })
local Sec = Tab:DrawSection({ Name = "Section Name", Position = "left" })  -- "left" or "right"
Sec:AddParagraph({ Title = "Title", Content = "Body text" })
Sec:AddToggle({ Name = "Feature Name", Default = false, Callback = function(v) F.Feature = v end })
Sec:AddButton({ Name = "Button", Callback = function() end })
Sec:AddSlider({ Name = "Speed", Min = 1, Max = 200, Default = 100, Callback = function(v) F.Speed = v end })
Sec:AddDropdown({ Name = "Mode", Options = { "Tween", "Teleport" }, Default = "Tween", Callback = function(v) F.MoveMode = v end })
```

---

## UI component reference (TemplateUI / S.Hub)

| Method | Purpose |
|--------|---------|
| `S.Hub.new({Name, Keybind, Logo, TextSize, Font})` | Create hub window |
| `Win:DrawCategory({Name})` | Add sidebar category header |
| `Win:DrawTab({Name, Icon, EnableScrolling})` | Add sidebar tab |
| `Tab:DrawSection({Name, Position})` | Add content section ("left"/"right") |
| `Sec:AddParagraph({Title, Content})` | Static text |
| `Sec:AddToggle({Name, Default, Callback})` | Toggle switch |
| `Sec:AddButton({Name, Callback})` | Clickable button |
| `Sec:AddSlider({Name, Min, Max, Default, Callback})` | Number slider |
| `Sec:AddDropdown({Name, Options, Default, Callback})` | Dropdown select |
| `Sec:AddTextBox({Name, Default, Placeholder, Callback})` | Text input |
| `S.Notify.new({Title, Content, Duration, Icon})` | Toast notification |

---

## Color palette (used in all scripts)

```lua
local C = {
    BG    = Color3.fromRGB(18,  18,  20),   -- main background
    Block = Color3.fromRGB(23,  23,  26),   -- section/card bg
    Drop  = Color3.fromRGB(28,  28,  32),   -- input/dropdown bg
    MEntr = Color3.fromRGB(48,  48,  53),   -- hover highlight
    Strok = Color3.fromRGB(45,  45,  45),   -- borders/strokes
    Line  = Color3.fromRGB(65,  65,  65),   -- divider lines
    Text  = Color3.fromRGB(255, 255, 255),  -- all text
    Acnt  = Color3.fromRGB(220, 60,  60),   -- RED accent (primary brand color)
    Green = Color3.fromRGB(55,  210, 95),   -- success states
}
```

---

## Coding conventions

- **Services**: always shortened — `TS`, `UIS`, `LP`, `RS`, `VU`
- **Tables**: `S` (shared state), `fn` (functions), `R` (remotes), `F` (feature flags)
- **Remote navigation**: `R.Name = { "Folder", "SubFolder", "RemoteName" }`
- **All network/game calls**: wrapped in `pcall()`
- **Movement**: `F.MoveMode = "Tween" | "Teleport"`, `F.FarmMode = "Behind" | ...`
- **Difficulty strings**: `"Normal"`, `"Hard"`, `"Nightmare"`
- **Font**: always `Enum.Font.GothamBold`
- **Animations**: `TweenService:Create(obj, TweenInfo.new(dur, style, dir), props):Play()`
- **Glow effects**: multi-layer UIStroke + UIGradient rotation loop (`task.spawn` with 3s tween, reset at 3.05s)
- **UIStroke text shadow**: `mkTS(obj)` helper — `UIStroke` Color black, Thickness 1.8

---

## Files

| File | Role |
|------|------|
| `MainLoaderUI` | Entry point. Routes by PlaceId, fires exec webhook |
| `TrapDoor` | Key verification UI + gate. Builds and passes S to GameRouter |
| `GameRouter` | Secondary PlaceId router (called from TrapDoor context with S) |
| `SailorPiece` | Source for game `77747658251236` — **edit this** |
| `CraftwarsRedux` | Script for game `107457593564828` |
| `TemplateUI` | UI library source (pimpleHUB v2.6) — basis for S.Hub |
| `MainScript` | Core shared script, identical structure to SailorPiece |

---

## Discord bot (`bot.py`)

- Key rotation every 12 hours, active key in `pympleKeyBot`
- Key history: `pympleKeyHistory` (format: `ISO8601|KEYNAME`)
- Counters: `pympleKeyCount` (rotations), `pympleExecCount` (executions)
- Env vars required: `DISCORD_TOKEN`, `GITHUB_TOKEN`, `ANNOUNCE_CHANNEL_ID`, `EXEC_STATS_CHANNEL_ID`, `THUMBNAIL_URL`
- GitHub repo: `pympleHUB/obfuscatedPYMPLE`

## Anti-skid security block (SailorPiece + CraftwarsRedux)

Identical `do...end` block at lines 1–66 of both files. **Webhook URL is NOT hardcoded** — it comes from `shared._pympleWebhook` set by the loader at runtime, so these files are safe to publish publicly.

**Validation checks (in order):**
1. `shared._pympleVerified == true` (must be boolean true, not truthy)
2. `type(shared._pympleAuth) == "string" and #shared._pympleAuth >= 10` — catches fakes like `_pympleAuth = true`
3. `type(shared._pympleTime) == "number"`
4. `tick() - shared._pympleTime < 120` — token expires after 2 minutes

**Webhook reason field values:**
- `"missing auth"` — `_pympleVerified` not set
- `"fake auth token"` — wrong type or too short (someone manually set `shared`)
- `"token expired"` — real token but >120s old
- `"auth invalid"` — passed type checks but failed for another reason
- `"runtime auth tamper"` — `_pympleVerified`/`_pympleAuth` cleared mid-session

**Kick behaviour:** 3 staggered `task.delay` calls at 0.1s, 0.2s, 0.3s — harder to bypass with a single `hookfunction`.

**Periodic re-auth:** `task.spawn` loop checks every 30s while the script runs. If `_pympleVerified` or `_pympleAuth` is cleared after load, triggers full deny + staggered kicks.

**`_pympleAuth` format** (generated by TrapDoor): `tostring(math.random(1000000,9999999)) .. tostring(math.floor(tick()*100) % 99999)` — always a numeric string of 10–12 chars. The `#_auth >= 10` check matches this.

**When adding the block to a new script**, copy the full `do...end` block verbatim from SailorPiece lines 1–66.

---

## Owner bypass UIDs (anti-skid whitelist)

These Roblox UserIds bypass the anti-skid auth check in all scripts. They are **XOR-obfuscated** in source using key `439041101` (`0x1A2B3C4D`) via `bit32.bxor`.

| Real UserId | Obfuscated value | Notes |
|-------------|-----------------|-------|
| `583568138` | `954447687` | Owner |
| `583572860` | `954442033` | Owner (also used for `S.ICON` avatar thumb) |
| `562883881` | `1000853860` | Owner |
| `1251202122` | `1354295303` | Bypass user |

**How to add a new bypass UID:**
1. Compute: `newId XOR 439041101` (use `bit32.bxor(newId, 439041101)` or any XOR calculator)
2. Add the result to the `_ot`/`_ot2` table in: `TemplateUI` (lines ~5 and ~11087), `MainScript`, `CraftwarsRedux`, `SailorPiece`

---

## Important rules

- `SailorPiece` is the editable source for game `77747658251236`
- Never hardcode secrets — always use env vars
- New game scripts must start with `local S = ...` to receive the shared hub
- Match the existing color palette and font exactly — visual consistency matters
