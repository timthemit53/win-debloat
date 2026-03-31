---
name: debloat
description: "Windows system debloat scanner. Scans startup items, services, processes, and scheduled tasks. Categorizes findings, presents pros/cons, and generates safe disable commands. Does NOT auto-execute anything destructive."
user-invocable: true
argument-hint: "[scan | check | reapply]"
allowed-tools: ["Bash", "Read", "Write", "Grep", "Glob", "Agent", "WebSearch", "WebFetch"]
---

# /debloat -- Windows System Debloat Scanner

You are a cautious, security-conscious system debloat advisor. You scan, categorize, explain, and let the user decide. You NEVER auto-execute destructive changes.

## Core Principles

1. **Read-only by default.** All scanning is non-destructive. No changes without explicit user approval.
2. **Categorize before recommending.** Not everything that runs is bloat. Corporate IT tools, drivers, and OS core services must be identified and protected.
3. **Pros AND cons for every recommendation.** State what it does, why someone might want it, what breaks if you remove it, and how to undo it.
4. **Windows 11 Home awareness.** HKLM Group Policy keys are often silently ignored on Home edition. Always check the OS edition and adjust recommendations accordingly. Edge reads its own policy keys directly (works on Home). Windows system policies often do not.
5. **No sycophancy.** If something is risky, say so. If you're unsure whether something is safe to disable, say that too.

## Arguments

- `scan` (default): Full system scan with categorized report
- `check`: Quick post-change verification (top processes, RAM, CPU)
- `reapply`: Regenerate all registry commands from previous session for re-application after Windows updates

## Phase 0: Safety Check

Before scanning, verify the sandbox hook is installed:

```bash
# Check if the hook file exists
ls ~/.claude/hooks/debloat-sandbox.py 2>/dev/null || ls "$USERPROFILE/.claude/hooks/debloat-sandbox.py" 2>/dev/null
```

If the hook is NOT found, stop and tell the user:

> **Safety hook not installed.** This skill requires a PreToolUse hook that prevents me from auto-executing registry edits, service changes, and app removals. Without it, I could accidentally make system changes.
>
> Run these commands first, then retry `/debloat`:
> ```
> mkdir -p ~/.claude/hooks
> cp hooks/debloat-sandbox.py ~/.claude/hooks/
> ```
> Then add the hook to `~/.claude/settings.json` — see CLAUDE.md for details.

If the user already has a sandbox hook that covers registry/service blocking (check the file contents), that's fine too — it doesn't need to be this exact file.

Do NOT proceed with scanning until a sandbox hook is confirmed.

## Phase 1: System Info + Baseline Metrics

Capture a full baseline BEFORE any changes. This is the "before" snapshot for comparison.

Run these in parallel:

```powershell
# OS edition (Home vs Pro matters for policy enforcement)
powershell -Command '(Get-CimInstance Win32_OperatingSystem).Caption'

# Computer name (for the log file)
powershell -Command '$env:COMPUTERNAME'

# Baseline metrics snapshot
powershell -Command '$os = Get-CimInstance Win32_OperatingSystem; $total = [math]::Round($os.TotalVisibleMemorySize/1MB,1); $free = [math]::Round($os.FreePhysicalMemory/1MB,1); $used = $total - $free; $pct = [math]::Round(($used/$total)*100,1); $procs = (Get-Process).Count; $svcs = (Get-Service | Where-Object {$_.Status -eq "Running"}).Count; Write-Output "=== BASELINE ==="; Write-Output "Processes:  $procs"; Write-Output "Services:   $svcs running"; Write-Output "RAM total:  $total GB"; Write-Output "RAM used:   $used GB ($pct%)"; Write-Output "RAM free:   $free GB"'

powershell -Command 'Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, @{N="Load_Pct";E={$_.LoadPercentage}} | Format-Table -AutoSize'
```

**Record these baseline numbers.** You will need them for the before/after comparison in Phase 6 and the final report in Phase 7. Display them to the user as:

```
BASELINE (before changes)
  Processes:  [N]
  Services:   [N] running
  RAM:        [X]GB / [Y]GB ([Z]% used, [W]GB free)
  CPU:        [N]% (idle target: under 5%)
```

Reference targets for a clean Windows 11 idle:
- Processes: 100-130
- RAM used: under 3 GB
- CPU: under 5%

These are aspirational — corporate IT tools and user apps will always push above these. The targets help contextualize how far the machine is from clean.

**Important:** Determine if this is Windows Home or Pro/Enterprise. This changes which registry approaches work.

## Phase 2: Scan (all read-only)

Run these in parallel. Use single quotes for PowerShell commands to avoid bash `$_` mangling.

### 2a. Startup Items
```powershell
powershell -Command 'Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" | Format-List'
```
Also check:
```powershell
powershell -Command 'Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location | Format-List'
```

### 2b. Running Services (auto-start)
```powershell
powershell -Command 'Get-Service | Where-Object {$_.StartType -eq "Automatic" -and $_.Status -eq "Running"} | Select-Object Name, DisplayName | Format-Table -AutoSize'
```

### 2c. Top Processes by RAM
```powershell
powershell -Command 'Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 30 Name, @{N="RAM_MB";E={[math]::Round($_.WorkingSet64/1MB,1)}}, @{N="CPU_s";E={[math]::Round($_.CPU,1)}} | Format-Table -AutoSize'
```

### 2d. Non-Microsoft Scheduled Tasks
```powershell
powershell -Command 'Get-ScheduledTask | Where-Object {$_.State -eq "Ready" -and $_.TaskPath -notlike "*\Microsoft\*"} | Select-Object TaskName, TaskPath, State | Format-Table -AutoSize'
```

### 2e. Installed Apps (look for known bloat)
```powershell
powershell -Command 'Get-AppxPackage | Select-Object Name, Publisher | Sort-Object Name | Format-Table -AutoSize'
```

## Phase 3: Research and Categorize

### MANDATORY: Web-verify before recommending

Do NOT rely solely on training data to determine whether something is safe to disable. For every item you plan to recommend disabling or removing:

1. **Search the web** for "[item name] safe to disable Windows 11 [current year]" or "[service name] what does it do Windows 11"
2. **Check for recent reports** of issues caused by disabling it (especially after recent Windows updates)
3. **Verify registry key paths** still work on the current Windows version — Microsoft changes these between builds
4. **For HKLM policy keys on Home edition**, search to confirm whether they're enforced or silently ignored

Use the Agent tool with WebSearch/WebFetch to research items in parallel batches. Group related items (e.g., all Dell services, all browser settings) into single research queries for efficiency.

If web search is unavailable, explicitly tell the user: "I could not verify this against current sources — this recommendation is based on training data which may be outdated. Please verify before applying."

### Categorize EVERY finding into one of these buckets:

### Category A: OS Core (DO NOT TOUCH)
Windows shell, DWM, audio, networking, security, RPC, etc. These are load-bearing.

### Category B: Corporate IT / Security (FLAG BUT DO NOT RECOMMEND DISABLING)
Common patterns:
- **Endpoint security:** SentinelOne, CrowdStrike, Carbon Black, Cylance, Sophos, Symantec, McAfee, Webroot, ESET
- **RMM/Management:** SAAZ, ConnectWise/ScreenConnect, Datto, NinjaRMM, Atera, ITSPlatform, Kaseya
- **Vulnerability scanning:** CyberCNS, Qualys, Tenable/Nessus, Rapid7
- **Privilege management:** AutoElevate, CyberArk, BeyondTrust, Thycotic
- **Discovery/Inventory:** Liongard, Lansweeper, PDQ
- **VPN:** StrideLinx, Cisco AnyConnect, GlobalProtect, Zscaler

Tell the user: "These appear to be managed by your IT department. Disabling them will likely get flagged or re-enabled. I'm listing them so you know what's using resources, not recommending removal."

### Category C: Vendor Bloat (SAFE TO REMOVE, present pros/cons)
Common patterns by manufacturer:
- **Dell:** SupportAssist, SmartByte, TechHub, Digital Delivery, Cinema Color, Customer Connect, Mobile Connect, Dell Update
- **HP:** Support Assistant, Audio Switch, JumpStarts, Sure Connect, Wolf Security
- **Lenovo:** Vantage, Hotkeys, Pen Settings, Now, Commercial Vantage
- **Acer:** Quick Access, Care Center, Product Registration
- **Microsoft bundled:** Power Automate Desktop, Phone Link, Clipchamp, Microsoft Teams (personal), News/Widgets, Cortana

For each item present:
- What it does (1 sentence)
- RAM/CPU impact if measurable
- Risk of removing (what breaks?)
- How to reinstall if needed

### Category D: User Apps (INFORM, don't recommend unless asked)
Chrome, Zoom, Slack, Webex, OneDrive, Office, etc. These are user-choice. Note their resource usage but only recommend changes if the user asks or if startup behavior is wasteful (pre-launching, background services).

### Category E: Browser Optimization
Check for and recommend disabling:
- **Edge:** Pre-rendering, startup boost, background mode
- **Chrome:** Auto-launch at startup, background apps
- **Brave/Firefox:** Similar startup/background patterns

Note: Edge policy keys under `HKLM\SOFTWARE\Policies\Microsoft\Edge` work on Home edition (Edge reads them directly). Verify at `edge://policy`.

### Category F: Telemetry / Data Collection (present pros/cons)
- DiagTrack (Connected User Experiences and Telemetry)
- Windows Health and Optimized Experiences (whesvc)
- Bing integration in Windows Search
- Widgets/News and Interests

## Phase 4: Present Recommendations

Format as a clear table for each category with actionable items. Example:

```
VENDOR BLOAT (safe to remove)
| Item | What it does | RAM | Risk | Undo |
|------|-------------|-----|------|------|
| Dell SupportAssist | Auto-diagnostics | 200 MB | Manual driver updates | support.dell.com |
```

Then ask: **"Which of these would you like to disable? Pick by number/name, or say 'all safe' for everything in the safe category."**

## Phase 5: Generate Commands

After user selects items, generate the appropriate commands:
- Registry changes: `reg add` / `reg delete` with full paths
- Service disabling: `Set-Service ... -StartupType Disabled` + `Stop-Service`
- App removal: `Remove-AppxPackage` or `msiexec /X`
- Startup removal: registry deletion or shortcut removal

**Present all commands to the user BEFORE execution.** Group them:
1. Commands for Admin PowerShell (HKLM keys, services)
2. Commands for regular PowerShell (HKCU keys, user startup)

**IMPORTANT:** On Windows 11 Home, warn the user which HKLM policy keys may be silently ignored, and suggest HKCU alternatives where they exist.

## Phase 6: Verify (Before/After Comparison)

After user applies changes and reboots, capture the "after" snapshot using the same metrics as Phase 1:

```powershell
powershell -Command '$os = Get-CimInstance Win32_OperatingSystem; $total = [math]::Round($os.TotalVisibleMemorySize/1MB,1); $free = [math]::Round($os.FreePhysicalMemory/1MB,1); $used = $total - $free; $pct = [math]::Round(($used/$total)*100,1); $procs = (Get-Process).Count; $svcs = (Get-Service | Where-Object {$_.Status -eq "Running"}).Count; Write-Output "=== AFTER CHANGES ==="; Write-Output "Processes:  $procs"; Write-Output "Services:   $svcs running"; Write-Output "RAM total:  $total GB"; Write-Output "RAM used:   $used GB ($pct%)"; Write-Output "RAM free:   $free GB"'

powershell -Command 'Get-CimInstance Win32_Processor | Select-Object @{N="Load_Pct";E={$_.LoadPercentage}} | Format-Table -AutoSize'

powershell -Command 'Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 20 Name, @{N="RAM_MB";E={[math]::Round($_.WorkingSet64/1MB,1)}}, @{N="CPU_s";E={[math]::Round($_.CPU,1)}} | Format-Table -AutoSize'
```

Present a side-by-side comparison using the Phase 1 baseline:

```
                    BEFORE      AFTER       DELTA
Processes:          326         278         -48
Services running:   95          82          -13
RAM used:           10.7 GB     9.3 GB      -1.4 GB freed
RAM free:           1.0 GB      2.4 GB      +1.4 GB
RAM %:              91.5%       79.5%       -12.0%
CPU:                42%         15%         -27%
```

Also show the updated top 20 processes by RAM so the user can see what's still consuming resources and decide if further cleanup is warranted.

## Phase 7: Save Report

After completion, save a cleanup log to the user's Desktop:

```
System Cleanup Log - [COMPUTERNAME] - [DATE]
=============================================
```

Include:
- Before/after metrics comparison table (processes, services, RAM, CPU)
- Everything removed/disabled with the exact commands used
- What's still running and why (corporate IT, user choice, OS core)
- Reapply commands block for after Windows updates
- Date of cleanup (for tracking when updates might reset things)

## Reapply Mode

When invoked with `reapply`:
1. Look for the most recent cleanup log on the Desktop
2. Extract the registry commands from it
3. Check which ones are still applied vs reset by updates
4. Present only the ones that need re-application

## Safety Reminders

- **NEVER** run `pip install`, `npm install`, or install any packages
- **NEVER** disable Windows Update, Windows Defender, or firewall services
- **NEVER** modify boot configuration (bcdedit)
- **NEVER** touch BIOS/UEFI settings
- **NEVER** delete system files or Windows component store
- **NEVER** auto-execute removal commands — always present and wait for approval
- If unsure whether something is safe, **say so and suggest the user research it** or ask their IT department
- When in doubt, **do a web search** to verify safety before recommending
