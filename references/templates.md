# Templates

## Pack layout

```
$R/
├── pack.json            # app, edition, components, phase (written by pack.py)
├── intake.md            # the RESEARCH INTAKE block as approved
├── sources.jsonl        # one row per source looked at (pack.py source)
├── evidence.jsonl       # one row per fact (pack.py evidence)
├── gaps.jsonl           # logged gaps with why and next action (pack.py gap)
├── coverage.md          # generated: per component, per kind, per checklist row
├── gaps.md              # generated, then you add the next action per gap
├── components/<id>/explored.md
└── media/
    ├── raw/             # gitignored: original downloads, PDFs, frames
    └── masked/          # safe copies referenced by evidence
```

## Commands

```
pack.py init --app A --edition E [--root DIR] [--components "S01:Timecards" ...]
pack.py add-component <id> "<name>" [--checklist "row" ...]
pack.py source --url U --title T --tier 1-4 --type help|guide|pdf|video|api|forum|customer|course|release-notes|other \
               --edition match|mismatch|unverified --status used|rejected|unreachable --reason "..." [--components S01,S02]
pack.py evidence --component S01 --kind field --fact "Field 'Pay Rule' (dropdown) on Employee > Timekeeping" \
               --src src-007 --loc "p.14" [--media media/masked/x.png] [--conflicts ev-012] [--checklist "row"]
pack.py gap --component S01 --gap "..." --why "..." --next "..."   # gaps beyond the checklist, and next actions for checklist gaps
pack.py mask <raw image> [--box x,y,w,h ...]    # writes media/masked/<name>; needs Pillow, else copies + warns
pack.py phase intake|map|hunt|extract|write|done   # set at the start of each SKILL.md step, so resume knows where you were
pack.py status | coverage | validate
```

Ids are assigned for you: `src-001`, `ev-0001`. In docs, cite them as `[src:src-007 p.14]`
or `[src:src-007@03:12]`.

## explored.md

```markdown
# <id> <Component name>

Edition: <edition>. Requirement: <one line from the intake>.

## Navigation
- <Menu > Path > Screen> [src:src-003 §Navigating]

## Screens
### <Screen name, exactly as the UI writes it>
- Regions: <header / filter bar / grid / side panel ...> [src:...]
- Controls: <label> (<type>, <enabled/disabled>, opens <x>) [src:...]
- Fields: <label> (<type>, required?, format/shape, default) [src:...]
- Table: columns <...>; sort <...>; filters <...>; paging <...> [src:...]
- States: empty / loading / error / read-only / <custom> [src:...]
- Screenshot: media/masked/<file> [src:...]

## Workflows
1. <step> [src:...@mm:ss]

## Rules and validation
- <rule, message text verbatim> [src:...]

## Roles and permissions
- <who sees / edits what> [src:...]

## API
- `METHOD /path`: fields <...> [src:...]

## Conflicts resolved
- <label A (src-x, 2023)> vs <label B (src-y, 2025)>: B wins (newer, tier 1)

## Gaps
- <what is missing>: <why> → next: <action>
```

## Gap entry (gaps.md)

```
| Component | Gap | Why | Next action |
| S13 | State W-4 form fields | only federal form shown in any source | search "<state> withholding" "<App>" site:.edu; or record it |
```
