"""Turn a grayscale page image into a watertight two-height solid."""

from __future__ import annotations

import numpy as np
from manifold3d import CrossSection, FillRule, Manifold
from skimage.measure import approximate_polygon, find_contours

from .config import Config


def _region_contours(gray: np.ndarray, threshold: float, raised_is_white: bool, cfg: Config) -> list[np.ndarray]:
    """Trace the outlines of the raised color as closed polygons in pixel units (x right, y up).

    Contours are traced on the anti-aliased grayscale image, so edges land at sub-pixel
    positions instead of following the pixel staircase.
    """
    # Normalize so the raised color is always "high", then pad with "low" so every contour closes.
    img = gray.astype(np.float32) if raised_is_white else 255.0 - gray.astype(np.float32)
    level = threshold if raised_is_white else 255.0 - threshold
    padded = np.pad(img, 1, constant_values=0.0)
    rows = gray.shape[0]

    polygons = []
    for contour in find_contours(padded, level):
        if cfg.simplify_px > 0:
            contour = approximate_polygon(contour, tolerance=cfg.simplify_px)
        if len(contour) < 4:  # closed contours repeat the first point
            continue
        # (row, col) in padded image -> (x, y) with origin at the page's bottom-left corner.
        x = contour[:, 1] - 0.5
        y = rows - (contour[:, 0] - 0.5)
        poly = np.column_stack([x, y])[:-1]
        area = 0.5 * abs(np.dot(poly[:, 0], np.roll(poly[:, 1], 1)) - np.dot(poly[:, 1], np.roll(poly[:, 0], 1)))
        if area < cfg.min_feature_px2:
            continue
        polygons.append(poly)
    return polygons


def build_page_solid(gray: np.ndarray, pixel_mm: float, cfg: Config) -> Manifold:
    """Full-page slab at the thinner color's height, plus the thicker color's regions raised on top."""
    if cfg.invert:
        gray = 255 - gray
    rows, cols = gray.shape
    mm = pixel_mm * cfg.scale

    base_h = min(cfg.white_height_mm, cfg.black_height_mm)
    top_h = max(cfg.white_height_mm, cfg.black_height_mm)
    raised_is_white = cfg.white_height_mm > cfg.black_height_mm

    solid = Manifold()
    if base_h > 0:
        solid = Manifold.extrude(CrossSection.square([cols * mm, rows * mm]), base_h)

    if top_h > base_h:
        contours = _region_contours(gray, cfg.threshold, raised_is_white, cfg)
        if contours:
            # Even-odd fill makes nested outlines (e.g. the hole in an "o") come out as holes.
            region = CrossSection([c * mm for c in contours], FillRule.EvenOdd)
            solid = solid + Manifold.extrude(region, top_h)

    return solid


def build_step_wedge(cfg: Config, max_layers: int = 8, step_mm: float = 10.0, depth_mm: float = 20.0) -> Manifold:
    """Staircase of 1..max_layers layers (left to right) for checking how the slicer counts layers."""
    solid = Manifold()
    for i in range(1, max_layers + 1):
        step = Manifold.cube([step_mm, depth_mm, cfg.layers_to_mm(i)]).translate([(i - 1) * step_mm, 0, 0])
        solid = solid + step
    return solid
