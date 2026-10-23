"""Minimal binary STL writer."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from manifold3d import Manifold


def write_stl(solid: Manifold, path: Path) -> int:
    mesh = solid.to_mesh()
    verts = np.asarray(mesh.vert_properties, dtype=np.float32)[:, :3]
    tris = np.asarray(mesh.tri_verts, dtype=np.int64)
    corners = verts[tris]  # (n, 3, 3)

    normals = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = np.divide(normals, lengths, out=np.zeros_like(normals), where=lengths > 0)

    record = np.dtype([("normal", "<f4", 3), ("v", "<f4", (3, 3)), ("attr", "<u2")])
    data = np.zeros(len(tris), dtype=record)
    data["normal"] = normals
    data["v"] = corners

    with open(path, "wb") as f:
        f.write(b"pdf2stl".ljust(80, b"\0"))
        f.write(np.uint32(len(tris)).tobytes())
        f.write(data.tobytes())
    return len(tris)
