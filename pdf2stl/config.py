"""Load and validate the TOML configuration."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.toml"


@dataclass
class Config:
    layer_height_mm: float = 0.1
    white_layers: int = 2
    black_layers: int = 1
    thickness_bias_layers: float = 0.25
    dpi: int = 300
    threshold: int = 128
    invert: bool = False
    scale: float = 1.0
    simplify_px: float = 0.5
    min_feature_px2: float = 4.0
    pages: str | list[int] = field(default="all")

    def layers_to_mm(self, layers: int) -> float:
        """Height for a layer count, nudged off the exact slice plane so the slicer can't drop the top layer."""
        if layers == 0:
            return 0.0
        return (layers + self.thickness_bias_layers) * self.layer_height_mm

    @property
    def white_height_mm(self) -> float:
        return self.layers_to_mm(self.white_layers)

    @property
    def black_height_mm(self) -> float:
        return self.layers_to_mm(self.black_layers)

    def validate(self) -> None:
        if self.layer_height_mm <= 0:
            raise ValueError("layer_height_mm must be > 0")
        if self.white_layers < 0 or self.black_layers < 0:
            raise ValueError("white_layers and black_layers must be >= 0")
        if self.white_layers == 0 and self.black_layers == 0:
            raise ValueError("white_layers and black_layers can't both be 0")
        if not -1 < self.thickness_bias_layers < 2:
            raise ValueError("thickness_bias_layers must be between -1 and 2")
        if self.dpi <= 0:
            raise ValueError("dpi must be > 0")
        if not 0 <= self.threshold <= 255:
            raise ValueError("threshold must be between 0 and 255")
        if self.scale <= 0:
            raise ValueError("scale must be > 0")
        if self.pages != "all" and not (
            isinstance(self.pages, list) and all(isinstance(p, int) and p >= 1 for p in self.pages)
        ):
            raise ValueError('pages must be "all" or a list of 1-based page numbers')


def load_config(path: Path | None = None) -> Config:
    path = path or DEFAULT_CONFIG_PATH
    if not path.exists():
        return Config()
    with open(path, "rb") as f:
        raw = tomllib.load(f)

    # Sections are purely organizational; flatten them into one namespace.
    flat: dict = {}
    for key, value in raw.items():
        if isinstance(value, dict):
            flat.update(value)
        else:
            flat[key] = value

    known = Config.__dataclass_fields__.keys()
    unknown = set(flat) - set(known)
    if unknown:
        raise ValueError(f"Unknown config keys in {path}: {', '.join(sorted(unknown))}")
    return Config(**flat)
