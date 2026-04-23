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
    .main .block-container { padding-top: 0.5rem !important; padding-bottom: 0 !important; }
    [data-testid="stPlotlyChart"] { height: calc(100vh - 90px) !important; min-height: 400px; }
    [data-testid="stPlotlyChart"] > div { height: 100% !important; min-height: 400px; }
    </style>""",
    unsafe_allow_html=True,
)

st.markdown("### Stairset Generator")

DEFAULTS = {
    "step_count": 8,
    "step_width": 1.0,
    "step_height": 0.18,
    "step_depth": 0.28,
    "bottom_extension": 0.0,
    "top_extension": 0.0,
    "enable_handrail": True,
    "handrail_type": "Metal",
    "rail_placement": "Side",
    "support_count": 4,
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

for key, default_value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default_value

with st.sidebar:
    st.header("Parameters")
    if st.button("Reset to default"):
        for key, default_value in DEFAULTS.items():
            st.session_state[key] = default_value
        st.experimental_rerun()

    st.subheader("Steps")
    step_count = st.slider("Step count", min_value=1, max_value=30, key="step_count")
    step_width = st.number_input(
        "Step width (m)", min_value=0.2, max_value=5.0, step=0.05, key="step_width"
    )
    step_height = st.number_input(
        "Step height (m)", min_value=0.05, max_value=0.4, step=0.01, key="step_height"
    )
    step_depth = st.number_input(
        "Step depth (m)", min_value=0.1, max_value=1.5, step=0.01, key="step_depth"
    )

    st.subheader("Extensions")
    bottom_extension = st.number_input(
        "Bottom extension (m)", min_value=0.0, max_value=3.0, step=0.05, key="bottom_extension"
    )
    top_extension = st.number_input(
        "Top extension (m)", min_value=0.0, max_value=3.0, step=0.05, key="top_extension"
    )

    st.subheader("Handrail")
    enable_handrail = st.checkbox("Enable handrail", key="enable_handrail")
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
        support_count = st.slider(
            "Post count", min_value=2, max_value=16, key="support_count"
        )
    else:
        support_count = st.session_state["support_count"]

    st.markdown("---")
    st.subheader("Colors")
    background_color = st.color_picker("Background", key="background_color")
    stair_color = st.color_picker("Stairs", key="stair_color")
    handrail_color = st.color_picker("Handrail", key="handrail_color")

    st.markdown("---")
    st.subheader("Viewer")
    viewer_mode = st.radio(
        "Render mode",
        options=["Face colors", "Wireframe", "Faces + edges"],
        key="viewer_mode",
    )
    projection_type = st.selectbox(
        "Projection",
        options=["perspective", "orthographic"],
        key="projection_type",
    )
    fisheye_strength = st.slider(
        "Fisheye", min_value=0.0, max_value=1.0, step=0.05, key="fisheye_strength"
    )
    st.markdown("Lighting")
    ambient = st.slider("Ambient", min_value=0.0, max_value=1.0, step=0.05, key="ambient")
    diffuse = st.slider("Diffuse", min_value=0.0, max_value=1.0, step=0.05, key="diffuse")
    specular = st.slider("Specular", min_value=0.0, max_value=1.0, step=0.05, key="specular")
    roughness = st.slider("Roughness", min_value=0.0, max_value=1.0, step=0.05, key="roughness")
    edge_width = st.slider("Edge width", min_value=1, max_value=8, key="edge_width")

    st.markdown("---")
    show_axis_guide = st.checkbox("Show orientation guide", key="show_axis_guide")
    st.markdown("---")
    st.write("Export")

params = {
    "step_count": step_count,
    "step_width": step_width,
    "step_height": step_height,
    "step_depth": step_depth,
    "bottom_extension": bottom_extension,
    "top_extension": top_extension,
    "enable_handrail": enable_handrail,
    "handrail_style": handrail_type,
    "rail_placement": rail_placement.lower(),
    "support_count": support_count,
    "stair_color": stair_color,
    "handrail_color": handrail_color,
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

col1, col2 = st.columns(2)
col1.download_button("Download OBJ", obj_bytes, file_name="stairset.obj", mime="text/plain")
col2.download_button(
    "Download config JSON", json_bytes,
    file_name="stairset-config.json", mime="application/json",
)

with st.expander("Parameters (JSON)"):
    st.json(params)
