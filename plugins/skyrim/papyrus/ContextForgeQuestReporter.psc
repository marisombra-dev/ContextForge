; ContextForgeQuestReporter.psc
; Attach this script to any quest in the Creation Kit
; to have it automatically report its state to ContextForge.
;
; Usage in Creation Kit:
;   1. Open a quest
;   2. Add ContextForgeQuestReporter as a script
;   3. Set the QuestDisplayName property to a human-readable name
;   4. That's it — it handles the rest

Scriptname ContextForgeQuestReporter extends Quest

string Property QuestDisplayName = "" Auto
; Human-readable quest name. Set this in the CK.
; If blank, falls back to the quest's editor ID.

string Property OutputPath = "Data/ContextForge/current_state.json" AutoReadOnly


Event OnStageSet(int auiStageID, int auiItemID)
    ; Called whenever this quest advances to a new stage
    ReportQuestState(auiStageID)
EndEvent

Function ReportQuestState(int stageID)
    string questName = QuestDisplayName
    if questName == ""
        questName = self.GetName()
    endif

    ; Find the next available slot in the quest array
    int slot = FindQuestSlot(questName)

    string prefix = "quests.active[" + slot + "]"
    JsonUtil.SetStringValue(OutputPath, prefix + ".name",      questName)
    JsonUtil.SetIntValue(   OutputPath, prefix + ".stage",     stageID)
    JsonUtil.SetStringValue(OutputPath, prefix + ".objective", GetCurrentObjective(stageID))

    ; Update quest count
    int currentCount = JsonUtil.GetIntValue(OutputPath, "quests.active_count", 0)
    if slot >= currentCount
        JsonUtil.SetIntValue(OutputPath, "quests.active_count", slot + 1)
    endif

    JsonUtil.Save(OutputPath, true)
EndFunction

int Function FindQuestSlot(string questName)
    ; Look for existing slot for this quest, or find next empty one
    int i = 0
    int maxSlots = 20
    while i < maxSlots
        string existingName = JsonUtil.GetStringValue(OutputPath, "quests.active[" + i + "].name", "")
        if existingName == questName || existingName == ""
            return i
        endif
        i += 1
    endwhile
    return 0   ; fallback — overwrite slot 0
EndFunction

string Function GetCurrentObjective(int stageID)
    ; Returns the display text for the current stage's objective
    ; Papyrus doesn't expose objective text directly —
    ; this returns a formatted string with the stage number.
    ; Future: map stage IDs to objective strings via a string table property.
    return "Stage " + stageID
EndFunction
