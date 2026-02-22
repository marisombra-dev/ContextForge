; ContextForge.psc
; Papyrus script for Skyrim SE
; Dumps game state to a JSON file every 30 seconds and on significant events.
; Requires: SKSE64, PapyrusUtil SE
;
; Installation:
;   Compile this script and place the .pex in:
;   Data/Scripts/ContextForge.pex
;
;   Place ContextForge.esp in your Data folder and enable it.
;   The quest CFMainQuest will autostart and run this script.

Scriptname ContextForge extends Quest

; ── Properties ────────────────────────────────────────────────────────────────
; Set these in the Creation Kit on the CFMainQuest quest object.

float Property HeartbeatInterval = 30.0 AutoReadOnly
; How often to write a full heartbeat (seconds). Default 30.

string Property OutputPath = "Data/ContextForge/current_state.json" AutoReadOnly
; Where to write the state file. Relative to Skyrim install directory.


; ── State tracking ─────────────────────────────────────────────────────────────

bool _inCombat      = false
bool _isDead        = false
string _lastCell    = ""
int _lastLevel      = 0
string _lastQuest   = ""


; ── Entry point ────────────────────────────────────────────────────────────────

Event OnInit()
    RegisterForSingleUpdate(2.0)   ; short delay on init, let the game settle
    _lastCell  = GetCurrentCellName()
    _lastLevel = Game.GetPlayer().GetLevel()
    _inCombat  = Game.GetPlayer().IsInCombat()
EndEvent

Event OnUpdate()
    WriteHeartbeat()
    RegisterForSingleUpdate(HeartbeatInterval)
EndEvent


; ── Event triggers ─────────────────────────────────────────────────────────────
; These fire immediately — don't wait for the next heartbeat.

Event OnCombatStateChanged(Actor akTarget, int aeCombatState)
    if akTarget == Game.GetPlayer()
        if aeCombatState == 1 && !_inCombat
            _inCombat = true
            WriteEvent("combat_start")
        elseif aeCombatState == 0 && _inCombat
            _inCombat = false
            WriteEvent("combat_end")
        endif
    endif
EndEvent

Event OnLocationChange(Location akOldLoc, Location akNewLoc)
    WriteEvent("location_change")
EndEvent

Event OnLevelIncrease(int akNewLevel)
    _lastLevel = akNewLevel
    WriteEvent("level_up")
EndEvent

Event OnDeath(Actor akKiller)
    WriteEvent("player_death")
EndEvent

Event OnPlayerLoadGame()
    WriteHeartbeat()
EndEvent


; ── State writer ───────────────────────────────────────────────────────────────

Function WriteHeartbeat()
    string json = BuildStateJSON("heartbeat", "")
    JsonUtil.Save(OutputPath, true)
    WriteFullState(json, "heartbeat", "")
EndFunction

Function WriteEvent(string eventType)
    WriteFullState(BuildStateJSON("event", eventType), "event", eventType)
EndFunction

Function WriteFullState(string json, string updateType, string eventType)
    ; Clear and rebuild the JSON object
    JsonUtil.CleanAll(OutputPath)

    Actor player = Game.GetPlayer()

    ; ── Schema & meta ──────────────────────────────────────────────────────
    JsonUtil.SetStringValue(OutputPath, "schema_version",  "1.0")
    JsonUtil.SetStringValue(OutputPath, "plugin_id",       "skyrim-se")
    JsonUtil.SetStringValue(OutputPath, "plugin_version",  "0.1")
    JsonUtil.SetStringValue(OutputPath, "game_name",       "Skyrim Special Edition")
    JsonUtil.SetStringValue(OutputPath, "update_type",     updateType)
    JsonUtil.SetStringValue(OutputPath, "event_type",      eventType)

    ; ── Player ─────────────────────────────────────────────────────────────
    JsonUtil.SetStringValue(OutputPath, "player.name",    player.GetDisplayName())
    JsonUtil.SetIntValue(   OutputPath, "player.level",   player.GetLevel())

    float healthMax = player.GetBaseActorValue("Health")
    float healthCur = player.GetActorValue("Health")
    JsonUtil.SetFloatValue( OutputPath, "player.health_current", healthCur)
    JsonUtil.SetFloatValue( OutputPath, "player.health_max",     healthMax)

    float staminaMax = player.GetBaseActorValue("Stamina")
    float staminaCur = player.GetActorValue("Stamina")
    JsonUtil.SetFloatValue( OutputPath, "player.stamina_current", staminaCur)
    JsonUtil.SetFloatValue( OutputPath, "player.stamina_max",     staminaMax)

    float magickaMax = player.GetBaseActorValue("Magicka")
    float magickaCur = player.GetActorValue("Magicka")
    JsonUtil.SetFloatValue( OutputPath, "player.magicka_current", magickaCur)
    JsonUtil.SetFloatValue( OutputPath, "player.magicka_max",     magickaMax)

    JsonUtil.SetIntValue(   OutputPath, "player.dragon_souls",   player.GetActorValue("DragonSouls") as int)
    JsonUtil.SetBoolValue(  OutputPath, "player.is_sneaking",    player.IsSneaking())
    JsonUtil.SetBoolValue(  OutputPath, "player.is_swimming",    player.IsSwimming())

    ; Equipped items
    Form rightHand = player.GetEquippedObject(1)
    Form leftHand  = player.GetEquippedObject(0)
    if rightHand
        JsonUtil.SetStringValue(OutputPath, "player.equipped_right", rightHand.GetName())
    endif
    if leftHand
        JsonUtil.SetStringValue(OutputPath, "player.equipped_left", leftHand.GetName())
    endif

    ; ── Location ───────────────────────────────────────────────────────────
    string cellName = GetCurrentCellName()
    JsonUtil.SetStringValue(OutputPath, "location.cell_name",   cellName)
    JsonUtil.SetBoolValue(  OutputPath, "location.is_interior", player.IsInInterior())

    Location currentLoc = player.GetCurrentLocation()
    if currentLoc
        JsonUtil.SetStringValue(OutputPath, "location.hold", currentLoc.GetName())
    endif

    ; ── World ──────────────────────────────────────────────────────────────
    JsonUtil.SetFloatValue( OutputPath, "world.game_hour",  GameHour.GetValue())
    JsonUtil.SetBoolValue(  OutputPath, "world.in_combat",  player.IsInCombat())

    ; Weather
    Weather currentWeather = Weather.GetCurrentWeather()
    if currentWeather
        int weatherType = currentWeather.GetClassification()
        string weatherName = "Clear"
        if weatherType == 1
            weatherName = "Cloudy"
        elseif weatherType == 2
            weatherName = "Rainy"
        elseif weatherType == 3
            weatherName = "Snow"
        endif
        JsonUtil.SetStringValue(OutputPath, "world.weather", weatherName)
    endif

    ; ── Quests ─────────────────────────────────────────────────────────────
    ; Active quests — iterate known quests and check status
    ; Note: Papyrus has no native "get all active quests" — we check a curated list
    ; Community contributors can extend this list in the ESP
    int questCount = 0
    ; Quest data written by individual quest scripts via ContextForgeQuestReporter
    ; (see ContextForgeQuestReporter.psc)

    ; ── Nearby actors ──────────────────────────────────────────────────────
    ; Get actors in a 2048-unit radius
    Actor[] nearbyActors = GetNearbyActors(player, 2048.0)
    int actorCount = 0
    int i = 0
    while i < nearbyActors.Length && actorCount < 10
        Actor a = nearbyActors[i]
        if a && a != player && !a.IsDead()
            string prefix = "entities_nearby[" + actorCount + "]"
            JsonUtil.SetStringValue(OutputPath, prefix + ".name",       a.GetDisplayName())
            JsonUtil.SetBoolValue(  OutputPath, prefix + ".is_hostile", a.IsHostileToActor(player))
            JsonUtil.SetBoolValue(  OutputPath, prefix + ".is_follower", IsFollower(a))
            JsonUtil.SetFloatValue( OutputPath, prefix + ".distance",   player.GetDistance(a))
            actorCount += 1
        endif
        i += 1
    endwhile
    JsonUtil.SetIntValue(OutputPath, "entities_nearby_count", actorCount)

    ; ── Bounty ─────────────────────────────────────────────────────────────
    JsonUtil.SetIntValue(OutputPath, "bounty.whiterun",    player.GetCrimeGold(Faction_CWImperialFaction))
    ; Full hold bounties require faction references set as properties in the ESP.
    ; See ContextForge.esp properties for the complete list.

    ; ── Session deaths ─────────────────────────────────────────────────────
    ; Tracked by a separate counter incremented in OnDeath
    JsonUtil.SetIntValue(OutputPath, "session_deaths", GetSessionDeaths())

    ; ── Save to disk ───────────────────────────────────────────────────────
    JsonUtil.Save(OutputPath, true)

EndFunction


; ── Helpers ────────────────────────────────────────────────────────────────────

string Function GetCurrentCellName()
    Cell currentCell = Game.GetPlayer().GetParentCell()
    if currentCell
        return currentCell.GetName()
    endif
    return "Unknown"
EndFunction

Actor[] Function GetNearbyActors(Actor akCenter, float radius)
    ; PapyrusUtil provides MiscUtil.GetNearbyActors
    return MiscUtil.GetNearbyActors(akCenter, radius)
EndFunction

bool Function IsFollower(Actor akActor)
    return akActor.IsPlayerTeammate()
EndFunction

int _sessionDeaths = 0

int Function GetSessionDeaths()
    return _sessionDeaths
EndFunction

; Called from OnDeath
Function IncrementDeaths()
    _sessionDeaths += 1
EndFunction
