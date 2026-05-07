<!-- markdownlint-disable-file -->

# Task Details: Stairset Polish

## Research Reference

**Source Research**: #file:../research/20260507-stairset-polish-research.md

## Phase 1: Square Rail Joint Cylinder

### Task 1.1: Replace cube filler with bisector-aligned cylinder

In `stairset.py` around line 750, the `else` branch of the joint filler block:

```python
else:
    s = rail_w * 1.4
    jv, jf = build_box(s, s, s, tuple(rail_pts[i]))
```

Replace with:

```python
else:
    d_prev = np.array(rail_pts[i - 1]) - np.array(rail_pts[i])
    d_next = np.array(rail_pts[i + 1]) - np.array(rail_pts[i])
    d_prev /= np.linalg.norm(d_prev)
    d_next /= np.linalg.norm(d_next)
    bisector = d_prev + d_next
    bn = np.linalg.norm(bisector)
    bisector = bisector / bn if bn > 1e-6 else np.array([0.0, 1.0, 0.0])
    jv, jf = build_oriented_cylinder(rail_w * 0.6, rail_w * 2.2, tuple(rail_pts[i]), bisector, segments=12)
```

- **Files**: `stairset.py` lines 750–754
- **Success**: No `build_box` call for joint filler in square rail branch
- **Dependencies**: `build_oriented_cylinder` exists at stairset.py:172

### Task 1.2: Smoke test

```bash
source /opt/miniconda3/etc/profile.d/conda.sh && conda activate stairset-generation && python -c "
from stairset import build_stair_mesh_parts
mp = build_stair_mesh_parts(step_count=4, handrail_style='Square')
print('parts:', len(mp))
mp2 = build_stair_mesh_parts(step_count=9, landings=[{'after_step':4,'depth':1.0}], handrail_style='Square')
print('parts with landing:', len(mp2))
"
```

- **Success**: Both print without error, part counts reasonable (>10)

## Phase 2: ZV1 Preset JSON Files

### Task 2.1: Create presets directory and 3 JSON files

```bash
mkdir -p /Users/maximiliansperlich/Developer/projects/stairset-generation/presets
```

**File 1: `presets/zine-vol1-arch.json`** — Minimal architectural

```json
{
  "name": "ZV1 Arch",
  "app": "stairset-generation",
  "params": {
    "step_width": 1.2,
    "step_height": 0.18,
    "step_depth": 0.30,
    "run_pattern": "12",
    "landing_depth": 0.9,
    "bottom_extension": 0.0,
    "top_extension": 0.0,
    "rail_bottom_ext": true,
    "rail_top_ext": true,
    "enable_handrail": true,
    "handrail_type": "Round",
    "rail_placement": "Right",
    "pole_density": 0.5,
    "viewer_mode": "Face colors",
    "projection_type": "perspective",
    "fisheye_strength": 0.0,
    "explode_factor": 0.0,
    "light_x": 4.0,
    "light_y": -8.0,
    "light_z": 12.0,
    "light_intensity": 1.2,
    "spotlight_enabled": false,
    "spotlight_cone_angle": 30.0,
    "ambient": 0.5,
    "diffuse": 0.9,
    "specular": 0.4,
    "roughness": 0.4,
    "edge_width": 2,
    "background_color": "#f0ede8",
    "stair_color": "#d4cfc8",
    "handrail_color": "#2a2a2a"
  }
}
```

**File 2: `presets/zine-vol1-split.json`** — Split run with landing

```json
{
  "name": "ZV1 Split",
  "app": "stairset-generation",
  "params": {
    "step_width": 1.0,
    "step_height": 0.20,
    "step_depth": 0.28,
    "run_pattern": "5 6",
    "landing_depth": 1.2,
    "bottom_extension": 0.2,
    "top_extension": 0.0,
    "rail_bottom_ext": true,
    "rail_top_ext": true,
    "enable_handrail": true,
    "handrail_type": "Square",
    "rail_placement": "Both sides",
    "pole_density": 0.5,
    "viewer_mode": "Face colors",
    "projection_type": "perspective",
    "fisheye_strength": 0.15,
    "explode_factor": 0.0,
    "light_x": 6.0,
    "light_y": -6.0,
    "light_z": 10.0,
    "light_intensity": 1.0,
    "spotlight_enabled": false,
    "spotlight_cone_angle": 30.0,
    "ambient": 0.55,
    "diffuse": 0.85,
    "specular": 0.2,
    "roughness": 0.6,
    "edge_width": 2,
    "background_color": "#1a1a1a",
    "stair_color": "#e8e4de",
    "handrail_color": "#888888"
  }
}
```

**File 3: `presets/zine-vol1-abstract.json`** — Fisheye sculptural

```json
{
  "name": "ZV1 Abstract",
  "app": "stairset-generation",
  "params": {
    "step_width": 0.9,
    "step_height": 0.22,
    "step_depth": 0.26,
    "run_pattern": "4 4 4",
    "landing_depth": 0.8,
    "bottom_extension": 0.0,
    "top_extension": 0.0,
    "rail_bottom_ext": false,
    "rail_top_ext": false,
    "enable_handrail": true,
    "handrail_type": "Curb",
    "rail_placement": "Both sides",
    "pole_density": 0.0,
    "viewer_mode": "Face colors",
    "projection_type": "perspective",
    "fisheye_strength": 0.55,
    "explode_factor": 0.0,
    "light_x": 2.0,
    "light_y": -10.0,
    "light_z": 8.0,
    "light_intensity": 1.3,
    "spotlight_enabled": true,
    "spotlight_cone_angle": 40.0,
    "ambient": 0.4,
    "diffuse": 0.95,
    "specular": 0.6,
    "roughness": 0.3,
    "edge_width": 1,
    "background_color": "#0d0d0d",
    "stair_color": "#c8c8c8",
    "handrail_color": "#c8c8c8"
  }
}
```

- **Files**: `presets/zine-vol1-arch.json`, `presets/zine-vol1-split.json`, `presets/zine-vol1-abstract.json`
- **Success**: Files valid JSON, loadable via `?preset=<url-encoded-content>`

## Phase 3: Verify + WORKPLAN

### Task 3.1: Restart and browser check

```bash
lsof -ti:8501 | xargs -r kill -9 2>/dev/null; sleep 1; source /opt/miniconda3/etc/profile.d/conda.sh && conda activate stairset-generation && nohup streamlit run streamlit_app.py --server.headless true > /tmp/stairset_streamlit.log 2>&1 &
sleep 6 && curl -sf http://localhost:8501/_stcore/health
```

- Confirm health returns `ok`
- Visually check: Square handrail bends show cylinder not box lump
- Confirm Metal absent from handrail type dropdown

### Task 3.2: WORKPLAN update

Mark as `[x]`:
- `Square rail joint cylinder`
- `Verify round rail joints + no Metal in browser`
- `ZV1-preset-stair`

## Dependencies

- conda env `stairset-generation`

## Success Criteria

- Smoke test passes
- 3 preset JSON files exist in `presets/`
- WORKPLAN items marked complete
