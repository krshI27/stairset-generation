import json

import plotly.graph_objects as go
import streamlit as st

from stairset import (
    build_plotly_meshes,
    build_stair_mesh_parts,
    combine_meshes,
    export_json,
    export_obj,
)

st.set_page_config(
    page_title="Stairset Generator",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Stairset Generator")
st.write(
    "Build procedural stair assemblies with configurable steps, landings, handrails, and exportable mesh output."
)

DEFAULTS = {
    "step_count": 8,
    "base_width": 1.0,
    "base_depth": 0.6,
    "step_height": 0.18,
    "width_decrease": 0.02,
    "depth_decrease": 0.015,
    "polygon_sides": 4,
    "alignment": "center",
    "enable_handrail": True,
    "handrail_type": "Metal",
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

    step_count = st.slider(
        "Step count",
        min_value=1,
        max_value=30,
        key="step_count",
    )
    base_width = st.number_input(
        "Base width (m)",
        min_value=0.2,
        max_value=5.0,
        step=0.05,
        key="base_width",
    )
    base_depth = st.number_input(
        "Base depth (m)",
        min_value=0.2,
        max_value=5.0,
        step=0.05,
        key="base_depth",
    )
    step_height = st.number_input(
        "Step height (m)",
        min_value=0.05,
        max_value=0.4,
        step=0.01,
        key="step_height",
    )
    width_decrease = st.number_input(
        "Width decrease per step (m)",
        min_value=0.0,
        max_value=0.5,
        step=0.01,
        key="width_decrease",
    )
    depth_decrease = st.number_input(
        "Depth decrease per step (m)",
        min_value=0.0,
        max_value=0.5,
        step=0.01,
        key="depth_decrease",
    )
    polygon_sides = st.slider(
        "Polygon footprint sides",
        min_value=3,
        max_value=12,
        key="polygon_sides",
    )
    alignment = st.selectbox(
        "Step alignment",
        options=[
            "center",
            "front-left",
            "front-right",
            "back-left",
            "back-right",
            "left",
            "right",
            "front",
            "back",
        ],
        key="alignment",
    )
    enable_handrail = st.checkbox(
        "Enable handrail",
        key="enable_handrail",
    )
    handrail_type = st.selectbox(
        "Handrail type",
        options=["Round", "Square", "Metal", "Concrete ledge"],
        key="handrail_type",
    )
    support_count = st.slider(
        "Rail support count",
        min_value=2,
        max_value=16,
        key="support_count",
    )

    st.markdown("---")
    st.header("Colors")
    background_color = st.color_picker("Background color", key="background_color")
    stair_color = st.color_picker("Stair color (blocks & ledges)", key="stair_color")
    handrail_color = st.color_picker("Handrail color", key="handrail_color")

    st.markdown("---")
    st.header("Viewer")
    viewer_mode = st.radio(
        "Render mode",
        options=["Face colors", "Wireframe", "Faces + edges"],
        key="viewer_mode",
    )
    projection_type = st.selectbox(
        "Projection type",
        options=["perspective", "orthographic"],
        key="projection_type",
    )
    fisheye_strength = st.slider(
        "Fisheye strength",
        min_value=0.0,
        max_value=1.0,
        step=0.05,
        key="fisheye_strength",
    )
    st.markdown("Lighting")
    ambient = st.slider(
        "Ambient intensity",
        min_value=0.0,
        max_value=1.0,
        step=0.05,
        key="ambient",
    )
    diffuse = st.slider(
        "Diffuse intensity",
        min_value=0.0,
        max_value=1.0,
        step=0.05,
        key="diffuse",
    )
    specular = st.slider(
        "Specular intensity",
        min_value=0.0,
        max_value=1.0,
        step=0.05,
        key="specular",
    )
    roughness = st.slider(
        "Roughness",
        min_value=0.0,
        max_value=1.0,
        step=0.05,
        key="roughness",
    )
    edge_width = st.slider(
        "Edge width",
        min_value=1,
        max_value=8,
        step=1,
        key="edge_width",
    )

    st.markdown("---")
    st.subheader("View helpers")
    show_axis_guide = st.checkbox(
        "Show orientation guide",
        key="show_axis_guide",
    )

    st.markdown("---")
    st.write("Export")

params = {
    "step_count": step_count,
    "base_width": base_width,
    "base_depth": base_depth,
    "step_height": step_height,
    "width_decrease": width_decrease,
    "depth_decrease": depth_decrease,
    "polygon_sides": polygon_sides,
    "alignment": alignment,
    "enable_handrail": enable_handrail,
    "handrail_style": handrail_type,
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

combined_mesh = combine_meshes(mesh_parts)
if len(combined_mesh["vertices"]) > 0:
    verts = combined_mesh["vertices"]
    min_x, max_x = float(verts[:, 0].min()), float(verts[:, 0].max())
    min_y, max_y = float(verts[:, 1].min()), float(verts[:, 1].max())
    min_z, max_z = float(verts[:, 2].min()), float(verts[:, 2].max())
    center_x = (min_x + max_x) / 2.0
    center_y = (min_y + max_y) / 2.0
    center_z = (min_z + max_z) / 2.0
    span_x = max(max_x - min_x, 0.1)
    span_y = max(max_y - min_y, 0.1)
    span_z = max(max_z - min_z, 0.1)
else:
    center_x = center_y = center_z = 0.0
    span_x = span_y = span_z = 1.0

camera = dict(
    eye=dict(x=1.8, y=1.2, z=1.8),
    center=dict(x=center_x, y=center_y, z=center_z),
    up=dict(x=0, y=0, z=1),
    projection={"type": projection_type},
)

scene = {
    "xaxis": {"visible": False},
    "yaxis": {"visible": False},
    "zaxis": {"visible": False},
    "aspectmode": "data",
    "dragmode": "orbit",
    "bgcolor": background_color,
    "uirevision": "stairset_camera",
}

if not st.session_state.get("stairset_view_initialized"):
    scene["camera"] = camera
    st.session_state["stairset_view_initialized"] = True

fig = {
    "data": plotly_meshes,
    "layout": {
        "scene": scene,
        "showlegend": False,
        "margin": {"l": 0, "r": 0, "b": 0, "t": 0},
        "paper_bgcolor": background_color,
        "uirevision": "stairset_view",
    },
}

st.plotly_chart(
    fig,
    use_container_width=True,
    height=700,
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
    axis_fig.add_trace(
        go.Scatter3d(
            x=[0, 1.0],
            y=[0, 0],
            z=[0, 0],
            mode='lines+text',
            text=['', 'X'],
            textposition='top center',
            line=dict(color='red', width=6),
            showlegend=False,
        )
    )
    axis_fig.add_trace(
        go.Scatter3d(
            x=[0, 0],
            y=[0, 1.0],
            z=[0, 0],
            mode='lines+text',
            text=['', 'Y'],
            textposition='top center',
            line=dict(color='green', width=6),
            showlegend=False,
        )
    )
    axis_fig.add_trace(
        go.Scatter3d(
            x=[0, 0],
            y=[0, 0],
            z=[0, 1.0],
            mode='lines+text',
            text=['', 'Z'],
            textposition='top center',
            line=dict(color='blue', width=6),
            showlegend=False,
        )
    )
    axis_fig.update_layout(
        scene=dict(
            xaxis=dict(visible=False, range=[-0.2, 1.2]),
            yaxis=dict(visible=False, range=[-0.2, 1.2]),
            zaxis=dict(visible=False, range=[-0.2, 1.2]),
            aspectmode='cube',
        ),
        margin=dict(l=0, r=0, b=0, t=0),
        paper_bgcolor='rgba(0,0,0,0)',
    )
    st.plotly_chart(
        axis_fig,
        use_container_width=True,
        height=260,
        config={"displayModeBar": False},
    )

obj_bytes = export_obj(mesh_parts).encode("utf-8")
json_bytes = export_json(params).encode("utf-8")

col1, col2 = st.columns(2)
col1.download_button(
    "Download OBJ", obj_bytes, file_name="stairset.obj", mime="text/plain"
)
col2.download_button(
    "Download config JSON",
    json_bytes,
    file_name="stairset-config.json",
    mime="application/json",
)

with st.expander("Stairset parameters (JSON)"):
    st.json(params)
