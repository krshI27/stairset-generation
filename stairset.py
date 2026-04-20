import json

import numpy as np
from vectorlab import fisheye_vertex as _vectorlab_fisheye

STEP_THICKNESS = 0.04
RAIL_THICKNESS = 0.05
RAIL_HEIGHT = 0.9
POST_SPACING = 0.8
POST_THICKNESS = 0.05


def build_box(width, height, depth, center):
    cx, cy, cz = center
    dx = width / 2.0
    dy = height / 2.0
    dz = depth / 2.0
    vertices = np.array(
        [
            [cx - dx, cy - dy, cz - dz],
            [cx + dx, cy - dy, cz - dz],
            [cx + dx, cy + dy, cz - dz],
            [cx - dx, cy + dy, cz - dz],
            [cx - dx, cy - dy, cz + dz],
            [cx + dx, cy - dy, cz + dz],
            [cx + dx, cy + dy, cz + dz],
            [cx - dx, cy + dy, cz + dz],
        ],
        dtype=float,
    )
    faces = np.array(
        [
            [0, 1, 2],
            [0, 2, 3],
            [4, 6, 5],
            [4, 7, 6],
            [0, 4, 5],
            [0, 5, 1],
            [1, 5, 6],
            [1, 6, 2],
            [2, 6, 7],
            [2, 7, 3],
            [3, 7, 4],
            [3, 4, 0],
        ],
        dtype=int,
    )
    return vertices, faces


def combine_meshes(mesh_parts):
    all_vertices = []
    all_faces = []
    index_offset = 0

    for part in mesh_parts:
        vertices, faces = part["vertices"], part["faces"]
        all_vertices.append(vertices)
        all_faces.append(faces + index_offset)
        index_offset += len(vertices)

    if all_vertices:
        combined = {
            "vertices": np.vstack(all_vertices),
            "faces": np.vstack(all_faces),
            "color": mesh_parts[0]["color"] if len(mesh_parts) == 1 else None,
        }
    else:
        combined = {
            "vertices": np.zeros((0, 3)),
            "faces": np.zeros((0, 3), dtype=int),
            "color": None,
        }

    return combined


def mesh_edges(faces):
    edges = np.vstack(
        [
            faces[:, [0, 1]],
            faces[:, [1, 2]],
            faces[:, [2, 0]],
        ]
    )
    sorted_edges = np.sort(edges, axis=1)
    unique_edges = np.unique(sorted_edges, axis=0)
    return unique_edges


def normalize(vector):
    norm = np.linalg.norm(vector)
    return vector / norm if norm > 0 else vector


def rotation_matrix_from_vectors(vec1, vec2):
    a = normalize(vec1)
    b = normalize(vec2)
    cross = np.cross(a, b)
    dot = np.dot(a, b)
    if np.allclose(cross, 0) and dot > 0.999999:
        return np.eye(3)
    if np.allclose(cross, 0) and dot < -0.999999:
        orth = np.array([1.0, 0.0, 0.0])
        if abs(a[0]) > abs(a[1]):
            orth = np.array([0.0, 1.0, 0.0])
        axis = normalize(np.cross(a, orth))
        return rotation_matrix_from_axis_angle(axis, np.pi)
    kmat = np.array(
        [
            [0, -cross[2], cross[1]],
            [cross[2], 0, -cross[0]],
            [-cross[1], cross[0], 0],
        ]
    )
    return np.eye(3) + kmat + kmat.dot(kmat) * (1.0 / (1.0 + dot))


def rotation_matrix_from_axis_angle(axis, angle):
    axis = normalize(axis)
    c = np.cos(angle)
    s = np.sin(angle)
    t = 1 - c
    x, y, z = axis
    return np.array(
        [
            [t * x * x + c, t * x * y - s * z, t * x * z + s * y],
            [t * x * y + s * z, t * y * y + c, t * y * z - s * x],
            [t * x * z - s * y, t * y * z + s * x, t * z * z + c],
        ]
    )


def transform_vertices(vertices, rotation, translation):
    return vertices.dot(rotation.T) + np.array(translation)


def build_oriented_box(width, height, depth, center, direction):
    vertices, faces = build_box(width, height, depth, (0.0, 0.0, 0.0))
    rotation = rotation_matrix_from_vectors(np.array([0.0, 0.0, 1.0]), direction)
    return transform_vertices(vertices, rotation, center), faces


def build_oriented_cylinder(radius, height, center, direction, segments=16):
    vertices, faces = build_cylinder(radius, height, (0.0, 0.0, 0.0), segments=segments)
    rotation = rotation_matrix_from_vectors(np.array([0.0, 0.0, 1.0]), direction)
    return transform_vertices(vertices, rotation, center), faces


def build_cylinder(radius, height, center, segments=16):
    cx, cy, cz = center
    dz = height / 2.0
    vertices = []
    for i in range(segments):
        angle = 2.0 * np.pi * i / segments
        x = np.cos(angle) * radius
        y = np.sin(angle) * radius
        vertices.append([x, y, -dz])
    for i in range(segments):
        angle = 2.0 * np.pi * i / segments
        x = np.cos(angle) * radius
        y = np.sin(angle) * radius
        vertices.append([x, y, dz])

    bottom_center = len(vertices)
    vertices.append([0.0, 0.0, -dz])
    top_center = len(vertices)
    vertices.append([0.0, 0.0, dz])

    faces = []
    for i in range(segments):
        next_i = (i + 1) % segments
        faces.append([i, next_i, segments + i])
        faces.append([next_i, segments + next_i, segments + i])
        faces.append([bottom_center, next_i, i])
        faces.append([top_center, segments + i, segments + next_i])

    vertices = np.array(vertices, dtype=float)
    vertices[:, 0] += cx
    vertices[:, 1] += cy
    vertices[:, 2] += cz
    return vertices, np.array(faces, dtype=int)


def apply_fisheye(vertices, strength=0.0, center=None):
    if strength <= 0.0:
        return vertices
    return _vectorlab_fisheye(vertices, strength=strength, center=center)


def build_plotly_meshes(
    mesh_parts,
    viewer_mode="faces",
    fisheye_strength=0.0,
    edge_width=2,
    ambient=0.6,
    diffuse=0.8,
    specular=0.3,
    roughness=0.5,
):
    import plotly.graph_objects as go

    traces = []

    for part in mesh_parts:
        vertices = part["vertices"]
        if fisheye_strength > 0.0:
            vertices = apply_fisheye(vertices, fisheye_strength)

        faces = part["faces"]
        color = part.get("color", "#999999")

        if viewer_mode in ("faces", "faces+edges"):
            traces.append(
                go.Mesh3d(
                    x=vertices[:, 0],
                    y=vertices[:, 1],
                    z=vertices[:, 2],
                    i=faces[:, 0],
                    j=faces[:, 1],
                    k=faces[:, 2],
                    color=color,
                    opacity=1.0,
                    flatshading=True,
                    showscale=False,
                    showlegend=False,
                    name="",
                    lighting=dict(
                        ambient=ambient,
                        diffuse=diffuse,
                        specular=specular,
                        roughness=roughness,
                    ),
                    lightposition=dict(x=100, y=200, z=0),
                )
            )

        if viewer_mode in ("wireframe", "faces+edges"):
            edges = mesh_edges(faces)
            line_x = []
            line_y = []
            line_z = []
            for start, end in edges:
                line_x.extend([vertices[start, 0], vertices[end, 0], None])
                line_y.extend([vertices[start, 1], vertices[end, 1], None])
                line_z.extend([vertices[start, 2], vertices[end, 2], None])

            traces.append(
                go.Scatter3d(
                    x=line_x,
                    y=line_y,
                    z=line_z,
                    mode="lines",
                    line=dict(color=color, width=edge_width),
                    hoverinfo="none",
                    showlegend=False,
                    name="",
                )
            )

    return traces


def build_polygon_footprint(sides, width, depth, center=(0.0, 0.0)):
    cx, cy = center
    if sides == 4:
        dx = width / 2.0
        dy = depth / 2.0
        return [
            (cx - dx, cy - dy),
            (cx + dx, cy - dy),
            (cx + dx, cy + dy),
            (cx - dx, cy + dy),
        ]

    angles = np.linspace(0.0, 2.0 * np.pi, sides, endpoint=False)
    return [
        (cx + np.cos(angle) * width / 2.0, cy + np.sin(angle) * depth / 2.0)
        for angle in angles
    ]


def build_prism_from_polygon(footprint, height, z_center):
    bottom = [[x, y, z_center - height / 2.0] for x, y in footprint]
    top = [[x, y, z_center + height / 2.0] for x, y in footprint]
    vertices = np.array(bottom + top, dtype=float)
    n = len(footprint)
    faces = []

    for i in range(1, n - 1):
        faces.append([0, i + 1, i])
    for i in range(1, n - 1):
        faces.append([n, n + i + 1, n + i])

    for i in range(n):
        next_i = (i + 1) % n
        faces.append([i, next_i, next_i + n])
        faces.append([i, next_i + n, i + n])

    return vertices, np.array(faces, dtype=int)


def build_stair_mesh_parts(
    step_count=8,
    base_width=1.0,
    base_depth=0.6,
    step_height=0.18,
    width_decrease=0.02,
    depth_decrease=0.015,
    polygon_sides=4,
    alignment="center",
    enable_handrail=True,
    handrail_style="Metal",
    support_count=4,
    stair_color="#cccccc",
    handrail_color="#404040",
):
    mesh_parts = []
    step_layout = []

    alignment_map = {
        "center": (0.0, 0.0),
        "front-left": (-1.0, 1.0),
        "front-right": (1.0, 1.0),
        "back-left": (-1.0, -1.0),
        "back-right": (1.0, -1.0),
        "left": (-1.0, 0.0),
        "right": (1.0, 0.0),
        "front": (0.0, 1.0),
        "back": (0.0, -1.0),
    }
    align_x, align_y = alignment_map.get(alignment, (0.0, 0.0))

    base_width = max(0.05, float(base_width))
    base_depth = max(0.05, float(base_depth))
    step_height = max(0.01, float(step_height))

    for index in range(step_count):
        step_width = max(0.05, base_width - width_decrease * index)
        step_depth = max(0.05, base_depth - depth_decrease * index)
        offset_x = align_x * (base_width - step_width) / 2.0
        offset_y = align_y * (base_depth - step_depth) / 2.0
        center_z = index * step_height + step_height / 2.0

        footprint = build_polygon_footprint(
            polygon_sides,
            step_width,
            step_depth,
            center=(offset_x, offset_y),
        )
        step_vertices, step_faces = build_prism_from_polygon(
            footprint, step_height, center_z
        )
        mesh_parts.append(
            {
                "vertices": step_vertices,
                "faces": step_faces,
                "color": stair_color,
            }
        )
        step_layout.append(
            {
                "top_z": center_z + step_height / 2.0,
                "offset_x": offset_x,
                "offset_y": offset_y,
                "width": step_width,
                "depth": step_depth,
                "footprint": footprint,
            }
        )

    if enable_handrail and step_layout:
        style_map = {
            "Round": {"rail_thickness": 0.05, "post_thickness": 0.04, "rail_shape": "round", "rail_top_offset": 0.9},
            "Square": {"rail_thickness": 0.06, "post_thickness": 0.05, "rail_shape": "square", "rail_top_offset": 0.9},
            "Metal": {"rail_thickness": 0.045, "post_thickness": 0.035, "rail_shape": "round", "rail_top_offset": 0.9},
            "Concrete ledge": {"rail_thickness": 0.12, "post_thickness": 0.08, "rail_shape": "square", "rail_top_offset": 0.75},
        }
        style = style_map.get(handrail_style, style_map["Metal"])
        rail_top_offset = style["rail_top_offset"]
        rail_thickness = style["rail_thickness"]
        post_thickness = style["post_thickness"]
        is_round = style["rail_shape"] == "round"

        direction = np.array([align_x, align_y], dtype=float)
        if np.linalg.norm(direction) < 1e-6:
            direction = np.array([1.0, 0.0], dtype=float)
        else:
            direction = direction / np.linalg.norm(direction)

        def extreme_point(footprint):
            pts = np.array(footprint, dtype=float)
            return pts[np.argmax(np.dot(pts, direction))]

        keypoints = []
        for step in step_layout:
            p = extreme_point(step["footprint"])
            keypoints.append(
                np.array([p[0], p[1], step["top_z"] + rail_top_offset], dtype=float)
            )

        for i in range(len(keypoints) - 1):
            a, b = keypoints[i], keypoints[i + 1]
            seg_dir = b - a
            seg_length = float(np.linalg.norm(seg_dir))
            if seg_length < 1e-4:
                continue
            seg_center = (a + b) / 2.0
            if is_round:
                rail_vertices, rail_faces = build_oriented_cylinder(
                    rail_thickness / 2.0, seg_length, seg_center, seg_dir, segments=16
                )
            else:
                rail_vertices, rail_faces = build_oriented_box(
                    rail_thickness, rail_thickness, seg_length, seg_center, seg_dir
                )
            mesh_parts.append(
                {"vertices": rail_vertices, "faces": rail_faces, "color": handrail_color}
            )

        vertical_axis = np.array([0.0, 0.0, 1.0], dtype=float)
        for i, step in enumerate(step_layout):
            top = keypoints[i]
            post_height = rail_top_offset
            post_center = (float(top[0]), float(top[1]), float(top[2] - post_height / 2.0))
            if is_round:
                post_vertices, post_faces = build_oriented_cylinder(
                    post_thickness / 2.0, post_height, post_center, vertical_axis, segments=12
                )
            else:
                post_vertices, post_faces = build_box(
                    post_thickness, post_height, post_thickness, post_center
                )
            mesh_parts.append(
                {"vertices": post_vertices, "faces": post_faces, "color": handrail_color}
            )

    return mesh_parts


def export_obj(mesh_parts):
    lines = []
    vertex_offset = 1

    for part in mesh_parts:
        vertices = part["vertices"]
        faces = part["faces"]
        for v in vertices:
            lines.append(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}")
        for f in faces:
            lines.append(
                f"f {f[0] + vertex_offset} {f[1] + vertex_offset} {f[2] + vertex_offset}"
            )
        vertex_offset += len(vertices)

    return "\n".join(lines) + "\n"


def export_json(mesh_params):
    return json.dumps(mesh_params, indent=2)
