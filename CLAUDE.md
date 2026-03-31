# win-debloat

Windows system debloat tool powered by Claude Code.

## First Run Setup

Before running `/debloat`, install the safety hook. This prevents Claude from auto-executing registry edits, service changes, or app removals. It can scan freely but presents commands for you to run manually.

**Step 1:** Copy the hook into your Claude config:
```
mkdir -p ~/.claude/hooks
cp hooks/debloat-sandbox.py ~/.claude/hooks/
```

**Step 2:** Register the hook in `~/.claude/settings.json`. Add this to the `hooks.PreToolUse` array (create the array if it doesn't exist):
```json
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "command": "python hooks/debloat-sandbox.py"
    }
  ]
}
```

Note: Adjust the `command` path to match your Python install. Examples:
- Windows with global Python: `"C:/Python314/python.exe C:/Users/YOURNAME/.claude/hooks/debloat-sandbox.py"`
- Windows with py launcher: `"py C:/Users/YOURNAME/.claude/hooks/debloat-sandbox.py"`
- macOS/Linux: `"python3 ~/.claude/hooks/debloat-sandbox.py"`

If you already have a sandbox hook (e.g., from another project), the debloat hook is additive — it blocks the same categories plus service/app modification. You can use either one.

**Step 3:** Verify by running Claude Code in this directory. It should block `reg add` commands but allow `reg query`.

## Usage

1. Clone this repo: `git clone https://github.com/timthemit53/win-debloat`
2. `cd win-debloat`
3. Complete the First Run Setup above (once per machine)
4. Run Claude Code and type `/debloat`

## Commands

- `/debloat` or `/debloat scan` — Full system scan with categorized report and recommendations
- `/debloat check` — Quick post-change verification (RAM, CPU, top processes)
- `/debloat reapply` — Regenerate registry commands after Windows updates reset them

## Safety

- A PreToolUse hook blocks all destructive operations (registry, services, uninstalls)
- All scanning is read-only — Claude can query but not modify
- Commands are presented for the user to copy/paste into Admin PowerShell
- Corporate IT tools are flagged but never recommended for removal
- Windows core services are never touched
- Windows 11 Home vs Pro differences are detected and accounted for

## What It Scans

- Startup items (registry + startup folder)
- Running services (auto-start)
- Top processes by RAM/CPU
- Non-Microsoft scheduled tasks
- Installed UWP/Store apps
- Browser startup and pre-rendering settings
- Telemetry and data collection services
