import json
import os
import sys
import urllib.parse

import streamlit as st
from streamlit_js_eval import streamlit_js_eval

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


_CAM_CAPTURE_JS = (
    "(() => { try {"
    "  const outer = window.parent.document.querySelector('iframe[title^=\"stpyvista\"]');"
    "  if (!outer) return {error:'no outer'};"
    "  const inner = outer.contentDocument && outer.contentDocument.getElementById('stpyvistaframe');"
    "  if (!inner) return {error:'no inner'};"
    "  const win = inner.contentWindow;"
    "  if (!win || !win.Bokeh) return {error:'no Bokeh'};"
    "  for (const d of win.Bokeh.documents) {"
    "    const all = d._all_models;"
    "    for (const [id, m] of (all.entries ? all.entries() : Object.entries(all))) {"
    "      if (m && m.camera && m.camera.position) {"
    "        const c = m.camera;"
    "        return {position: c.position, focal_point: c.focalPoint, up: c.viewUp, parallel_scale: c.parallelScale};"
    "      }"
    "    }"
    "  }"
    "  return {error:'no camera model'};"
    "} catch(e) { return {error: String(e)}; } })()"
)

st.set_page_config(
    page_title="Stairset Generator",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """<style>
    .stApp { background-color: #E7DED2 !important; color: #30360F !important; }
    header[data-testid="stHeader"] { background-color: #E7DED2 !important; height: 2.5rem !important; min-height: 2.5rem !important; }
    section[data-testid="stSidebar"] { background-color: #DDD3C5 !important; padding-top: 16px !important; }
    [data-testid="stSidebar"] h3 {
        color: #CB411B !important; font-size: 18px !important; font-weight: 600 !important;
        letter-spacing: 0.5px !important; padding-bottom: 8px !important;
        border-bottom: 2px solid rgba(203,65,27,0.3) !important;
        margin-top: 24px !important; margin-bottom: 12px !important;
    }
    [data-testid="stSidebar"] hr { border-color: rgba(203,65,27,0.4) !important; }
    .stButton > button {
        background: linear-gradient(135deg, #CB411B 0%, #945029 100%) !important;
        color: white !important; border: none !important; border-radius: 6px !important;
        box-shadow: 0 2px 4px rgba(203,65,27,0.3) !important; transition: all 0.2s ease !important;
    }
    .stButton > button:hover { transform: translateY(-2px) !important; box-shadow: 0 4px 8px rgba(203,65,27,0.4) !important; }
    [data-testid="stToggle"] input:checked + div { background-color: #CB411B !important; }
    .stCaption, [data-testid="stCaptionContainer"] { color: #945029 !important; }
    a { color: #945029 !important; }
    button:focus-visible { outline: 2px solid #CB411B !important; outline-offset: 2px !important; }
    [data-testid="stSpinner"] { color: #CB411B !important; }
    footer { display: none !important; }
    .main .block-container { padding-top: 0 !important; padding-bottom: 0 !important; }
    iframe[title="stpyvista.simple"], iframe[title="stpyvista"] {
        height: calc(100vh - 52px) !important; width: 100% !important; min-height: 400px;
    }
    [data-testid="stHtmlIframe"] iframe { width: 100% !important; }
    .sidebar-title { font-size: 1.1rem; font-weight: 700; color: #30360F; margin-bottom: 0.1rem; }
    .sidebar-subtitle { font-size: 0.75rem; color: #945029; margin-bottom: 0.75rem; }
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
    step_width = col_w.number_input("Width m", 0.2, 5.0, step=0.05, key="step_width")
    step_height = col_h.number_input("Riser m", 0.05, 0.4, step=0.01, key="step_height")
    step_depth = col_d.number_input("Tread m", 0.1, 1.5, step=0.01, key="step_depth")
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
        st.caption("Flat platform added before step 1 / after last step.")
        bottom_extension = st.number_input(
            "Bottom m", 0.0, 3.0, step=0.05, key="bottom_extension",
        )
        rail_bottom_ext = st.checkbox("Rail follows bottom", key="rail_bottom_ext")
        top_extension = st.number_input(
            "Top m", 0.0, 3.0, step=0.05, key="top_extension",
        )
        rail_top_ext = st.checkbox("Rail follows top", key="rail_top_ext")

    st.subheader("Handrail")
    enable_handrail = st.checkbox("Enable handrail", key="enable_handrail")
    if enable_handrail:
        handrail_type = st.selectbox(
            "Type", ["Round", "Square", "Curb"], key="handrail_type",
            help="Round/Square = metal rail. Curb = concrete/stone ledge.",
        )
        rail_placement = st.selectbox(
            "Placement",
            ["Right", "Left", "Both sides", "Both sides + middle", "Middle"],
            key="rail_placement",
        )
        if handrail_type != "Curb":
            pole_density = st.slider(
                "Post density", 0.0, 1.0, step=0.05, key="pole_density",
                help="0 = anchors only · 0.5 = bisect runs · 1 = one post per step.",
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

    st.caption("Drag/zoom the viewer to set the camera. Pin to lock for PNG/SVG export.")
    _has_captured = bool(st.session_state.get("captured_camera"))
    if _has_captured:
        if st.button("📌 Pinned · clear", use_container_width=True,
                     help="Drop pinned camera; export uses live viewer angle again."):
            st.session_state.pop("captured_camera", None)
            st.session_state["_capture_pending"] = False
            st.rerun()
    else:
        if st.button("📌 Pin viewer camera", use_container_width=True,
                     help="Capture the live drag/zoom state and reuse it for the next render + PNG/SVG export."):
            st.session_state["_capture_nonce"] = st.session_state.get("_capture_nonce", 0) + 1
            st.session_state["_capture_pending"] = True

    if st.session_state.get("_capture_pending"):
        cam = streamlit_js_eval(
            js_expressions=_CAM_CAPTURE_JS,
            key=f"cam_capture_{st.session_state['_capture_nonce']}",
        )
        if cam is not None:
            st.session_state["_capture_pending"] = False
            if isinstance(cam, dict) and "position" in cam:
                st.session_state["captured_camera"] = cam
                st.rerun()
            else:
                st.warning(f"Capture failed: {cam}")

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
    cap = st.session_state.get("captured_camera")
    cam_pos = None
    if cap and "position" in cap:
        cam_pos = [tuple(cap["position"]), tuple(cap["focal_point"]), tuple(cap["up"])]
    return build_pyvista_plotter(
        mesh_parts,
        window_size=window_size,
        background_color=background_color,
        viewer_mode=viewer_mode_map[viewer_mode],
        edge_width=edge_width,
        camera_position=cam_pos,
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
            "edge_width": edge_width,
            "background_color": background_color,
            "captured_camera": st.session_state.get("captured_camera"),
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
    "Drag = rotate · Shift+drag = pan · scroll = zoom · "
    "Pin viewer camera to keep the live angle across param changes."
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

        st.markdown("**Print render**")
        col_p1, col_p2 = st.columns(2)
        png_paper = col_p1.selectbox("Paper", list(PAPER_SIZES_INCHES.keys()), index=0, key="png_paper")
        png_orientation = col_p2.selectbox("Orient", ["portrait", "landscape"], key="png_orientation")
        png_dpi = st.select_slider("DPI", options=[72, 150, 300, 600], value=300, key="png_dpi")
        _w_in, _h_in = PAPER_SIZES_INCHES[png_paper]
        if png_orientation == "landscape":
            _w_in, _h_in = _h_in, _w_in
        _png_w = int(_w_in * png_dpi)
        _png_h = int(_h_in * png_dpi)
        st.caption(f"{_png_w} × {_png_h} px · matches viewer camera/lighting.")

        if st.button("Render PNG", use_container_width=True, key="render_png_btn"):
            with st.spinner("Rendering…"):
                _off_plotter = _build_plotter(off_screen=True, window_size=(_png_w, _png_h))
                import datetime as _dt
                _payload = json.dumps(
                    {
                        "app": "stairset-generation",
                        "ts": _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
                        "preset": params,
                    },
                    sort_keys=True,
                    default=str,
                    separators=(",", ":"),
                ).encode("utf-8")
                st.session_state["png_bytes"] = screenshot_png(
                    _off_plotter, window_size=(_png_w, _png_h), payload=_payload,
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

        st.caption("Preset URL")
        st.code(_preset_url(), language=None)
