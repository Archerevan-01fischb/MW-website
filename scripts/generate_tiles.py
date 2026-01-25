#!/usr/bin/env python3
"""
Midwinter Map Tile Generator
Generates Deep Zoom tiles from a large map image for use with OpenSeadragon.

Usage:
    python generate_tiles.py <input_image> <output_folder>

Example:
    python generate_tiles.py FULLMAP_extracted.png midwinter_map

This creates:
    - midwinter_map.dzi (descriptor file)
    - midwinter_map_files/ (folder with tile pyramid)
"""

import os
import sys
import math
from pathlib import Path

try:
    from PIL import Image
    # Allow very large images (needed for 582M pixel map)
    Image.MAX_IMAGE_PIXELS = 700000000
except ImportError:
    print("ERROR: Pillow is required. Install with: pip install Pillow")
    sys.exit(1)

# Configuration
TILE_SIZE = 512
OVERLAP = 1
JPEG_QUALITY = 85
TILE_FORMAT = "jpg"  # jpg for smaller files, png for lossless


def generate_dzi_tiles(input_path: str, output_base: str):
    """Generate Deep Zoom Image tiles from a large image."""

    print(f"Loading image: {input_path}")
    print("(This may take a while for large images...)")

    # Open with PIL - it will memory-map large images
    img = Image.open(input_path)
    width, height = img.size
    print(f"Image size: {width} x {height} pixels")

    # Calculate number of zoom levels
    max_dimension = max(width, height)
    max_level = math.ceil(math.log2(max_dimension))
    print(f"Zoom levels: 0 to {max_level}")

    # Create output directory
    tiles_dir = Path(f"{output_base}_files")
    tiles_dir.mkdir(parents=True, exist_ok=True)

    # Generate .dzi descriptor file
    dzi_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<Image xmlns="http://schemas.microsoft.com/deepzoom/2008"
       Format="{TILE_FORMAT}"
       Overlap="{OVERLAP}"
       TileSize="{TILE_SIZE}">
    <Size Width="{width}" Height="{height}"/>
</Image>'''

    dzi_path = f"{output_base}.dzi"
    with open(dzi_path, "w") as f:
        f.write(dzi_content)
    print(f"Created: {dzi_path}")

    # Generate tiles for each level
    total_tiles = 0

    for level in range(max_level + 1):
        # Calculate dimensions at this level
        scale = 2 ** (max_level - level)
        level_width = math.ceil(width / scale)
        level_height = math.ceil(height / scale)

        # Create level directory
        level_dir = tiles_dir / str(level)
        level_dir.mkdir(exist_ok=True)

        # Calculate number of tiles
        cols = math.ceil(level_width / TILE_SIZE)
        rows = math.ceil(level_height / TILE_SIZE)

        print(f"Level {level}: {level_width}x{level_height} ({cols}x{rows} tiles)")

        # Resize image for this level
        if scale > 1:
            level_img = img.resize((level_width, level_height), Image.Resampling.LANCZOS)
        else:
            level_img = img

        # Generate tiles
        for row in range(rows):
            for col in range(cols):
                # Calculate tile boundaries with overlap
                x = col * TILE_SIZE
                y = row * TILE_SIZE

                # Add overlap (except at edges)
                x_start = max(0, x - OVERLAP) if col > 0 else 0
                y_start = max(0, y - OVERLAP) if row > 0 else 0
                x_end = min(level_width, x + TILE_SIZE + OVERLAP)
                y_end = min(level_height, y + TILE_SIZE + OVERLAP)

                # Crop tile
                tile = level_img.crop((x_start, y_start, x_end, y_end))

                # Save tile
                tile_path = level_dir / f"{col}_{row}.{TILE_FORMAT}"
                if TILE_FORMAT == "jpg":
                    # Convert to RGB for JPEG (no alpha channel)
                    if tile.mode in ('RGBA', 'LA', 'P'):
                        tile = tile.convert('RGB')
                    tile.save(tile_path, "JPEG", quality=JPEG_QUALITY, optimize=True)
                else:
                    tile.save(tile_path, "PNG", optimize=True)

                total_tiles += 1

        # Clean up level image
        if scale > 1:
            del level_img

    print(f"\nComplete! Generated {total_tiles} tiles")
    print(f"Output: {dzi_path} and {tiles_dir}/")

    # Calculate approximate size
    total_size = sum(f.stat().st_size for f in tiles_dir.rglob("*") if f.is_file())
    print(f"Total size: {total_size / (1024*1024):.1f} MB")


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    input_path = sys.argv[1]
    output_base = sys.argv[2]

    if not os.path.exists(input_path):
        print(f"ERROR: Input file not found: {input_path}")
        sys.exit(1)

    generate_dzi_tiles(input_path, output_base)


if __name__ == "__main__":
    main()
