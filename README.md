# Figma to Illustrator Editable Text

English · [繁體中文](README.zh.md)

A reusable Skill for diagnosing Figma plugin exports and repairing their import into Adobe Illustrator while preserving editable text and original files.

It covers SVG exports with companion JSX scripts, font metadata, and image folders. This is a diagnosis and repair workflow, not a one-click patch or a guarantee of lossless conversion.

## What it does

- Reads the plugin instructions before choosing an import or repair approach.
- Includes a read-only Python checker for SVG structure, font metadata, image links, text filters, and gradient risks.
- Separates missing fonts, placeholder font names, text filters, image links, and gradient-fill problems.
- Preserves original files and makes repairs in separate copies.
- Requires approval before approximating gradients, removing shadows, or substituting fonts.
- Checks editable text, fonts, images, fills, and artboards.
- Requires successful AI saving and reopening before reporting completion.

## Quick start

### Install for Codex

```bash
git clone https://github.com/Xuanwinnie/figma-to-illustrator-editable-text.git \
  ~/.codex/skills/figma-to-illustrator-editable-text
```

### Install for Claude Code

```bash
git clone https://github.com/Xuanwinnie/figma-to-illustrator-editable-text.git \
  ~/.claude/skills/figma-to-illustrator-editable-text
```

Reload skills or restart the relevant AI tool if needed, then provide the extracted export folder or complete ZIP. Installation does not grant access to Illustrator; the agent also needs suitable local-file and application-control tools.

```text
Use figma-to-illustrator-editable-text to process the Figma plugin export I supplied. Preserve editable text and original files. Ask before approximating gradients, removing shadows, or substituting fonts. Save a new AI file and reopen it to verify the result; report any incomplete steps clearly.
```

You can also use the GitHub-reading prompt below without installing the Skill, provided the agent can access the repository and your files.

## Workflow

### Run the read-only checker

Requires Python 3; no extra packages. From this repository, replace the example paths with your own:

```bash
python3 scripts/inspect_export.py '/path/to/export-folder' \
  --svg 'Page_1_RGB.svg' --output '/path/to/new-report.json'
```

If the folder contains multiple SVGs, `--svg` is required. The checker does not execute JSX, modify designs, download images, or overwrite reports. A completed check is not proof of installed fonts, correct Illustrator rendering, or a saved AI file. See [checker usage and limits](references/diagnostic-tool.md).

### Import and repair

```text
Export folder or ZIP + plugin instructions
        ↓
Inspect SVG, JSX, font metadata, and images
        ↓
Follow the plugin's normal import procedure
        ↓
Identify problems and test repairs on a copy
        ↓
Confirm any visual trade-offs with the user
        ↓
Verify text, fonts, images, fills, and artboards
        ↓
Save a new AI file and reopen it for verification
```

## Copyable prompts

### One-line prompt — no installation required

Provide the folder path or ZIP with this prompt. If the agent cannot read the Skill, it should say so rather than pretend it has loaded it.

```text
First read https://github.com/Xuanwinnie/figma-to-illustrator-editable-text/blob/main/SKILL.md in full and its linked case notes when relevant, then process my supplied Figma plugin export folder. If I have not provided a folder path or ZIP, ask for it instead of guessing. Preserve editable text and original files; ask before approximating gradients, removing shadows, or substituting fonts. Save a new AI file, confirm saving succeeded, and reopen it for verification. Clearly report any step that cannot be completed; do not claim completion prematurely.
```

### Diagnosis only

```text
Use figma-to-illustrator-editable-text to diagnose this export's missing text, changed fonts, missing images, or incorrect colors. Explain the evidence and proposed repairs first; do not modify the files yet.
```

## Core output

When the workflow can be completed, deliver a separately saved and reopened AI file plus a verification summary. Include what was repaired, which text remains editable, known visual differences, and any incomplete steps. Never offer a nonexistent AI file as a completed deliverable.

## Observed problems and improvements

The [case notes](references/observed-failures.md) record placeholder fonts, text-filter failures, image embedding, black gradient text, unreliable imported IDs, blank text frames, repeated-script conflicts, and saving failures.

They distinguish observed fixes from approximations and unfinished verification. The original case restored visible text and images, but did not verify a final saved AI file; native gradients and shadows were not fully restored.

## Repository structure

```text
figma-to-illustrator-editable-text/
├── SKILL.md
├── references/
│   ├── diagnostic-tool.md
│   └── observed-failures.md
├── scripts/
│   └── inspect_export.py
├── tests/
│   └── test_inspect_export.py
├── README.md
└── README.zh.md
```

## Limitations

- Editable text and exact appearance may require a trade-off. Character-by-character colors only approximate a gradient and may need recalculation after edits.
- Removing a text filter can restore visibility while changing the shadow or other effect.
- Compatibility depends on the export, plugin version, fonts, and Illustrator version; case-specific counts are not universal defaults.
- No project-specific patch scripts, artwork, images, or font files are bundled.
- Current automation covers read-only inspection only. General-purpose repair scripts and AI reopening verification are not implemented.

## Tests

```bash
python3 -B -m unittest discover -s tests -v
```

Tests use synthetic data, not private design assets or customer export packages.

## License

No license has been specified for this repository yet. Public availability does not by itself grant redistribution rights. Check permissions separately for third-party plugins, fonts, and design assets.
