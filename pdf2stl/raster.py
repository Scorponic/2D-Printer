"""Render PDF pages to grayscale images."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pymupdf
import numpy as np


@dataclass
class PageImage:
    number: int  # 1-based page number
    gray: np.ndarray  # (rows, cols) uint8, 0 = black, 255 = white
    pixel_mm: float  # physical size of one pixel


def render_pages(pdf_path: Path, dpi: int, pages: str | list[int] = "all") -> list[PageImage]:
    doc = pymupdf.open(pdf_path)
    numbers = range(1, doc.page_count + 1) if pages == "all" else pages
    images = []
    for n in numbers:
        if n > doc.page_count:
            raise ValueError(f"Page {n} requested but {pdf_path.name} has {doc.page_count} pages")
        pix = doc[n - 1].get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY, alpha=False)
        gray = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.stride)[:, : pix.width]
        images.append(PageImage(number=n, gray=gray.copy(), pixel_mm=25.4 / dpi))
    doc.close()
    return images
