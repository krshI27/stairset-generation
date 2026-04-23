import json

import numpy as np
from vectorlab import fisheye_vertex as _vectorlab_fisheye


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


def _build_box_oriented(par_size, perp_size, z_size, center, par_dir_2d, perp_dir_2d):
    """Box aligned to an arbitrary 2D frame in the XY plane, standing upright in Z."""
    par3 = np.array([par_dir_2d[0], par_dir_2d[1], 0.0]) * (par_size / 2)
    per3 = np.array([perp_dir_2d[0], perp_dir_2d[1], 0.0]) * (perp_size / 2)
    zv = np.array([0.0, 0.0, z_size / 2])
    c = np.array(center, dtype=float)
    verts = np.array(
        [
            c - par3 - per3 - zv,
            c + par3 - per3 - zv,
            c + par3 + per3 - zv,
            c - par3 + per3 - zv,
            c - par3 - per3 + zv,
            c + par3 - per3 + zv,
            c + par3 + per3 + zv,
            c - par3 + per3 + zv,
        ],
        dtype=float,
    )
    faces = np.array(
        [
            [0, 1, 2], [0, 2, 3],
            [4, 6, 5], [4, 7, 6],
            [0, 4, 5], [0, 5, 1],
            [1, 5, 6], [1, 6, 2],
            [2, 6, 7], [2, 7, 3],
            [3, 7, 4], [3, 4, 0],
        ],
        dtype=int,
    )
    return verts, faces


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


def build_stair_mesh_parts(
    step_count=8,
    step_width=1.0,
    step_height=0.18,
    step_depth=0.28,
    bottom_extension=0.0,
    top_extension=0.0,
    enable_handrail=True,
    handrail_style="Metal",
    rail_placement="side",
    support_count=4,
    stair_color="#cccccc",
    handrail_color="#404040",
):
    """Linear staircase: each step i is a cumulative block (i+1)*step_height tall,
    step_depth wide, step_width across. Steps ascend in Y and Z."""
    mesh_parts = []
    step_count = max(1, int(step_count))
    step_width = max(0.05, float(step_width))
    step_height = max(0.01, float(step_height))
    step_depth = max(0.05, float(step_depth))
    bottom_extension = max(0.0, float(bottom_extension))
    top_extension = max(0.0, float(top_extension))

    for i in range(step_count):
        y_front = float(i) * step_depth - (bottom_extension if i == 0 else 0.0)
        y_back = float(i + 1) * step_depth + (top_extension if i == step_count - 1 else 0.0)
        block_h = float(i + 1) * step_height
        verts, faces = build_box(
            step_width, y_back - y_front, block_h,
            (0.0, (y_front + y_back) / 2.0, block_h / 2.0),
        )
        mesh_parts.append({"vertices": verts, "faces": faces, "color": stair_color})

    if not enable_handrail:
        return mesh_parts

    style_map = {
        "Round":  {"rail_r": 0.025, "post_r": 0.020, "is_round": True,  "rail_height": 0.9},
        "Square": {"rail_r": 0.030, "post_r": 0.025, "is_round": False, "rail_height": 0.9},
        "Metal":  {"rail_r": 0.022, "post_r": 0.018, "is_round": True,  "rail_height": 0.9},
        "Curb":   {"thickness": 0.15, "curb_height": 0.88},
    }
    style = style_map.get(handrail_style, style_map["Metal"])

    if handrail_style == "Curb":
        thickness = style["thickness"]
        curb_height = style["curb_height"]
        cx = 0.0 if rail_placement == "center" else step_width / 2.0 - thickness / 2.0
        for i in range(step_count):
            y_front = float(i) * step_depth - (bottom_extension if i == 0 else 0.0)
            y_back = float(i + 1) * step_depth + (top_extension if i == step_count - 1 else 0.0)
            top_z = float(i + 1) * step_height
            lv, lf = build_box(
                thickness, y_back - y_front, curb_height,
                (cx, (y_front + y_back) / 2.0, top_z + curb_height / 2.0),
            )
            mesh_parts.append({"vertices": lv, "faces": lf, "color": handrail_color})
        return mesh_parts

    # Round / Square / Metal
    rail_height = style["rail_height"]
    rail_r = style["rail_r"]
    post_r = style["post_r"]
    is_round = style["is_round"]
    inset = post_r * 3.0
    rail_x = 0.0 if rail_placement == "center" else step_width / 2.0 - inset

    # Keypoints: at each step nosing (front edge of tread) at rail_height above tread
    keypoints = []
    if bottom_extension > 0.0:
        keypoints.append(np.array([rail_x, -bottom_extension, step_height + rail_height]))
    for i in range(step_count):
        keypoints.append(np.array([
            rail_x,
            float(i) * step_depth,
            float(i + 1) * step_height + rail_height,
        ]))
    if top_extension > 0.0:
        keypoints.append(np.array([
            rail_x,
            float(step_count) * step_depth + top_extension,
            float(step_count) * step_height + rail_height,
        ]))
    keypoints = np.array(keypoints)

    overhang = 0.15
    if len(keypoints) >= 2:
        d0 = keypoints[1] - keypoints[0]
        d0 /= np.linalg.norm(d0)
        d1 = keypoints[-1] - keypoints[-2]
        d1 /= np.linalg.norm(d1)
        rail_pts = np.vstack([
            keypoints[0:1] - d0 * overhang,
            keypoints,
            keypoints[-1:] + d1 * overhang,
        ])
    else:
        rail_pts = keypoints

    rail_w = rail_r * 2.0
    for i in range(len(rail_pts) - 1):
        a, b = rail_pts[i], rail_pts[i + 1]
        seg = b - a
        seg_len = float(np.linalg.norm(seg))
        if seg_len < 1e-4:
            continue
        ctr = (a + b) / 2.0
        if is_round:
            rv, rf = build_oriented_cylinder(rail_r, seg_len, tuple(ctr), seg, segments=16)
        else:
            rv, rf = build_oriented_box(rail_w, rail_w, seg_len, tuple(ctr), seg)
        mesh_parts.append({"vertices": rv, "faces": rf, "color": handrail_color})

    # Posts evenly distributed across step nosings
    post_idxs = np.unique(
        np.round(np.linspace(0, step_count - 1, min(support_count, step_count))).astype(int)
    )
    vertical = np.array([0.0, 0.0, 1.0])
    for i in post_idxs:
        nosing_y = float(i) * step_depth
        tread_z = float(i + 1) * step_height
        post_ctr = (rail_x, nosing_y, tread_z + rail_height / 2.0)
        if is_round:
            pv, pf = build_oriented_cylinder(post_r, rail_height, post_ctr, vertical, segments=12)
        else:
            pv, pf = build_box(post_r * 2.0, post_r * 2.0, rail_height, post_ctr)
        mesh_parts.append({"vertices": pv, "faces": pf, "color": handrail_color})

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


def render_png(
    size: int = 800,
    elev: float = 20.0,
    azim: float = -60.0,
    bg=None,
    fisheye_strength: float = 0.0,
    **stair_params,
) -> bytes:
    """Headless matplotlib render of a stairset → PNG bytes.

    All `build_stair_mesh_parts` params pass through via **stair_params.
    `bg=None` produces a transparent background; pass a matplotlib color
    string to fill.
    """
    import io

    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    mesh_parts = build_stair_mesh_parts(**stair_params)

    fig = plt.figure(figsize=(size / 150, size / 150), dpi=150)
    ax = fig.add_subplot(111, projection="3d")
    ax.set_axis_off()

    all_v = []
    for part in mesh_parts:
        verts = part["vertices"]
        if fisheye_strength > 0.0:
            verts = apply_fisheye(verts, fisheye_strength)
        faces = part["faces"]
        tri = [[verts[i] for i in face] for face in faces]
        poly = Poly3DCollection(tri, facecolor=part.get("color", "#999999"), edgecolor="none")
        ax.add_collection3d(poly)
        all_v.append(verts)

    if all_v:
        v = np.vstack(all_v)
        mins, maxs = v.min(axis=0), v.max(axis=0)
        ax.set_xlim(mins[0], maxs[0])
        ax.set_ylim(mins[1], maxs[1])
        ax.set_zlim(mins[2], maxs[2])

    try:
        ax.set_box_aspect((1, 1, 1))
    except Exception:
        pass
    ax.view_init(elev=elev, azim=azim)

    transparent = bg is None
    if not transparent:
        fig.patch.set_facecolor(bg)
        ax.set_facecolor(bg)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, transparent=transparent, bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    return buf.getvalue()
