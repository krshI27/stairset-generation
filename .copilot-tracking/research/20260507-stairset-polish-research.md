<!-- markdownlint-disable-file -->

# Task Research Notes: Stairset Polish Tasks

## Research Executed

### File Analysis

- `stairset.py` lines 735–760
  - Square rail joint filler uses `build_box(s, s, s, rail_pts[i])` where `s = rail_w * 1.4`. Box has perpendicular faces — visible square lump at bends.
  - Round rail joint filler uses `build_uv_sphere(rail_r * 1.05, rail_pts[i])`. Works well.
  - `build_oriented_cylinder(radius, height, center, direction, segments=16)` exists at line 172. Takes a numpy direction vector.

- `stairset.py` lines 172–177
  - `build_oriented_cylinder` wraps `build_cylinder` + `rotation_matrix_from_vectors`. Direction is 3D numpy array.

- `streamlit_app.py` lines 57–89
  - `DEFAULTS` dict is the preset schema. All keys are primitive (float/int/bool/str).
  - `_preset_url()` at line 105 serialises session_state to `?preset=` URL param.
  - `handrail_type` key in DEFAULTS = `"Round"`. Options: Round, Square, Curb (Metal dropped).

### Code Search Results

- `build_oriented_cylinder` — single definition at stairset.py:172, called ~8 times for rail segments and posts.
- `build_box(s, s, s` — only call is the joint filler at stairset.py:752 (cube case).

## Key Discoveries

### Square Rail Joint Cylinder Approach

Replace the cube filler with a bisector-aligned cylinder:

```python
d_prev = np.array(rail_pts[i-1]) - np.array(rail_pts[i])
d_next = np.array(rail_pts[i+1]) - np.array(rail_pts[i])
d_prev /= np.linalg.norm(d_prev)
d_next /= np.linalg.norm(d_next)
bisector = d_prev + d_next
bn = np.linalg.norm(bisector)
if bn < 1e-6:
    bisector = np.array([0.0, 1.0, 0.0])
else:
    bisector /= bn
jv, jf = build_oriented_cylinder(rail_w * 0.6, rail_w * 2.2, tuple(rail_pts[i]), bisector, segments=12)
```

- Radius = rail_w * 0.6 (slightly wider than half-width so it overlaps rail segments)
- Length = rail_w * 2.2 (enough to straddle both adjacent segments' end-caps)
- Oriented along bisector so it blends naturally into both rail directions

### ZV1 Preset Candidates

Good starting param combinations for zine-style prints:
1. **Minimal/architectural**: 12 steps, no landing, Round rail, fisheye=0, perspective
2. **Mid-spiral**: 8+5 split with landing, Square rail, fisheye=0.3, explode=0
3. **Abstract/sculptural**: 6+6+4, Curb rail, fisheye=0.6, fisheye pushes geometry

### ORTHO-LIGHTING

Current state: `ambient` bumped +0.15 in ortho mode (stairset.py or streamlit_app.py — need to verify where). May need second directional fill light.

## Recommended Approach

1. Square joint cylinder: bisector-aligned `build_oriented_cylinder` — single code change.
2. ZV1 presets: create `presets/` dir with 3 JSON files via `_preset_url()` pattern.
3. ORTHO-LIGHTING: check streamlit_app.py for ortho light logic, add second pyvista light.

## Implementation Guidance

- **Objectives**: Fix square rail bend visuals; create printable zine presets; confirm ortho lighting
- **Key Tasks**: Edit stairset.py joint filler block; mkdir presets/; write 3 JSON files; test
- **Dependencies**: pyvista/stpyvista installed; conda env stairset-generation active
- **Success Criteria**: No gap/cube lump at square rail bends; 3 preset JSONs load via ?preset=; ortho view looks good
