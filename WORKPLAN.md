# WORKPLAN — stairset-generation

**Status**: DEPLOYED on Streamlit Cloud (2026-04-25). Migrated viewer Plotly → pyvista (stpyvista 0.1.4) on 2026-05-07.
**Last changes**: stpyvista migration (2026-05-07): VTK rendering, real Phong/ortho lighting, spotlight, server-side PNG/SVG export at print resolution, proper z-buffer (no rail vanishing).

---

## Viewer / UI bugs (backlog)

- [x] **FISH-LENS** done (2026-05-07): mesh subdivision (recursive midpoint, 4ⁿ tris) before fisheye_vertex so straight edges become smooth curves. Subdivision level auto-scales 0/2/3/4 based on fisheye_strength.
- [x] **EXPLODE** done (2026-05-07): per-part offset along (part_centroid − world_centroid), scaled by world bbox max dim. Slider in Viewer section, factor 0–1.
- [ ] **ORTHO-LIGHTING** ~30min: Verify orthographic lighting looks good after lightposition z fix (z=0→z=300). May need a second directional light or higher ambient when in orthographic mode.
- [x] **PNG-CURRENT-CAM** done (2026-05-07): Plotly modebar PNG already captures live camera (client-side toImage). Added elev/azim sliders in Print PNG section so matplotlib `render_png` can match the viewer angle. Defaults 30°/-45° approximate Plotly's home eye (1.5,-1.5,1.2).

## Active priorities (2026-04-25 — Path A: ready, just needs presets + DPI fix)

### Path A: Zine Vol.1 preset rollout

- [x] **ZV1-3** ~1hr: `?preset=` URL loader done (2026-04-25)
- [x] **STR-EXPORT** done (2026-05-07): `render_png` accepts `dpi=` + `paper=` + `orientation=`; A3@300dpi verified at 3507×4962. Sidebar Render PNG button + download_button wired in streamlit_app.py.
- [ ] **ZV1-preset-stair** ~30min: Create 2–3 Zine Vol.1 candidate presets — run render, save params as `presets/zine-vol1-*.json`
- [ ] **STR-2** ~1hr: Evaluate stair renders as Prodigi print product — pick 3–4 strongest outputs at A3 300dpi

### Revenue path (deferred)

- [x] **STR-1**: Deployed to Streamlit Cloud (2026-04-25)
- [ ] **STR-PRODIGI** ~1hr: "Order Print" button → `render_png(dpi=300)` → upload bytes to R2 public bucket → `POST https://api.prodigi.com/v4.0/orders` with `GLOBAL-FAP-16.5X11.7` (A3); `PRODIGI_API_KEY` from `.streamlit/secrets.toml`
- [ ] **CRT-1** ~30min: Add stairset-generation to karoshirt.art `/create` gallery page
- [ ] **EXHIBIT-STR** ~1hr: Embed steganographic watermark in exported PNG — preset ID + timestamp in pixel LSBs (see Exhibition Concept note)

## Completed geometry fixes (2026-05-07)

- [x] Handrail kink at landing transitions — tread-centre keypoints, no landing-start duplicate
- [x] Post density tier system — 0.0 = anchors only, 0.5 = + landing edges, 1.0 = per step
- [x] Curb: slanted parallelogram prism top (hand can glide smoothly), flat landing sections
- [x] Lightposition z=0 → z=300 (top faces now properly lit in both perspective + ortho)
- [x] Camera preservation — camera.eye only on first render; uirevision preserves user angle
- [x] Turntable rotation mode (was orbital — hard to align to axes)
- [x] Removed orientation guide widget (redundant)
- [x] STR-EXPORT: render_png paper/dpi/orientation; A3@300dpi sidebar download
- [x] EXPLODE: per-part outward offset slider
- [x] FISH-LENS: mesh subdivision so fisheye curves straight lines
- [x] PNG-CURRENT-CAM: elev/azim sliders for matplotlib export
- [x] Handrail placement options: Right / Left / Both sides / Both sides + middle / Middle (was: Side / Center)

## stpyvista migration (2026-05-07)

**Why**: Plotly path was hitting limits — broken ortho lighting, camera reset on param change, matplotlib PNG export mismatched viewer (different camera + no z-buffer → middle rail vanishing behind stairs).

**What changed**:
- Viewer: `build_plotly_meshes` → `build_pyvista_plotter` (VTK PolyData per part, Phong shading, key+fill lights). `streamlit_app.py` uses `stpyvista()` instead of `st.plotly_chart()`.
- PNG export: matplotlib `render_png` removed; new `screenshot_png(plotter, window_size)` does server-side off-screen VTK render at exact print res (A3@300dpi → 3507×4962 verified). Same camera/lighting/effects as viewer.
- Vector export: added "Render vector (SVG)" using `Plotter.save_graphic` — clean lines for zine print.
- Lighting controls: added light intensity slider + spotlight checkbox + cone-angle slider. Spotlight uses `pv.Light(positional=True, cone_angle=...)`.
- Deps: `vtk>=9.3` + `pyvista>=0.43` + `stpyvista<0.2` (0.2+ requires Streamlit components v2 not yet supported by Streamlit 1.56).
- Cloud: `pv.start_xvfb()` called on Linux when DISPLAY empty.

**Wins**:
- Ortho lighting works — depth is visible per step (was flat in Plotly ortho).
- Z-buffer correct — middle rail no longer hidden behind stair body.
- Print PNG = exact live view (same VTK pipeline server-side and client-side).
- Real spotlight + freely positioned key light.
- Vector SVG export for zine.

**Trade-offs / open issues**:
- **Camera not preserved across Python reruns**: pyvista builds a fresh plotter on every script run; client-side drags are local to the iframe and don't sync back. (Plotly's `uirevision` did keep dragged eye.) Followup: add JS bridge that captures VTK panel camera state and stores in `st.session_state`.
- **Fisheye is still mesh-distortion**, not viewer post-process. VTK supports custom GLSL shader replacement → feasible but unimplemented.
- Server-side print render takes ~5-10s at A3@300dpi (off-screen VTK render is heavier than matplotlib was).

## Post-migration fixes (2026-05-07)

- [x] **Square rail gap at kinks**: rail segments meet with perpendicular box ends → visible inner-corner gap. Added 1.4×rail_w filler cube at every keypoint (round rails skip — cylindrical caps already meet cleanly).
- [x] **mesh_parts caching**: `@st.cache_data` (max 32 entries) keyed on JSON-serialised `params`. Repeated tweaks to non-geometric params (lighting, viewer mode) reuse cached geometry.
- [x] **Viewer key fix**: stpyvista 0.1.x caches by `key`. Stable key suppressed re-renders. Now keys hash full live config so each unique scene re-mounts → live updates work.
- [x] **Pan / zoom hint**: added caption "Drag = rotate · Shift+drag = pan · scroll = zoom." beneath viewer.

## Open after migration

- [ ] **Camera persistence across reruns**: still resets when params change (component re-mount). Needs JS bridge to capture VTK panel camera and feed into next `plotter.camera_position`. Defer until friction shows.
- [ ] **Render PNG matches dragged camera**: requires camera-bridge above.
- [ ] **Two-finger trackpad pan**: out of scope; Shift+drag accepted as substitute.
- [ ] **Viewer-level fisheye post-process**: would need custom GLSL via VTK shader replacement; current geometric fisheye stays as-is.

## Bug fixes (2026-05-07 round 2)

- [x] **Camera reset on param change**: was sending `camera={"projection":{...}}` only on first render, but Streamlit re-runs on init meant camera spec dropped on second pass. Now always sends home eye every render; uirevision="stairset_camera" preserves user-dragged state. Verified via real mouse drag + number_input change.
- [x] **Fisheye broke geometry**: `apply_fisheye(center=world_c)` passed 3-vec; vectorlab's `fisheye_vertex` reads `c[0],c[1]` as XZ coords (not XY). Now passes `(world_c[0], world_c[2])`.
- [x] **Explode collapsed inward**: `build_box` triangle winding produces inward-pointing normals → offset moved faces toward centroid. Now flips normals where `dot(normal, tri_centroid - part_centroid) < 0`. Cube [-0.5,0.5] → [-1.0,1.0] at factor=1.0 verified.
- [x] **Per-face explode** (was per-part centroid): cubes split into 6 separated squares, each moving along its own face normal. Curved meshes shatter radially.
- [x] **Ortho lighting**: lightposition now scaled to world_centroid + world_scale (consistent across projections); ambient bumped +0.15 in ortho; lighting epsilons tightened to avoid flat-face artifacts.

## Preset loader pattern (Streamlit)

```python
import json
import streamlit as st

_raw = st.query_params.get("preset")
if _raw:
    try:
        _p = json.loads(_raw)
        for k, v in _p.get("params", {}).items():
            st.session_state.setdefault(k, v)
    except (json.JSONDecodeError, KeyError):
        pass
# add key= to every widget matching the DEFAULTS key names
```

`DEFAULTS` dict is the preset schema as-is — just JSON-serialize it.

## Decisions needed

- `render_png` current DPI? Check matplotlib `fig.savefig(buf, dpi=...)` — set to 300 for print
- Preset hosting: start with repo-bundled `presets/` dir; switch to R2 fetch when hosting presets centrally

## Notes

- `fisheye_strength=0` → clean architectural; high → sculptural/abstract — both strong exhibition prints
- True fisheye (curved lines) would require post-process screen-space warp — not trivial in Plotly
- Exploded view idea: offset mesh parts along centroid direction — good for exhibition / assembly diagrams
- See `krshi27-scribe/WORKPLAN.md` for shared `upload_to_r2()` + `create_prodigi_order()` pattern
- Depends on `vectorlab` as editable sibling (`-e ../vectorlab` in environment.yml)

---

## Active priorities (2026-04-25 — Path A: ready, just needs presets + DPI fix)

### Path A: Zine Vol.1 preset rollout

- [x] **ZV1-3** ~1hr: `?preset=` URL loader done (2026-04-25)
- [x] **STR-EXPORT** done (2026-05-07): `render_png` accepts `dpi=` + `paper=` + `orientation=`; A3@300dpi verified at 3507×4962. Sidebar Render PNG button + download_button wired in streamlit_app.py.
- [ ] **ZV1-preset-stair** ~30min: Create 2–3 Zine Vol.1 candidate presets — run render, save params as `presets/zine-vol1-*.json`
- [ ] **STR-2** ~1hr: Evaluate stair renders as Prodigi print product — pick 3–4 strongest outputs at A3 300dpi

### Revenue path (deferred)

- [x] **STR-1**: Deployed to Streamlit Cloud (2026-04-25)
- [ ] **STR-PRODIGI** ~1hr: "Order Print" button → `render_png(dpi=300)` → upload bytes to R2 public bucket → `POST https://api.prodigi.com/v4.0/orders` with `GLOBAL-FAP-16.5X11.7` (A3); `PRODIGI_API_KEY` from `.streamlit/secrets.toml`
- [ ] **CRT-1** ~30min: Add stairset-generation to karoshirt.art `/create` gallery page
- [ ] **EXHIBIT-STR** ~1hr: Embed steganographic watermark in exported PNG — preset ID + timestamp in pixel LSBs (see Exhibition Concept note)

## Preset loader pattern (Streamlit)

```python
import json
import streamlit as st

_raw = st.query_params.get("preset")
if _raw:
    try:
        _p = json.loads(_raw)
        for k, v in _p.get("params", {}).items():
            st.session_state.setdefault(k, v)
    except (json.JSONDecodeError, KeyError):
        pass
# add key= to every widget matching the DEFAULTS key names
```

`DEFAULTS` dict is the preset schema as-is — just JSON-serialize it.

## Decisions needed

- `render_png` current DPI? Check matplotlib `fig.savefig(buf, dpi=...)` — set to 300 for print
- Preset hosting: start with repo-bundled `presets/` dir; switch to R2 fetch when hosting presets centrally

## Notes

- `fisheye_strength=0` → clean architectural; high → sculptural/abstract — both strong exhibition prints
- See `krshi27-scribe/WORKPLAN.md` for shared `upload_to_r2()` + `create_prodigi_order()` pattern
- Depends on `vectorlab` as editable sibling (`-e ../vectorlab` in environment.yml)
