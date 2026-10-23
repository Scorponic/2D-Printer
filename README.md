# 2D Printer

Turn a black & white PDF into a paper-like STL for the Form 4L. Each page becomes a thin sheet,
with **white** and **black** areas printed at different layer counts, so the page's contents show
up as differences in thickness (and so in translucency) in the printed part.

```
 white (2 layers) ▇▇▇▇▇▇      ▇▇▇▇▇▇▇▇▇▇      ▇▇▇▇
 black (1 layer)  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇
                        ^ ink        ^ ink
```

## Setup

Requires [uv](https://docs.astral.sh/uv/) (it handles Python 3.11+ and the dependencies for you).

```bash
uv sync
```

## Usage

```bash
uv run pdf2stl my_document.pdf
```

This writes `my_document.stl` next to the PDF (or `my_document_p1.stl`, `_p2.stl`, … for multi-page
PDFs). Other options:

```bash
uv run pdf2stl my_document.pdf -o output/                 # choose output file or folder
uv run pdf2stl my_document.pdf --white-layers 3 --black-layers 1   # quick override for one run
uv run pdf2stl my_document.pdf --pages 1,3 --dpi 550
uv run pdf2stl my_document.pdf -c my_tuning.toml           # use a different config file
uv run pdf2stl --calibrate                                 # 1-8 layer step model for checking PreForm slicing
```

## Tuning: `config.toml`

All parameters live in [config.toml](config.toml). Edit it and rerun. Command-line flags override it.

| Setting | Meaning |
| --- | --- |
| `layer_height_mm` | Layer height. Match it to the layer height you pick in PreForm. |
| `white_layers` | Layers for white areas |
| `black_layers` | Layers for black areas. `0` turns black areas into cut-outs (stencil mode). |
| `thickness_bias_layers` | Extra fraction of a layer added to each height (default 0.25) so top faces don't land exactly on a slice plane and get dropped |
| `dpi` | Render resolution. The Form 4L's ~46 µm pixel is about 550 DPI. |
| `threshold` | Gray level (0–255) that separates black from white |
| `invert` | Swap black and white |
| `scale` | Scales the page's width and height only; thickness is unchanged (1.0 = real paper size) |
| `simplify_px` | Edge simplification tolerance; higher means fewer triangles |
| `min_feature_px2` | Remove specks smaller than this many square pixels |
| `pages` | `"all"` or a list like `[1, 3]` |

Either color can be the thicker one. For example, `white_layers = 1, black_layers = 3` gives raised ink.

## How it works

1. **Rasterize:** PyMuPDF renders each page to grayscale at `dpi`.
2. **Trace:** scikit-image traces the outlines of the thicker color at `threshold` on the anti-aliased
   image, so edges are sub-pixel smooth rather than stair-stepped. The outlines are then simplified.
3. **Build:** manifold3d makes a full-page slab at the thinner color's height, then unions in the
   thicker regions extruded to their height. The output is always a watertight, manifold mesh.
4. **Export:** a binary STL in millimeters, page bottom-left at the origin, readable from +Z.

Code is in [pdf2stl/](pdf2stl/): `raster.py` → `geometry.py` → `stl.py`, run by `cli.py`.

## Printing notes

- **Check layer counts with `--calibrate`.** It writes a staircase whose steps are 1 to 8 layers thick.
  Slice it in PreForm at the same layer height and check that step N has N layers. If every step is
  one short, raise `thickness_bias_layers` (e.g. to `1.25`). If every step is one over, lower it.

- **The sheet must lie flat, directly on the build platform** (no tilt, no supports). Otherwise the
  slices don't run through the sheet's thickness and the layer counts won't match. The Form 4L
  platform is 353 × 196 mm, so a full-size US Letter or A4 page doesn't fit flat. Use `--scale 0.9`
  (or `scale` in the config). The tool turns the page 90° automatically when that lets it fit, and
  warns when it still doesn't.
- **Don't scale the part in PreForm.** PreForm scales Z as well, which shrinks the layer thickness
  and loses layers. Set the size with `--scale` (or `scale` in the config) instead; it only changes XY.
- With `black_layers = 0`, enclosed islands such as the middle of an "O" become separate loose pieces.
- [examples/sample.pdf](examples/sample.pdf) is a small test page with text, white-on-black, and line weights.

## Roadmap ideas

- "Print to Form 4L" from the macOS print dialog (a PDF Services workflow that calls `pdf2stl`)
- PreForm / Formlabs API integration to create the print job automatically
- More than two thickness levels (grayscale → layer count)
- Optional border frame or ribs for stiffness
