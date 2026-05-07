import json
from typing import Optional

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


def build_uv_sphere(radius, center, lat_segments=8, lon_segments=12):
    """Low-poly UV sphere centered at `center`. Returns (vertices, faces)."""
    cx, cy, cz = center
    verts = [[cx, cy, cz + radius]]  # north pole
    for i in range(1, lat_segments):
        theta = np.pi * i / lat_segments
        z = np.cos(theta) * radius
        r = np.sin(theta) * radius
        for j in range(lon_segments):
            phi = 2.0 * np.pi * j / lon_segments
            verts.append([cx + r * np.cos(phi), cy + r * np.sin(phi), cz + z])
    verts.append([cx, cy, cz - radius])  # south pole
    faces = []
    for j in range(lon_segments):
        nxt = (j + 1) % lon_segments
        faces.append([0, 1 + nxt, 1 + j])
    for i in range(lat_segments - 2):
        ring0 = 1 + i * lon_segments
        ring1 = ring0 + lon_segments
        for j in range(lon_segments):
            nxt = (j + 1) % lon_segments
            faces.append([ring0 + j, ring0 + nxt, ring1 + nxt])
            faces.append([ring0 + j, ring1 + nxt, ring1 + j])
    south = len(verts) - 1
    last_ring = south - lon_segments
    for j in range(lon_segments):
        nxt = (j + 1) % lon_segments
        faces.append([south, last_ring + j, last_ring + nxt])
    return np.array(verts, dtype=float), np.array(faces, dtype=int)


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


def subdivide_mesh(vertices, faces, levels=2):
    """Recursively split each triangle into 4 sub-triangles via edge midpoints.

    levels=0 -> no change. levels=N -> 4**N triangles per original face.
    Returns (new_vertices, new_faces).
    """
    if levels <= 0:
        return vertices, faces
    v = vertices.copy()
    f = faces.copy()
    for _ in range(levels):
        midpoint_cache: dict[tuple[int, int], int] = {}
        v_list = v.tolist()

        def _mid(a: int, b: int) -> int:
            key = (a, b) if a < b else (b, a)
            idx = midpoint_cache.get(key)
            if idx is None:
                mp = ((v[a] + v[b]) / 2.0).tolist()
                idx = len(v_list)
                v_list.append(mp)
                midpoint_cache[key] = idx
            return idx

        new_faces = []
        for tri in f:
            a, b, c = int(tri[0]), int(tri[1]), int(tri[2])
            ab = _mid(a, b)
            bc = _mid(b, c)
            ca = _mid(c, a)
            new_faces.extend([[a, ab, ca], [ab, b, bc], [ca, bc, c], [ab, bc, ca]])
        v = np.array(v_list, dtype=float)
        f = np.array(new_faces, dtype=int)
    return v, f


def explode_per_face(vertices, faces, factor, scale):
    """Detach every triangle and offset it outward along its own face normal.

    Returns (new_vertices, new_faces) with 3 unique verts per triangle.
    Coplanar triangle pairs (e.g. cube quads) move in lockstep so cubes split
    into 6 separated squares; curved meshes shatter into shards radially.

    Triangle normals are flipped where needed to point AWAY from the part
    centroid, so explode always pushes outward regardless of mesh winding.
    """
    if factor <= 0.0:
        return vertices, faces
    if len(faces) == 0:
        return vertices, faces
    tris = vertices[faces]  # (N, 3, 3)
    edge1 = tris[:, 1] - tris[:, 0]
    edge2 = tris[:, 2] - tris[:, 0]
    normals = np.cross(edge1, edge2)
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    norms = np.where(norms < 1e-12, 1.0, norms)
    unit_normals = normals / norms

    part_centroid = vertices.mean(axis=0)
    tri_centroids = tris.mean(axis=1)
    outward = tri_centroids - part_centroid
    flip = np.einsum("ij,ij->i", unit_normals, outward) < 0.0
    unit_normals[flip] *= -1.0

    offsets = unit_normals * (factor * scale)
    new_tris = tris + offsets[:, None, :]
    new_vertices = new_tris.reshape(-1, 3)
    new_faces = np.arange(len(faces) * 3, dtype=int).reshape(-1, 3)
    return new_vertices, new_faces


def _world_centroid_and_scale(mesh_parts):
    if not mesh_parts:
        return np.zeros(3), 1.0
    all_v = np.vstack([p["vertices"] for p in mesh_parts])
    mins = all_v.min(axis=0)
    maxs = all_v.max(axis=0)
    return (mins + maxs) / 2.0, float(np.max(maxs - mins))


def build_plotly_meshes(
    mesh_parts,
    viewer_mode="faces",
    fisheye_strength=0.0,
    edge_width=2,
    ambient=0.6,
    diffuse=0.8,
    specular=0.3,
    roughness=0.5,
    explode_factor=0.0,
    fisheye_subdivide_levels=None,
    projection_type="perspective",
    light_position=None,
):
    import plotly.graph_objects as go

    traces = []
    world_c, world_scale = _world_centroid_and_scale(mesh_parts)

    if fisheye_subdivide_levels is None:
        if fisheye_strength <= 0.0:
            sub_levels = 0
        elif fisheye_strength < 0.4:
            sub_levels = 2
        elif fisheye_strength < 0.7:
            sub_levels = 3
        else:
            sub_levels = 4
    else:
        sub_levels = int(fisheye_subdivide_levels)

    fisheye_center_xz = (float(world_c[0]), float(world_c[2]))
    explode_scale = world_scale * 0.15

    # Light positioned relative to world centroid + user-provided XYZ offset
    # (in world_scale units) so shading reads consistently in both perspective
    # and orthographic projections. In ortho we also bump ambient so unlit
    # faces still receive baseline light.
    if light_position is None:
        lx, ly, lz = 4.0, -8.0, 12.0
    else:
        lx, ly, lz = light_position
    light_pos = dict(
        x=world_c[0] + world_scale * float(lx),
        y=world_c[1] + world_scale * float(ly),
        z=world_c[2] + world_scale * float(lz),
    )
    is_ortho = str(projection_type).lower().startswith("ortho")
    eff_ambient = min(1.0, ambient + (0.15 if is_ortho else 0.0))

    for part in mesh_parts:
        vertices = part["vertices"]
        faces = part["faces"]

        if explode_factor > 0.0:
            vertices, faces = explode_per_face(vertices, faces, explode_factor, explode_scale)

        if sub_levels > 0:
            vertices, faces = subdivide_mesh(vertices, faces, levels=sub_levels)

        if fisheye_strength > 0.0:
            vertices = apply_fisheye(vertices, fisheye_strength, center=fisheye_center_xz)

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
                        ambient=eff_ambient,
                        diffuse=diffuse,
                        specular=specular,
                        roughness=roughness,
                        facenormalsepsilon=1e-12,
                        vertexnormalsepsilon=1e-12,
                    ),
                    lightposition=light_pos,
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


RAIL_PLACEMENT_PRESETS = {
    "right": ["right"],
    "left": ["left"],
    "center": ["center"],
    "side": ["right"],  # legacy alias
    "both": ["left", "right"],
    "both+center": ["left", "right", "center"],
}


def _normalize_rail_placements(rail_placement):
    """Accept str | list[str]. Return list of {'left','right','center'}.

    String inputs map via RAIL_PLACEMENT_PRESETS (lower-cased). Unknown strings
    fall back to ["right"] to preserve historical default.
    """
    if isinstance(rail_placement, (list, tuple, set)):
        normalized = [str(p).lower() for p in rail_placement]
        valid = [p for p in normalized if p in {"left", "right", "center"}]
        return valid or ["right"]
    key = str(rail_placement).lower()
    return list(RAIL_PLACEMENT_PRESETS.get(key, ["right"]))


def _placement_to_x(placement, step_width, inset):
    if placement == "center":
        return 0.0
    if placement == "left":
        return -(step_width / 2.0 - inset)
    return step_width / 2.0 - inset  # right (default)


def build_stair_mesh_parts(
    step_count=8,
    step_width=1.0,
    step_height=0.18,
    step_depth=0.28,
    bottom_extension=0.0,
    top_extension=0.0,
    enable_handrail=True,
    handrail_style="Metal",
    rail_placement="right",
    pole_density=0.3,
    stair_color="#cccccc",
    handrail_color="#404040",
    landings=None,
    rail_bottom_ext=True,
    rail_top_ext=True,
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

    # Per-step Y offset accumulated from landings that precede each step
    if landings is None:
        landings = []
    landings_sorted = sorted(
        [l for l in landings if isinstance(l, dict) and 0 < int(l["after_step"]) < step_count],
        key=lambda l: int(l["after_step"]),
    )
    y_extra = [0.0] * step_count
    _accum = 0.0
    _li = 0
    for _i in range(step_count):
        while _li < len(landings_sorted) and int(landings_sorted[_li]["after_step"]) <= _i:
            _accum += float(landings_sorted[_li]["depth"])
            _li += 1
        y_extra[_i] = _accum

    for i in range(step_count):
        y_front = float(i) * step_depth + y_extra[i] - (bottom_extension if i == 0 else 0.0)
        y_back = float(i + 1) * step_depth + y_extra[i] + (top_extension if i == step_count - 1 else 0.0)
        block_h = float(i + 1) * step_height
        verts, faces = build_box(
            step_width, y_back - y_front, block_h,
            (0.0, (y_front + y_back) / 2.0, block_h / 2.0),
        )
        mesh_parts.append({"vertices": verts, "faces": faces, "color": stair_color})

    # Build flat landing geometry (solid boxes from z=0 to landing height)
    _accum_land_y = 0.0
    for land in landings_sorted:
        _after_i = int(land["after_step"])
        _land_depth = float(land["depth"])
        _land_y_start = float(_after_i) * step_depth + _accum_land_y
        _land_h = float(_after_i) * step_height
        lv, lf = build_box(
            step_width, _land_depth, _land_h,
            (0.0, _land_y_start + _land_depth / 2.0, _land_h / 2.0),
        )
        mesh_parts.append({"vertices": lv, "faces": lf, "color": stair_color})
        _accum_land_y += _land_depth

    if not enable_handrail:
        return mesh_parts

    style_map = {
        "Round":  {"rail_r": 0.025, "post_r": 0.020, "is_round": True,  "rail_height": 0.9},
        "Square": {"rail_r": 0.030, "post_r": 0.025, "is_round": False, "rail_height": 0.9},
        "Curb":   {"thickness": 0.15, "curb_height": 0.88},
    }
    # Legacy alias: presets created before 2026-05-07 may still pass "Metal".
    style = style_map.get(handrail_style, style_map["Round"])

    placements = _normalize_rail_placements(rail_placement)

    if handrail_style == "Curb":
        thickness = style["thickness"]
        curb_height = style["curb_height"]
        ht = thickness / 2.0  # half-thickness for vertex offsets
        ch = curb_height

        def _curb_slab_at(cx, y_front, y_back, z_front, z_back):
            """Parallelogram prism: bottom follows stair slope, top parallel to bottom."""
            verts = np.array([
                [cx - ht, y_front, z_front],
                [cx + ht, y_front, z_front],
                [cx + ht, y_back,  z_back],
                [cx - ht, y_back,  z_back],
                [cx - ht, y_front, z_front + ch],
                [cx + ht, y_front, z_front + ch],
                [cx + ht, y_back,  z_back  + ch],
                [cx - ht, y_back,  z_back  + ch],
            ], dtype=float)
            faces = np.array([
                [0, 2, 1], [0, 3, 2],
                [4, 5, 6], [4, 6, 7],
                [0, 1, 5], [0, 5, 4],
                [3, 7, 6], [3, 6, 2],
                [0, 4, 7], [0, 7, 3],
                [1, 2, 6], [1, 6, 5],
            ], dtype=int)
            return verts, faces

        for _placement in placements:
            cx = _placement_to_x(_placement, step_width, thickness / 2.0)

            if bottom_extension > 0.0 and rail_bottom_ext:
                lv, lf = build_box(
                    thickness, bottom_extension, ch,
                    (cx, -bottom_extension / 2.0, ch / 2.0),
                )
                mesh_parts.append({"vertices": lv, "faces": lf, "color": handrail_color})

            for i in range(step_count):
                y_front = float(i) * step_depth + y_extra[i]
                y_back  = float(i + 1) * step_depth + y_extra[i]
                z_front = float(i) * step_height
                z_back  = float(i + 1) * step_height
                lv, lf = _curb_slab_at(cx, y_front, y_back, z_front, z_back)
                mesh_parts.append({"vertices": lv, "faces": lf, "color": handrail_color})

            if top_extension > 0.0 and rail_top_ext:
                _ext_y = float(step_count) * step_depth + y_extra[step_count - 1]
                _ext_z = float(step_count) * step_height
                lv, lf = build_box(
                    thickness, top_extension, ch,
                    (cx, _ext_y + top_extension / 2.0, _ext_z + ch / 2.0),
                )
                mesh_parts.append({"vertices": lv, "faces": lf, "color": handrail_color})

            _accum_land_y = 0.0
            for land in landings_sorted:
                _after_i = int(land["after_step"])
                _land_depth = float(land["depth"])
                _land_y_start = float(_after_i) * step_depth + _accum_land_y
                _top_z = float(_after_i) * step_height
                lv, lf = build_box(
                    thickness, _land_depth, ch,
                    (cx, _land_y_start + _land_depth / 2.0, _top_z + ch / 2.0),
                )
                mesh_parts.append({"vertices": lv, "faces": lf, "color": handrail_color})
                _accum_land_y += _land_depth
        return mesh_parts

    # Round / Square / Metal
    rail_height = style["rail_height"]
    rail_r = style["rail_r"]
    post_r = style["post_r"]
    is_round = style["is_round"]
    inset = post_r * 3.0

    _landing_by_after = {int(l["after_step"]): l for l in landings_sorted}

    # --- Density-based post placement (rail-X-independent) ---
    # Priority tiers: 0.0 = global ends, 0.5 = landing transitions, 0.5-1.0 = inner bisect.
    runs = []
    run_start = 0
    for land in landings_sorted:
        run_end_idx = int(land["after_step"]) - 1
        if run_end_idx >= run_start:
            runs.append((run_start, run_end_idx))
        run_start = int(land["after_step"])
    runs.append((run_start, step_count - 1))

    step_priority = {0: 0.0, step_count - 1: 0.0}
    for run_idx in range(len(runs) - 1):
        r_end = runs[run_idx][1]
        step_priority.setdefault(r_end, 0.5)

    def _bisect_list(arr, lo, hi, result):
        if hi < lo:
            return
        mid = (lo + hi) // 2
        result.append(arr[mid])
        _bisect_list(arr, lo, mid - 1, result)
        _bisect_list(arr, mid + 1, hi, result)

    inner_ordered = []
    for r_start, r_end in runs:
        inner = [i for i in range(r_start, r_end + 1) if i not in step_priority]
        if inner:
            ordered = []
            _bisect_list(inner, 0, len(inner) - 1, ordered)
            inner_ordered.extend(ordered)

    n_inner = len(inner_ordered)
    for rank, step_i in enumerate(inner_ordered):
        step_priority[step_i] = 0.5 + 0.5 * (rank + 1) / n_inner if n_inner else 0.5

    landing_end_posts = []
    for land in landings_sorted:
        _after_i = int(land["after_step"])
        _land_surface_z = float(_after_i) * step_height
        _tread_center_last = (
            float(_after_i - 1) * step_depth + y_extra[_after_i - 1] + step_depth / 2.0
        )
        _y_land_end = _tread_center_last + float(land["depth"])
        landing_end_posts.append((_y_land_end, _land_surface_z))

    density = float(max(0.0, min(1.0, pole_density)))
    vertical = np.array([0.0, 0.0, 1.0])
    rail_w = rail_r * 2.0

    for _placement in placements:
        rail_x = _placement_to_x(_placement, step_width, inset)

        # Keypoints at tread-centres so posts align; landing transitions kink-free.
        keypoints = []
        if bottom_extension > 0.0 and rail_bottom_ext:
            keypoints.append(np.array([rail_x, -bottom_extension, step_height + rail_height]))
        for i in range(step_count):
            nosing_y = float(i) * step_depth + y_extra[i]
            tread_center_y = nosing_y + step_depth / 2.0
            nosing_z = float(i + 1) * step_height + rail_height
            keypoints.append(np.array([rail_x, tread_center_y, nosing_z]))
            _after_key = i + 1
            if _after_key in _landing_by_after and _after_key < step_count:
                _land = _landing_by_after[_after_key]
                _land_z = float(i + 1) * step_height + rail_height
                _y_land_end = tread_center_y + float(_land["depth"])
                keypoints.append(np.array([rail_x, _y_land_end, _land_z]))
        if top_extension > 0.0 and rail_top_ext:
            keypoints.append(np.array([
                rail_x,
                float(step_count) * step_depth + y_extra[step_count - 1] + top_extension,
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

        # Joint fillers at every kink keypoint. Square rails get an oversized
        # cube; round rails get a UV-sphere — both straddle the joint and
        # close the inner-corner gap that perpendicular cylinder/box end-caps
        # leave at angled rail-to-rail meets.
        if len(rail_pts) >= 3:
            for i in range(1, len(rail_pts) - 1):
                if is_round:
                    jv, jf = build_uv_sphere(rail_r * 1.05, tuple(rail_pts[i]))
                else:
                    # Cylinder axis = X (horizontal, perpendicular to stair run)
                    # so it sits flush across the rail width at each kink.
                    jv, jf = build_oriented_cylinder(rail_w * 0.5, rail_w * 1.05, tuple(rail_pts[i]), (1.0, 0.0, 0.0), segments=12)
                mesh_parts.append({"vertices": jv, "faces": jf, "color": handrail_color})

        for step_i, prio in step_priority.items():
            if prio > density:
                continue
            nosing_y = float(step_i) * step_depth + y_extra[step_i]
            tread_z = float(step_i + 1) * step_height
            post_ctr = (rail_x, nosing_y + step_depth / 2.0, tread_z + rail_height / 2.0)
            if is_round:
                pv, pf = build_oriented_cylinder(post_r, rail_height, post_ctr, vertical, segments=12)
            else:
                pv, pf = build_box(post_r * 2.0, post_r * 2.0, rail_height, post_ctr)
            mesh_parts.append({"vertices": pv, "faces": pf, "color": handrail_color})

        if density >= 0.5:
            for (_y_land_end, _land_surface_z) in landing_end_posts:
                post_ctr = (rail_x, _y_land_end, _land_surface_z + rail_height / 2.0)
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


PAPER_SIZES_INCHES = {
    "A3": (11.69, 16.54),
    "A4": (8.27, 11.69),
    "Letter": (8.5, 11.0),
    "Square": (12.0, 12.0),
}


def _faces_to_pyvista(faces: np.ndarray) -> np.ndarray:
    """Convert (N, 3) triangle indices to pyvista's flat [3, i, j, k, ...] form."""
    n = len(faces)
    out = np.empty((n, 4), dtype=np.int64)
    out[:, 0] = 3
    out[:, 1:] = faces
    return out.ravel()


def _resolve_sub_levels(fisheye_strength: float, override: Optional[int]) -> int:
    if override is not None:
        return int(override)
    if fisheye_strength <= 0.0:
        return 0
    if fisheye_strength < 0.4:
        return 2
    if fisheye_strength < 0.7:
        return 3
    return 4


def build_pyvista_plotter(
    mesh_parts,
    *,
    window_size=(800, 800),
    background_color: str = "#808080",
    viewer_mode: str = "faces",
    edge_color: str = "#222222",
    edge_width: int = 2,
    ambient: float = 0.3,
    diffuse: float = 0.7,
    specular: float = 0.3,
    specular_power: float = 20.0,
    fisheye_strength: float = 0.0,
    fisheye_subdivide_levels: Optional[int] = None,
    explode_factor: float = 0.0,
    projection_type: str = "perspective",
    light_position=(4.0, -8.0, 12.0),
    light_intensity: float = 1.0,
    spotlight_enabled: bool = False,
    spotlight_cone_angle: float = 30.0,
    camera_position=None,
    off_screen: bool = False,
):
    """Build a configured pyvista Plotter for the stair scene.

    `mesh_parts` is the output of `build_stair_mesh_parts`. Lighting params map
    directly to VTK's Phong shader. `light_position` is in world_scale units
    relative to the model centroid — same convention as the Plotly path so
    presets translate. Set `spotlight_enabled=True` to attach a VTK spot light.
    """
    import pyvista as pv

    plotter = pv.Plotter(window_size=list(window_size), off_screen=off_screen, lighting="none")
    plotter.background_color = background_color
    plotter.parallel_projection = str(projection_type).lower().startswith("ortho")

    world_c, world_scale = _world_centroid_and_scale(mesh_parts)
    sub_levels = _resolve_sub_levels(fisheye_strength, fisheye_subdivide_levels)
    fisheye_center_xz = (float(world_c[0]), float(world_c[2]))
    explode_scale = world_scale * 0.15

    show_faces = viewer_mode in ("faces", "faces+edges")
    show_edges = viewer_mode in ("wireframe", "faces+edges")

    for part in mesh_parts:
        verts = part["vertices"]
        faces = part["faces"]
        if explode_factor > 0.0:
            verts, faces = explode_per_face(verts, faces, explode_factor, explode_scale)
        if sub_levels > 0:
            verts, faces = subdivide_mesh(verts, faces, levels=sub_levels)
        if fisheye_strength > 0.0:
            verts = apply_fisheye(verts, fisheye_strength, center=fisheye_center_xz)

        mesh = pv.PolyData(np.asarray(verts, dtype=float), _faces_to_pyvista(faces))
        color = part.get("color", "#999999")

        if show_faces:
            plotter.add_mesh(
                mesh,
                color=color,
                opacity=1.0,
                smooth_shading=False,
                lighting=True,
                ambient=ambient,
                diffuse=diffuse,
                specular=specular,
                specular_power=specular_power,
                show_edges=(viewer_mode == "faces+edges"),
                edge_color=edge_color,
                line_width=edge_width,
            )
        elif show_edges:
            plotter.add_mesh(
                mesh,
                style="wireframe",
                color=color,
                line_width=edge_width,
                lighting=False,
            )

    # Lighting: a key directional light at the user-positioned point + a
    # softer fill light from the opposite side so unlit faces still read.
    lx, ly, lz = light_position
    key_pos = (
        world_c[0] + world_scale * float(lx),
        world_c[1] + world_scale * float(ly),
        world_c[2] + world_scale * float(lz),
    )
    fill_pos = (
        world_c[0] - world_scale * float(lx) * 0.6,
        world_c[1] - world_scale * float(ly) * 0.6,
        world_c[2] + world_scale * abs(float(lz)) * 0.4,
    )
    if spotlight_enabled:
        key_light = pv.Light(
            position=key_pos,
            focal_point=tuple(world_c),
            color="white",
            intensity=float(light_intensity),
            light_type="scene light",
        )
        key_light.positional = True
        key_light.cone_angle = float(spotlight_cone_angle)
        plotter.add_light(key_light)
    else:
        plotter.add_light(
            pv.Light(
                position=key_pos,
                focal_point=tuple(world_c),
                color="white",
                intensity=float(light_intensity),
                light_type="scene light",
            )
        )
    plotter.add_light(
        pv.Light(
            position=fill_pos,
            focal_point=tuple(world_c),
            color="white",
            intensity=0.35,
            light_type="scene light",
        )
    )

    if camera_position is not None:
        plotter.camera_position = camera_position
    else:
        # Default home view — equivalent to Plotly's eye=(1.5,-1.5,1.2)
        focal = tuple(world_c)
        eye = (
            world_c[0] + world_scale * 1.5,
            world_c[1] - world_scale * 1.5,
            world_c[2] + world_scale * 1.2,
        )
        plotter.camera_position = [eye, focal, (0.0, 0.0, 1.0)]
        plotter.reset_camera_clipping_range()

    return plotter


def screenshot_png(plotter, window_size=None, transparent: bool = False) -> bytes:
    """Render the plotter to PNG bytes at the requested window_size."""
    import io
    img = plotter.screenshot(
        transparent_background=transparent,
        return_img=True,
        window_size=list(window_size) if window_size is not None else None,
    )
    from PIL import Image
    buf = io.BytesIO()
    Image.fromarray(img).save(buf, format="PNG")
    return buf.getvalue()
