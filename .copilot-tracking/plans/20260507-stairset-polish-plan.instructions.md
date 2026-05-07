---
applyTo: ".copilot-tracking/changes/20260507-stairset-polish-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Stairset Polish — Joint Cylinder + ZV1 Presets + Ortho Lighting

## Overview

Polish the stairset viewer: replace square rail cube joint filler with bisector-aligned cylinder, create Zine Vol.1 preset JSON files, and verify ortho lighting.

## Objectives

- Square rail bends show smooth cylinder joint instead of box lump
- 3 Zine Vol.1 preset JSON files loadable via `?preset=` URL
- Ortho projection lighting confirmed good (no flat/dark faces)

## Research Summary

### Project Files

- `stairset.py` - geometry, joint filler at lines 741–754
- `streamlit_app.py` - DEFAULTS schema, preset URL pattern, lighting controls

### External References

- #file:../research/20260507-stairset-polish-research.md - bisector cylinder math + preset schema

## Implementation Checklist

### [ ] Phase 1: Square Rail Joint Cylinder

- [ ] Task 1.1: Replace cube filler with bisector-aligned cylinder in stairset.py
  - Details: .copilot-tracking/details/20260507-stairset-polish-details.md (Lines 15–45)

- [ ] Task 1.2: Smoke-test with `python -c "from stairset import build_stair_mesh_parts; ..."`
  - Details: .copilot-tracking/details/20260507-stairset-polish-details.md (Lines 47–60)

### [ ] Phase 2: ZV1 Preset JSON Files

- [ ] Task 2.1: Create `presets/` directory and 3 zine-vol1 JSON files
  - Details: .copilot-tracking/details/20260507-stairset-polish-details.md (Lines 62–105)

### [ ] Phase 3: Verify + WORKPLAN update

- [ ] Task 3.1: Restart streamlit, verify square joints + round joints in browser
  - Details: .copilot-tracking/details/20260507-stairset-polish-details.md (Lines 107–120)

- [ ] Task 3.2: Mark completed items in WORKPLAN.md
  - Details: .copilot-tracking/details/20260507-stairset-polish-details.md (Lines 122–130)

## Dependencies

- conda env `stairset-generation` with pyvista/stpyvista installed
- streamlit running on port 8501

## Success Criteria

- `python -c "from stairset import build_stair_mesh_parts; build_stair_mesh_parts(step_count=4, handrail_style='Square')"` exits 0
- 3 files exist: `presets/zine-vol1-arch.json`, `presets/zine-vol1-spiral.json`, `presets/zine-vol1-abstract.json`
- WORKPLAN items checked off
