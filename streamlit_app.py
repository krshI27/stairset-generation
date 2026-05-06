import json
import urllib.parse

import plotly.graph_objects as go
import streamlit as st

from stairset import (
    build_plotly_meshes,
    build_stair_mesh_parts,
    export_json,
    export_obj,
)

st.set_page_config(
    page_title="Stairset Generator",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """<style>
    /* Remove all top padding so the 3D viewer starts at the very top */
    .main .block-container {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }
    /* Give the Plotly chart as much vertical space as possible */
    [data-testid="stPlotlyChart"] { height: calc(100vh - 52px) !important; min-height: 400px; }
    [data-testid="stPlotlyChart"] > div { height: 100% !important; min-height: 400px; }
    /* Tighten the Streamlit header bar */
    header[data-testid="stHeader"] { height: 2.5rem !important; min-height: 2.5rem !important; }
    /* Sidebar app title styling */
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
    "handrail_type": "Metal",
    "rail_placement": "Side",
    "pole_density": 0.3,
    "viewer_mode": "Face colors",
    "projection_type": "perspective",
    "fisheye_strength": 0.0,
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
            options=["Round", "Square", "Metal", "Curb"],
            key="handrail_type",
        )
        rail_placement = st.radio(
            "Placement",
            options=["Side", "Center"],
            horizontal=True,
            key="rail_placement",
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
        help="0 = off. Adds barrel distortion for a wide-angle lens effect.",
    )
    show_axis_guide = st.checkbox(
        "Show orientation guide", key="show_axis_guide",
        help="Displays an XYZ axis reference below the main viewer.",
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
    "rail_placement": rail_placement.lower(),
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

mesh_parts = build_stair_mesh_parts(**params)
plotly_meshes = build_plotly_meshes(
    mesh_parts,
    viewer_mode=viewer_mode_map[viewer_mode],
    fisheye_strength=fisheye_strength,
    edge_width=edge_width,
    ambient=ambient,
    diffuse=diffuse,
    specular=specular,
    roughness=roughness,
)

scene = {
    "xaxis": {"visible": False},
    "yaxis": {"visible": False},
    "zaxis": {"visible": False},
    "aspectmode": "data",
    "dragmode": "orbit",
    "bgcolor": background_color,
    "uirevision": "stairset_camera",
    "camera": {
        "eye": {"x": 1.5, "y": -1.5, "z": 1.2},
        "center": {"x": 0, "y": 0, "z": 0},
        "up": {"x": 0, "y": 0, "z": 1},
        "projection": {"type": projection_type},
    },
}

fig = {
    "data": plotly_meshes,
    "layout": {
        "scene": scene,
        "showlegend": False,
        "margin": {"l": 0, "r": 0, "b": 0, "t": 0},
        "paper_bgcolor": background_color,
        "uirevision": "stairset_view",
        "autosize": True,
    },
}

st.plotly_chart(
    fig,
    use_container_width=True,
    theme="streamlit",
    config={
        "scrollZoom": True,
        "displayModeBar": True,
        "doubleClick": "reset",
        "responsive": True,
    },
    key="stairset_plot",
)

if show_axis_guide:
    axis_fig = go.Figure()
    for vec, label, color in [
        ([1, 0, 0], "X", "red"),
        ([0, 1, 0], "Y", "green"),
        ([0, 0, 1], "Z", "blue"),
    ]:
        axis_fig.add_trace(go.Scatter3d(
            x=[0, vec[0]], y=[0, vec[1]], z=[0, vec[2]],
            mode="lines+text",
            text=["", label],
            textposition="top center",
            line=dict(color=color, width=6),
            showlegend=False,
        ))
    axis_fig.update_layout(
        scene=dict(
            xaxis=dict(visible=False, range=[-0.2, 1.2]),
            yaxis=dict(visible=False, range=[-0.2, 1.2]),
            zaxis=dict(visible=False, range=[-0.2, 1.2]),
            aspectmode="cube",
        ),
        margin=dict(l=0, r=0, b=0, t=0),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(
        axis_fig, use_container_width=True, height=260,
        config={"displayModeBar": False},
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
        st.caption("Preset URL (copy to share):")
        st.code(_preset_url(), language=None)
