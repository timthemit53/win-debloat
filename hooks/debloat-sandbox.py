"""
debloat-sandbox.py — PreToolUse hook for the win-debloat skill.

Blocks destructive system operations so Claude presents commands
for the user to run manually instead of auto-executing them.

Blocks:
1. Registry writes (reg add, reg delete, reg import, regedit)
2. Service modification (Set-Service, Stop-Service, Remove-Service, sc config/delete/stop)
3. App uninstall (Remove-AppxPackage, msiexec /X, winget uninstall)
4. Recursive/bulk delete (rm -r, rmdir /s, Remove-Item -Recurse)
5. System shutdown/restart
6. Disk/partition commands (diskpart, format, fdisk)

Allows:
- All read-only commands (reg query, Get-Service, Get-Process, Get-AppxPackage, etc.)
- File writes to Desktop (for saving cleanup logs)

Reads JSON from stdin, writes decision JSON to stdout.
"""
import json
import re
import sys

DENY = {
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "",
    }
}


def deny(reason: str) -> None:
    DENY["hookSpecificOutput"]["permissionDecisionReason"] = reason
    json.dump(DENY, sys.stdout)
    sys.exit(0)


def main() -> None:
    data = json.load(sys.stdin)
    cmd = data.get("tool_input", {}).get("command", "")

    # 1. Block registry writes (not reads)
    if re.search(r'\breg\s+(add|delete|import)\b', cmd, re.IGNORECASE) or \
       re.search(r'\bregedit\b', cmd, re.IGNORECASE):
        deny(
            "Blocked: registry modification detected. "
            "The debloat skill generates commands for you to run manually in Admin PowerShell. "
            "Copy the commands from Claude's output and paste them yourself."
        )

    # 2. Block service modification
    service_write_patterns = [
        r'\bSet-Service\b',
        r'\bStop-Service\b',
        r'\bRemove-Service\b',
        r'\bNew-Service\b',
        r'\bsc\s+(config|delete|stop|disable)\b',
    ]
    for pattern in service_write_patterns:
        if re.search(pattern, cmd, re.IGNORECASE):
            deny(
                "Blocked: service modification detected. "
                "Run service commands manually in Admin PowerShell."
            )

    # 3. Block app uninstall
    uninstall_patterns = [
        r'\bRemove-AppxPackage\b',
        r'\bmsiexec\b.*(/[Xx]|/uninstall)',
        r'\bwinget\s+uninstall\b',
        r'\bwmic\s+product\b.*\bcall\s+uninstall\b',
    ]
    for pattern in uninstall_patterns:
        if re.search(pattern, cmd, re.IGNORECASE):
            deny(
                "Blocked: app uninstall detected. "
                "Run uninstall commands manually in Admin PowerShell."
            )

    # 4. Block recursive/bulk delete
    delete_patterns = [
        r'(?<!git )\brm\s+.*-[a-z]*r[a-z]*\b',
        r'\brm\s+--recursive\b',
        r'\bdel\s+/[sq]',
        r'\brmdir\s+/s\b',
        r'\bRemove-Item\b.*-Recurse',
        r'\brd\s+/s\b',
    ]
    for pattern in delete_patterns:
        if re.search(pattern, cmd, re.IGNORECASE):
            deny(
                "Blocked: recursive/bulk delete detected. "
                "Run destructive filesystem operations manually."
            )

    # 5. Block shutdown/restart
    shutdown_patterns = [
        r'\bshutdown\b',
        r'\brestart-computer\b',
        r'\bstop-computer\b',
    ]
    for pattern in shutdown_patterns:
        if re.search(pattern, cmd, re.IGNORECASE):
            deny(
                "Blocked: system shutdown/restart detected. "
                "Restart manually when ready."
            )

    # 6. Block disk/partition/format
    disk_patterns = [
        r'\bformat\s+[A-Za-z]:',
        r'\bdiskpart\b',
        r'\bfdisk\b',
        r'\bmkfs\b',
    ]
    for pattern in disk_patterns:
        if re.search(pattern, cmd, re.IGNORECASE):
            deny(
                "Blocked: disk/partition command detected. "
                "Never run these from Claude Code."
            )

    # Allow everything else (read-only scans, file writes for logs)
    sys.exit(0)


if __name__ == "__main__":
    main()
