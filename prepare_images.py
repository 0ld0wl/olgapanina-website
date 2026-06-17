"""
prepare_images.py — prepare photos for the website.

What it does:
  1. Picks up all images from the _raw/ folder
  2. Resizes them down to 1600px on the longest side (web-friendly)
  3. Compresses to JPEG quality 85 (visually lossless, 5-10x smaller)
  4. Renames to lowercase .jpg (so paths work the same on macOS and Linux)
  5. Drops the result into images/
  6. If the source is already a small JPEG, just copies it (no re-encoding,
     to avoid quality loss from double compression)

Usage:
  1. Put original photos into the _raw/ folder inside olgapanina-website/
  2. In the terminal:
       cd /Users/olga/Documents/Claude/Projects/Webpage/olgapanina-website
       python3 prepare_images.py
  3. Processed versions will appear in images/

Options:
  python3 prepare_images.py blog
     → output goes to images/blog/ (for blog post photos)

  python3 prepare_images.py _raw/portraits images/photos
     → custom input and output folders
"""

import os
import shutil
import sys
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    print("ERROR: Pillow library is not installed.")
    print("Install it with:  pip install Pillow")
    sys.exit(1)


# Quality and size settings
MAX_WIDTH = 1600                  # maximum width in pixels
JPEG_QUALITY = 85                 # 1-100. 85 = best balance of size and quality for web
SKIP_SIZE_BYTES = 500 * 1024      # 500KB. Files smaller than this aren't re-compressed


def prepare_one(src_path: Path, dst_path: Path) -> str:
    """
    Process one image.
    Returns 'compressed' (re-encoded) or 'copied' (just copied as-is).
    """
    src_size = src_path.stat().st_size
    is_jpeg = src_path.suffix.lower() in (".jpg", ".jpeg")

    # Quick check: if it's already a small JPEG with the right width,
    # just copy it. Avoids quality loss from re-compressing.
    if is_jpeg and src_size <= SKIP_SIZE_BYTES:
        with Image.open(src_path) as img_peek:
            w, h = img_peek.size
        if w <= MAX_WIDTH:
            shutil.copy2(src_path, dst_path)
            return "copied"

    # Otherwise, do the full processing
    img = Image.open(src_path)

    # Honor EXIF rotation (phone photos often carry a rotation tag)
    img = ImageOps.exif_transpose(img)

    # Convert to RGB if needed (JPEG doesn't support alpha)
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")

    # Resize if wider than MAX_WIDTH
    w, h = img.size
    if w > MAX_WIDTH:
        new_h = int(h * MAX_WIDTH / w)
        img = img.resize((MAX_WIDTH, new_h), Image.LANCZOS)

    # Save as optimized JPEG
    img.save(dst_path, "JPEG", quality=JPEG_QUALITY, optimize=True)
    return "compressed"


def lowercase_jpg_name(filename: str) -> str:
    """horse.JPEG → horse.jpg, MyPhoto.PNG → myphoto.jpg"""
    stem = Path(filename).stem.lower()
    return f"{stem}.jpg"


def process_folder(src_dir: Path, dst_dir: Path) -> None:
    """Walks through src_dir and writes processed images to dst_dir."""
    if not src_dir.exists():
        print(f"ERROR: folder {src_dir} doesn't exist.")
        print("Create it and put the original photos inside.")
        sys.exit(1)

    dst_dir.mkdir(parents=True, exist_ok=True)

    image_extensions = (".jpg", ".jpeg", ".png", ".heic", ".webp", ".tiff", ".bmp")
    files = [f for f in src_dir.iterdir()
             if f.is_file() and f.suffix.lower() in image_extensions]

    if not files:
        print(f"No images found in {src_dir}. Add some photos and run again.")
        return

    print(f"Processing {len(files)} file(s) from {src_dir} → {dst_dir}\n")

    total_before, total_after = 0, 0
    n_compressed, n_copied = 0, 0

    for src in sorted(files):
        new_name = lowercase_jpg_name(src.name)
        dst = dst_dir / new_name

        before = src.stat().st_size

        try:
            action = prepare_one(src, dst)
            after = dst.stat().st_size
            total_before += before
            total_after += after

            if action == "copied":
                n_copied += 1
                print(f"  {src.name:35s} → {new_name:30s}  "
                      f"{before/1024:6.0f}KB  (already small, kept as-is)")
            else:
                n_compressed += 1
                print(f"  {src.name:35s} → {new_name:30s}  "
                      f"{before/1024:6.0f}KB → {after/1024:5.0f}KB  "
                      f"(-{(1 - after/before)*100:.0f}%)")
        except Exception as e:
            print(f"  {src.name:35s} → ERROR: {e}")

    if total_before > 0:
        print(f"\nTotal: {total_before/1024/1024:.1f}MB → {total_after/1024/1024:.1f}MB")
        if n_compressed > 0 and total_before > total_after:
            print(f"  compressed {n_compressed} file(s), {total_before/total_after:.1f}x smaller")
        if n_copied > 0:
            print(f"  copied {n_copied} already-small file(s) without changes")


def main():
    project_root = Path(__file__).parent
    args = sys.argv[1:]

    if len(args) == 0:
        # python3 prepare_images.py
        src_dir = project_root / "_raw"
        dst_dir = project_root / "images"
    elif len(args) == 1:
        # python3 prepare_images.py blog
        # → _raw/ → images/blog/
        subfolder = args[0]
        src_dir = project_root / "_raw"
        dst_dir = project_root / "images" / subfolder
    elif len(args) == 2:
        # python3 prepare_images.py src/path dst/path
        src_dir = Path(args[0])
        dst_dir = Path(args[1])
        if not src_dir.is_absolute():
            src_dir = project_root / src_dir
        if not dst_dir.is_absolute():
            dst_dir = project_root / dst_dir
    else:
        print("Usage:")
        print("  python3 prepare_images.py                    # _raw/ → images/")
        print("  python3 prepare_images.py blog               # _raw/ → images/blog/")
        print("  python3 prepare_images.py src/path dst/path  # custom folders")
        sys.exit(1)

    process_folder(src_dir, dst_dir)


if __name__ == "__main__":
    main()
