# ContextForge — Papyrus Scripts

This folder contains the Papyrus source scripts (`.psc`) for the ContextForge
Skyrim SE plugin. You need to compile these into `.pex` files before Skyrim
can run them.

This document explains exactly how to do that.

---

## What's in here

| File | Purpose |
|---|---|
| `ContextForge.psc` | Main script — collects game state and writes the JSON file |
| `ContextForgeQuestReporter.psc` | Attach to any quest to track its progress |

---

## What you need

- **Skyrim SE Creation Kit** — free on Steam
  (Library → search "Creation Kit" → install)
- **SKSE64** — must be installed and working first
- **PapyrusUtil SE** — the scripts use JsonUtil from PapyrusUtil

---

## One-time setup

Before you can compile, the Creation Kit needs to know where Skyrim's
source scripts live. You only do this once.

**1. Find your Skyrim source scripts folder**

They ship with the Creation Kit. Default location:
```
C:/Program Files (x86)/Steam/steamapps/common/Skyrim Special Edition/Data/Scripts/Source/
```

**2. Find PapyrusUtil's source scripts**

When you install PapyrusUtil, it adds its own `.psc` files. They should be in
the same `Scripts/Source/` folder, or in your mod manager's overwrite folder
if using MO2.

If they're missing, download PapyrusUtil manually and extract the source
scripts into `Data/Scripts/Source/`.

**3. Configure the Creation Kit compiler**

Open `CreationKit.ini` (in your Skyrim SE root folder) and find or add:

```ini
[Papyrus]
sScriptSourceFolder = ".\Data\Scripts\Source"
sAdditionalImports = "$(source);.\Data\Scripts\Source\User;.\Data\Scripts\Source\Base"
bEnableLogging = 1
bEnableTrace = 1
bLoadDebugInformation = 1
```

---

## Compiling the scripts

**1. Copy the `.psc` files to your source folder**

Copy both files from this folder into:
```
Data/Scripts/Source/
```

**2. Open the Creation Kit**

Launch via SKSE (recommended) or directly. Let it load — it takes a while.

**3. Open the Script Manager**

Go to: **Gameplay → Papyrus Script Manager**

**4. Find and compile ContextForge.psc**

- In the script list, find `ContextForge`
- Right-click → **Compile**
- Repeat for `ContextForgeQuestReporter`

Or select both, right-click → **Compile Selected**.

You should see output like:
```
Compiling "ContextForge"...
No errors.
```

If you see errors, see the Troubleshooting section below.

**5. Find the compiled files**

The `.pex` files are written to:
```
Data/Scripts/
```

Confirm both exist:
- `Data/Scripts/ContextForge.pex`
- `Data/Scripts/ContextForgeQuestReporter.pex`

That's it. Skyrim can now run the scripts.

---

## Creating the ESP

The scripts need a quest to run on. You create this in the Creation Kit.

**1. Create a new plugin**

File → New (or Data → click New at top)

**2. Create the main quest**

- Object Window → Quest → right-click → New
- Editor ID: `CFMainQuest`
- Check **Start Game Enabled**
- Check **Run Once** — uncheck this, we want it running always

**3. Add the script**

- In the Quest window, go to the **Scripts** tab
- Click **Add**
- Find and select `ContextForge`
- Click OK

**4. Save the plugin**

File → Save As → `ContextForge.esp`

Save it to your `Data/` folder.

**5. Enable in your load order**

Add `ContextForge.esp` to your load order via MO2, Vortex, or directly in
the Skyrim launcher. Load order position doesn't matter — put it anywhere.

---

## Troubleshooting compilation errors

**"unknown type JsonUtil"**
PapyrusUtil source scripts aren't in your import path. Find `JsonUtil.psc`
(it ships with PapyrusUtil) and put it in `Data/Scripts/Source/`.

**"unknown type MiscUtil"**
Same issue — MiscUtil.psc is also part of PapyrusUtil.

**"cannot open source file"**
The Creation Kit can't find the `.psc` file. Confirm it's in
`Data/Scripts/Source/` and not in a subfolder.

**Compilation succeeds but `.pex` doesn't appear**
Check the `sScriptSourceFolder` path in `CreationKit.ini` — a typo there
sends the output somewhere unexpected.

**Script compiles but doesn't run in game**
Confirm `ContextForge.esp` is enabled in your load order and that SKSE64
is launching the game (not the default Skyrim launcher).
Check the Papyrus log for errors:
```
Documents/My Games/Skyrim Special Edition/Logs/Script/Papyrus.0.log
```

---

## Using MO2?

If you're using Mod Organizer 2, compiled `.pex` files land in MO2's
overwrite folder rather than directly in `Data/Scripts/`. That's fine —
just create a new mod from the overwrite folder contents and enable it.

---

## Questions?

If something isn't working, open an issue on the
[ContextForge repo](https://github.com/marisombra-dev/ContextForge)
and include the relevant section of your Papyrus log.

---

*Part of ContextForge v0.2*
