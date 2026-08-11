import os
import numpy as np
from PIL import Image

def render_frame(index, total_frames, width, height, max_iter, center_x, center_y):
    zoom = 1.0 * (1.3 ** index)

    x = np.linspace(center_x - 1.5/zoom, center_x + 1.5/zoom, width)
    y = np.linspace(center_y - 1.5/zoom, center_y + 1.5/zoom, height)
    X, Y = np.meshgrid(x, y)
    C = X + 1j * Y
    Z = np.zeros_like(C)
    output = np.zeros(C.shape, dtype=int)

    for i in range(max_iter):
        mask = np.abs(Z) <= 2
        Z[mask] = Z[mask] ** 2 + C[mask]
        output[mask] = i

    img_array = (output / output.max() * 255).astype(np.uint8)
    img = Image.fromarray(img_array, mode="L").convert("RGB")
    return img

if __name__ == "__main__":
    index = int(os.environ.get("JOB_COMPLETION_INDEX", "0"))
    total_frames = int(os.environ.get("TOTAL_FRAMES", "24"))
    max_iter = int(os.environ.get("MAX_ITER", "200"))
    width = int(os.environ.get("FRAME_WIDTH", "640"))
    height = int(os.environ.get("FRAME_HEIGHT", "480"))
    out_dir = os.environ.get("OUTPUT_DIR", "/output")

    center_x = float(os.environ.get("CENTER_X", "-0.743643887037151"))
    center_y = float(os.environ.get("CENTER_Y", "0.13182590420533"))
    print(f"[frame {index}] rendering... (max_iter={max_iter}, center=({center_x},{center_y}))")
    img = render_frame(index, total_frames, width, height, max_iter, center_x, center_y)

    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"frame_{index:04d}.png")
    tmp_path = out_path + ".tmp"
    img.save(tmp_path, format="PNG")
    os.rename(tmp_path, out_path)
    print(f"[frame {index}] saved to {out_path}")
