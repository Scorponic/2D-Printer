"""Command-line entry point: pdf2stl input.pdf [options]"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .config import DEFAULT_CONFIG_PATH, load_config
from .geometry import build_page_solid, build_step_wedge
from .raster import render_pages
from .stl import write_stl

# Form 4L build volume, mm (X, Y, Z).
FORM_4L_BUILD_MM = (353.0, 196.0, 350.0)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="pdf2stl", description="Convert a black & white PDF into paper-like STL(s).")
    p.add_argument("pdf", type=Path, nargs="?", help="input PDF file")
    p.add_argument("-o", "--output", type=Path, help="output STL path (single page) or directory (default: next to the PDF)")
    p.add_argument("-c", "--config", type=Path, default=DEFAULT_CONFIG_PATH, help=f"config file (default: {DEFAULT_CONFIG_PATH.name})")
    p.add_argument("--layer-height", type=float, dest="layer_height_mm", help="override layer height (mm)")
    p.add_argument("--white-layers", type=int, help="override number of layers for white")
    p.add_argument("--black-layers", type=int, help="override number of layers for black")
    p.add_argument("--dpi", type=int, help="override render DPI")
    p.add_argument("--scale", type=float, help="override page scale (1.0 = real size)")
    p.add_argument("--pages", help='override pages, e.g. "1,3" or "all"')
    p.add_argument("--bias", type=float, dest="thickness_bias_layers", help="override thickness bias (fraction of a layer)")
    p.add_argument("--calibrate", action="store_true", help="write a 1-8 layer step model instead of converting a PDF")
    return p.parse_args(argv)


def output_path(args: argparse.Namespace, page: int, multi: bool) -> Path:
    stem = args.pdf.stem
    name = f"{stem}_p{page}.stl" if multi else f"{stem}.stl"
    if args.output is None:
        return args.pdf.with_name(name)
    if args.output.suffix.lower() == ".stl" and not multi:
        return args.output
    args.output.mkdir(parents=True, exist_ok=True)
    return args.output / name


def write_calibration(args: argparse.Namespace, cfg) -> int:
    path = args.output or Path(f"calibration_{cfg.layer_height_mm}mm.stl")
    if path.suffix.lower() != ".stl":
        path.mkdir(parents=True, exist_ok=True)
        path = path / f"calibration_{cfg.layer_height_mm}mm.stl"
    write_stl(build_step_wedge(cfg), path)
    print(
        f"Wrote {path}: 8 steps, 1 to 8 layers left to right, at {cfg.layer_height_mm} mm layers with "
        f"{cfg.thickness_bias_layers} layer bias.\nIn PreForm, slice at {cfg.layer_height_mm} mm and check that step N has N layers."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cfg = load_config(args.config)
    for key in ("layer_height_mm", "white_layers", "black_layers", "dpi", "scale", "thickness_bias_layers"):
        if getattr(args, key) is not None:
            setattr(cfg, key, getattr(args, key))
    if args.pages:
        cfg.pages = "all" if args.pages == "all" else [int(p) for p in args.pages.split(",")]
    try:
        cfg.validate()
    except ValueError as e:
        print(f"Config error: {e}", file=sys.stderr)
        return 2

    if args.calibrate:
        return write_calibration(args, cfg)
    if args.pdf is None:
        print("A PDF file is required (or use --calibrate)", file=sys.stderr)
        return 2
    if not args.pdf.exists():
        print(f"No such file: {args.pdf}", file=sys.stderr)
        return 2

    print(
        f"Layer height {cfg.layer_height_mm} mm | white {cfg.white_layers} layers ({cfg.white_height_mm:.3f} mm) "
        f"| black {cfg.black_layers} layers ({cfg.black_height_mm:.3f} mm) | bias {cfg.thickness_bias_layers} layer | {cfg.dpi} DPI"
    )

    pages = render_pages(args.pdf, cfg.dpi, cfg.pages)
    multi = len(pages) > 1
    for page in pages:
        t0 = time.perf_counter()
        solid = build_page_solid(page.gray, page.pixel_mm, cfg)
        if solid.is_empty():
            print(f"  page {page.number}: nothing to print (page is entirely the 0-layer color)")
            continue
        bx, by, _ = FORM_4L_BUILD_MM
        box = solid.bounding_box()
        w, h, t = box[3] - box[0], box[4] - box[1], box[5] - box[2]
        rotated = False
        if not (w <= bx and h <= by) and (h <= bx and w <= by):
            # Only fits flat sideways: turn it 90° about Z (layer stack is unchanged).
            solid = solid.rotate([0, 0, -90]).translate([0, w, 0])
            w, h, rotated = h, w, True

        path = output_path(args, page.number, multi)
        n_tris = write_stl(solid, path)
        print(
            f"  page {page.number}: {w:.1f} x {h:.1f} x {t:.3f} mm{' (rotated 90° to fit)' if rotated else ''}, "
            f"{n_tris:,} triangles -> {path} ({time.perf_counter() - t0:.1f}s)"
        )
        if not (w <= bx and h <= by):
            # Layer counts only hold when the sheet lies flat on the platform; tilting or supports change them.
            max_scale = cfg.scale * min(bx / max(w, h), by / min(w, h))
            print(
                f"    warning: too large to lie flat on the Form 4L platform ({bx:.0f} x {by:.0f} mm). "
                f"Tilted or supported, the layer counts won't match. Use --scale {int(max_scale * 100) / 100} or smaller."
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
