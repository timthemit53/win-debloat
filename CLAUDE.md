# win-debloat

Windows system debloat tool powered by Claude Code.

## Usage

1. Clone this repo: `git clone https://github.com/timthemit53/win-debloat`
2. `cd win-debloat`
3. Run Claude Code and type `/debloat`

## Commands

- `/debloat` or `/debloat scan` — Full system scan with categorized report and recommendations
- `/debloat check` — Quick post-change verification (RAM, CPU, top processes)
- `/debloat reapply` — Regenerate registry commands after Windows updates reset them

## Safety

- All scanning is read-only
- No changes are made without explicit user approval
- Commands are presented for review before execution
- Corporate IT tools are flagged but never recommended for removal
- Windows core services are never touched
