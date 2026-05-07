import json
import os
import sys
import urllib.parse

import streamlit as st

# pyvista needs xvfb on headless Linux (Streamlit Cloud); harmless on macOS/Win.
import pyvista as pv

if sys.platform.startswith("linux") and os.environ.get("DISPLAY", "") == "":
    try:
        pv.start_xvfb()
    except Exception:
        pass

from stpyvista import stpyvista

from stairset import (
    PAPER_SIZES_INCHES,
    build_pyvista_plotter,
    build_stair_mesh_parts,
    export_json,
    export_obj,
    screenshot_png,
)


@st.cache_data(show_spinner=False, max_entries=32)
def _cached_mesh_parts(params_json: str):
    """Mesh-part lists are expensive to recompute and depend purely on geometric
    params. Cache by JSON-serialised params; falls through to a fresh build on
    miss. Returned dict is treated read-only by all callers."""
    return build_stair_mesh_parts(**json.loads(params_json))

st.set_page_config(
    page_title="Stairset Generator",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """<style>
    .main .block-container { padding-top: 0 !important; padding-bottom: 0 !important; }
    /* stpyvista wraps the panel canvas in an iframe; let it fill the viewport */
    iframe[title="stpyvista.simple"], iframe[title="stpyvista"] {
        height: calc(100vh - 52px) !important; width: 100% !important; min-height: 400px;
    }
    [data-testid="stHtmlIframe"] iframe { width: 100% !important; }
    header[data-testid="stHeader"] { height: 2.5rem !important; min-height: 2.5rem !important; }
    .sidebar-title { font-size: 1.1rem; font-weight: 700; color: #262730; margin-bottom: 0.1rem; }
    .sidebar-subtitle { font-size: 0.75rem; color: #6c7280; margin-bottom: 0.75rem; }
    </style>""",
    unsafe_allow_html=True,
)

DEFAULTS = {
    "step_width": 1.0,
    "step_height": 0.18,
    "step_depth": 0.28,
    "run_pattern": "8",
    "landing_depth": 0.9,
    "bottom_extension": 0.0,
    "top_extension": 0.0,
    "rail_bottom_ext": True,
    "rail_top_ext": True,
    "enable_handrail": True,
    "handrail_type": "Round",
    "rail_placement": "Right",
    "pole_density": 0.3,
    "viewer_mode": "Face colors",
    "projection_type": "perspective",
    "fisheye_strength": 0.0,
    "camera_azimuth": -45.0,
    "camera_elevation": 30.0,
    "camera_zoom": 1.0,
    "light_x": 4.0,
    "light_y": -8.0,
    "light_z": 12.0,
    "light_intensity": 1.0,
    "spotlight_enabled": False,
    "spotlight_cone_angle": 30.0,
    "ambient": 0.6,
    "diffuse": 0.8,
    "specular": 0.3,
    "roughness": 0.5,
    "edge_width": 2,
    "background_color": "#808080",
    "stair_color": "#cccccc",
    "handrail_color": "#404040",
}

def _load_preset() -> None:
    preset_raw = st.query_params.get("preset")
    if not preset_raw:
        return
    preset_text = preset_raw[0] if isinstance(preset_raw, list) else preset_raw
    try:
        preset = json.loads(preset_text)
        for key, value in preset.get("params", {}).items():
            if key in DEFAULTS:
                st.session_state.setdefault(key, value)
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass


def _preset_url() -> str:
    params = {key: st.session_state.get(key, default) for key, default in DEFAULTS.items()}
    payload = {"name": "Stairset preset", "app": "stairset-generation", "params": params}
    return f"?preset={urllib.parse.quote(json.dumps(payload, separators=(',', ':')))}"


def _parse_run_pattern(pattern: str, depth: float):
    """Parse a step / run pattern into (total_step_count, landings_list).

    '8'       → (8, [])          single integer = step count, no landings
    '3 5'     → (8, [{after 3}]) two runs with one landing between
    '4 4 4'   → (12, [{…},{…}])  three runs, two landings
    empty/bad → (None, None)
    """
    pattern = pattern.strip()
    if not pattern:
        return None, None
    try:
        parts = [int(p) for p in pattern.split()]
    except ValueError:
        return None, None
    if any(p < 1 for p in parts):
        return None, None
    if len(parts) == 1:
        return parts[0], []
    total = sum(parts)
    result = []
    cumulative = 0
    for run in parts[:-1]:
        cumulative += run
        result.append({"after_step": cumulative, "depth": float(depth)})
    return total, result


_load_preset()

for key, default_value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default_value

with st.sidebar:
    st.markdown('<p class="sidebar-title">Stairset Generator</p>', unsafe_allow_html=True)
    st.markdown('<p class="sidebar-subtitle">Procedural stair model designer</p>', unsafe_allow_html=True)
    if st.button("↺ Reset to defaults", use_container_width=True):
        for key, default_value in DEFAULTS.items():
            st.session_state[key] = default_value
        st.rerun()

    st.subheader("Steps")
    run_pattern = st.text_input(
        "Step / run pattern",
        placeholder="8   or   3 5   or   4 4 4",
        help="Single number = step count.  Multiple numbers = step runs separated by flat landings (e.g. `3 5` = 3 steps, landing, 5 steps).",
        key="run_pattern",
    )
    col_w, col_h, col_d = st.columns(3)
    step_width = col_w.number_input(
        "Width", min_value=0.2, max_value=5.0, step=0.05, key="step_width",
        help="Step width in metres",
    )
    step_height = col_h.number_input(
        "Height", min_value=0.05, max_value=0.4, step=0.01, key="step_height",
        help="Riser height in metres",
    )
    step_depth = col_d.number_input(
        "Depth", min_value=0.1, max_value=1.5, step=0.01, key="step_depth",
        help="Tread depth in metres",
    )
    # Pre-parse to decide whether to show landing depth widget
    _pre_count, _pre_landings = _parse_run_pattern(
        run_pattern, st.session_state.get("landing_depth", DEFAULTS["landing_depth"])
    )
    if _pre_landings:
        landing_depth = st.number_input(
            "Landing depth (m)", min_value=0.3, max_value=5.0, step=0.05, key="landing_depth"
        )
        _parsed_count, landings = _parse_run_pattern(run_pattern, landing_depth)
        _run_parts = run_pattern.split()
        st.caption("  →  ".join(_run_parts) + f"  ·  {_parsed_count} steps total")
    else:
        landing_depth = st.session_state.get("landing_depth", DEFAULTS["landing_depth"])
        _parsed_count, landings = _pre_count, (_pre_landings if _pre_landings is not None else [])
    if _parsed_count is not None:
        step_count = _parsed_count
    else:
        step_count = 8
        landings = []
        if run_pattern.strip():
            st.warning("Invalid — enter e.g. `8` or `3 5`")

    with st.expander("Extensions", expanded=False):
        bottom_extension = st.number_input(
            "Bottom (m)", min_value=0.0, max_value=3.0, step=0.05, key="bottom_extension",
            help="Flat platform added before step 1",
        )
        rail_bottom_ext = st.checkbox(
            "Rail follows bottom extension",
            key="rail_bottom_ext",
            help="When unchecked the handrail stops at the first step nosing.",
        )
        top_extension = st.number_input(
            "Top (m)", min_value=0.0, max_value=3.0, step=0.05, key="top_extension",
            help="Flat platform added after the last step",
        )
        rail_top_ext = st.checkbox(
            "Rail follows top extension",
            key="rail_top_ext",
            help="When unchecked the handrail stops at the last step nosing.",
        )

    st.subheader("Handrail")
    enable_handrail = st.checkbox("Enable handrail", key="enable_handrail")
    if enable_handrail:
        handrail_type = st.selectbox(
            "Type",
            options=["Round", "Square", "Curb"],
            key="handrail_type",
            help="Round/Square = metal handrail. Curb = concrete/stone ledge.",
        )
        rail_placement = st.selectbox(
            "Placement",
            options=["Right", "Left", "Both sides", "Both sides + middle", "Middle"],
            key="rail_placement",
            help="Where to place handrails along the step width.",
        )
        if handrail_type != "Curb":
            pole_density = st.slider(
                "Post density", min_value=0.0, max_value=1.0, step=0.05,
                key="pole_density",
                help="0 = anchors only (first & last step of each run + landing edges).  "
                     "0.5 = bisect runs progressively.  1 = one post per step.",
            )
        else:
            pole_density = st.session_state["pole_density"]
    else:
        handrail_type = st.session_state["handrail_type"]
        rail_placement = st.session_state["rail_placement"]
        pole_density = st.session_state["pole_density"]

    st.subheader("Colors")
    col_bg, col_st, col_hr = st.columns(3)
    background_color = col_bg.color_picker("BG", key="background_color")
    stair_color = col_st.color_picker("Stairs", key="stair_color")
    handrail_color = col_hr.color_picker("Rail", key="handrail_color")

    st.subheader("Viewer")
    viewer_mode = st.radio(
        "Render mode",
        options=["Face colors", "Wireframe", "Faces + edges"],
        key="viewer_mode",
    )
    if viewer_mode == "Faces + edges":
        edge_width = st.slider("Edge width", min_value=1, max_value=8, key="edge_width")
    else:
        edge_width = st.session_state["edge_width"]
    projection_type = st.selectbox(
        "Projection",
        options=["perspective", "orthographic"],
        key="projection_type",
    )
    fisheye_strength = st.slider(
        "Fisheye distortion", min_value=0.0, max_value=1.0, step=0.05, key="fisheye_strength",
        help="0 = off. Barrel distortion that curves straight lines (mesh subdivided to keep curves smooth).",
    )
    st.caption("Camera angle (also controls export view)")
    col_ca, col_ce = st.columns(2)
    camera_azimuth = col_ca.number_input(
        "Azimuth°", min_value=-180.0, max_value=180.0, step=5.0, key="camera_azimuth",
        help="Horizontal rotation around model (0° = +X axis, 90° = +Y, 270°/−90° = −Y).",
    )
    camera_elevation = col_ce.number_input(
        "Elevation°", min_value=1.0, max_value=89.0, step=5.0, key="camera_elevation",
        help="Tilt above the horizon (30° = default, 89° = near top-down).",
    )
    camera_zoom = st.slider(
        "Zoom", min_value=0.4, max_value=3.0, step=0.05, key="camera_zoom",
        help="1.0 = default distance. Lower = zoom in, higher = zoom out.",
    )

    with st.expander("Lighting", expanded=False):
        ambient = st.slider(
            "Ambient", min_value=0.0, max_value=1.0, step=0.05, key="ambient",
            help="Baseline light on all surfaces.",
        )
        diffuse = st.slider(
            "Diffuse", min_value=0.0, max_value=1.0, step=0.05, key="diffuse",
            help="Directional light contribution.",
        )
        specular = st.slider(
            "Specular", min_value=0.0, max_value=1.0, step=0.05, key="specular",
            help="Shininess highlight intensity.",
        )
        roughness = st.slider(
            "Roughness", min_value=0.0, max_value=1.0, step=0.05, key="roughness",
            help="Surface roughness — higher = more matte.",
        )
        st.caption("Key light position (relative to model centroid, in world_scale units)")
        col_lx, col_ly, col_lz = st.columns(3)
        light_x = col_lx.number_input("X", min_value=-30.0, max_value=30.0, step=0.5, key="light_x")
        light_y = col_ly.number_input("Y", min_value=-30.0, max_value=30.0, step=0.5, key="light_y")
        light_z = col_lz.number_input("Z", min_value=-30.0, max_value=30.0, step=0.5, key="light_z")
        light_intensity = st.slider(
            "Light intensity", min_value=0.0, max_value=2.0, step=0.05, key="light_intensity",
        )
        spotlight_enabled = st.checkbox(
            "Spotlight (cone)", key="spotlight_enabled",
            help="Convert key light into a positional spotlight aimed at the model centroid.",
        )
        if spotlight_enabled:
            spotlight_cone_angle = st.slider(
                "Cone angle°", min_value=5.0, max_value=80.0, step=1.0, key="spotlight_cone_angle",
            )
        else:
            spotlight_cone_angle = st.session_state["spotlight_cone_angle"]

RAIL_PLACEMENT_UI_MAP = {
    "Right": "right",
    "Left": "left",
    "Both sides": "both",
    "Both sides + middle": "both+center",
    "Middle": "center",
    # Legacy preset values
    "Side": "right",
    "Center": "center",
}

params = {
    "step_count": step_count,
    "step_width": step_width,
    "step_height": step_height,
    "step_depth": step_depth,
    "bottom_extension": bottom_extension,
    "top_extension": top_extension,
    "rail_bottom_ext": rail_bottom_ext,
    "rail_top_ext": rail_top_ext,
    "enable_handrail": enable_handrail,
    "handrail_style": handrail_type,
    "rail_placement": RAIL_PLACEMENT_UI_MAP.get(rail_placement, "right"),
    "pole_density": pole_density,
    "stair_color": stair_color,
    "handrail_color": handrail_color,
    "landings": landings,
}

viewer_mode_map = {
    "Face colors": "faces",
    "Wireframe": "wireframe",
    "Faces + edges": "faces+edges",
}

mesh_parts = _cached_mesh_parts(json.dumps(params, sort_keys=True, default=str))


def _build_plotter(off_screen: bool, window_size):
    return build_pyvista_plotter(
        mesh_parts,
        window_size=window_size,
        background_color=background_color,
        viewer_mode=viewer_mode_map[viewer_mode],
        edge_width=edge_width,
        ambient=ambient,
        diffuse=diffuse,
        specular=specular,
        specular_power=max(1.0, (1.0 - roughness) * 100.0),
        fisheye_strength=fisheye_strength,
        projection_type=projection_type,
        camera_azimuth=camera_azimuth,
        camera_elevation=camera_elevation,
        camera_zoom=camera_zoom,
        light_position=(light_x, light_y, light_z),
        light_intensity=light_intensity,
        spotlight_enabled=spotlight_enabled,
        spotlight_cone_angle=spotlight_cone_angle,
        off_screen=off_screen,
    )


plotter = _build_plotter(off_screen=True, window_size=(1000, 800))

# stpyvista 0.1.x caches by `key`: a stable key prevents re-rendering on
# parameter changes. Hash the full live config so each unique scene gets its
# own component instance. (Trade-off: client-side camera drags don't survive
# parameter changes — see WORKPLAN open issues.)
import hashlib as _hashlib
_viewer_key = "stairset_pv_" + _hashlib.md5(
    json.dumps(
        {
            **params,
            "viewer_mode": viewer_mode,
            "projection_type": projection_type,
            "fisheye_strength": fisheye_strength,
            "camera_azimuth": camera_azimuth,
            "camera_elevation": camera_elevation,
            "camera_zoom": camera_zoom,
            "ambient": ambient,
            "diffuse": diffuse,
            "specular": specular,
            "roughness": roughness,
            "edge_width": edge_width,
            "background_color": background_color,
            "light_x": light_x,
            "light_y": light_y,
            "light_z": light_z,
            "light_intensity": light_intensity,
            "spotlight_enabled": spotlight_enabled,
            "spotlight_cone_angle": spotlight_cone_angle,
        },
        sort_keys=True,
        default=str,
    ).encode()
).hexdigest()[:12]

stpyvista(
    plotter,
    use_container_width=True,
    panel_kwargs={"orientation_widget": False},
    key=_viewer_key,
)
st.caption(
    "Drag = rotate · Shift+drag = pan · scroll = zoom. "
    "Live drags don't survive parameter changes (pyvista re-renders the scene)."
)

obj_bytes = export_obj(mesh_parts).encode("utf-8")
json_bytes = export_json(params).encode("utf-8")

with st.sidebar:
    with st.expander("Export & Share", expanded=False):
        col_e1, col_e2 = st.columns(2)
        col_e1.download_button(
            "OBJ", obj_bytes, file_name="stairset.obj", mime="text/plain",
            use_container_width=True,
        )
        col_e2.download_button(
            "JSON", json_bytes, file_name="stairset-config.json", mime="application/json",
            use_container_width=True,
        )

        st.markdown("**Print render** (server-side, off-screen VTK render at print resolution).")
        col_p1, col_p2 = st.columns(2)
        png_paper = col_p1.selectbox(
            "Paper", options=list(PAPER_SIZES_INCHES.keys()), index=0, key="png_paper",
        )
        png_orientation = col_p2.selectbox(
            "Orient", options=["portrait", "landscape"], key="png_orientation",
        )
        png_dpi = st.select_slider(
            "DPI", options=[72, 150, 300, 600], value=300, key="png_dpi",
        )
        _w_in, _h_in = PAPER_SIZES_INCHES[png_paper]
        if png_orientation == "landscape":
            _w_in, _h_in = _h_in, _w_in
        _png_w = int(_w_in * png_dpi)
        _png_h = int(_h_in * png_dpi)
        st.caption(f"{_png_w} × {_png_h} px · uses the same camera/lighting/effects as the viewer.")

        if st.button("Render PNG", use_container_width=True, key="render_png_btn"):
            with st.spinner("Rendering…"):
                _off_plotter = _build_plotter(off_screen=True, window_size=(_png_w, _png_h))
                st.session_state["png_bytes"] = screenshot_png(
                    _off_plotter, window_size=(_png_w, _png_h)
                )
                _off_plotter.close()
        if st.session_state.get("png_bytes"):
            st.download_button(
                "Download PNG",
                st.session_state["png_bytes"],
                file_name=f"stairset-{png_paper}-{png_dpi}dpi.png",
                mime="image/png",
                use_container_width=True,
            )

        if st.button("Render vector (SVG)", use_container_width=True, key="render_svg_btn"):
            with st.spinner("Rendering vector…"):
                import tempfile
                _vec_plotter = _build_plotter(off_screen=True, window_size=(_png_w, _png_h))
                with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as _f:
                    _vec_plotter.save_graphic(_f.name)
                    _f.flush()
                    with open(_f.name, "rb") as _r:
                        st.session_state["svg_bytes"] = _r.read()
                os.unlink(_f.name)
                _vec_plotter.close()
        if st.session_state.get("svg_bytes"):
            st.download_button(
                "Download SVG",
                st.session_state["svg_bytes"],
                file_name=f"stairset-{png_paper}.svg",
                mime="image/svg+xml",
                use_container_width=True,
            )

        st.caption("Preset URL (copy to share):")
        st.code(_preset_url(), language=None)
