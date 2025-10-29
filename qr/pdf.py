# --------------------------------------------------------------
# decode_barcode.py – Docker + ZXing + OpenCV (headless)
# --------------------------------------------------------------
import cv2
import subprocess
import os
import sys
import re
from pathlib import Path

# ------------------- CONFIG -------------------
JARS = ["javase-3.5.0.jar", "core-3.5.0.jar", "jcommander-1.82.jar"]
IMAGE_PATH = "./qr/code.jpg"           # ← change if needed
DOCKER_IMAGE = "openjdk:17"
MOUNT_DIR = os.getcwd()
# ------------------------------------------------

def check_files():
    missing = [f for f in JARS + [IMAGE_PATH] if not Path(f).exists()]
    if missing:
        print("Missing files:")
        for m in missing:
            print(f"  - {m}")
        sys.exit(1)

def pull_docker_image():
    print(f"Ensuring Docker image '{DOCKER_IMAGE}' is available...")
    try:
        subprocess.run(["docker", "inspect", DOCKER_IMAGE], check=True, capture_output=True)
        print("  → Image already pulled.")
    except subprocess.CalledProcessError:
        print("  → Pulling image (this may take a minute)...")
        result = subprocess.run(["docker", "pull", DOCKER_IMAGE], capture_output=True, text=True)
        if result.returncode != 0:
            print("Failed to pull image:")
            print(result.stderr)
            sys.exit(1)
        print("  → Pull complete.")

def run_zxing():
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{MOUNT_DIR}:/app",
        "-w", "/app",
        DOCKER_IMAGE,
        "java", "-cp",
        ":".join(f"/app/{jar}" for jar in JARS),
        "com.google.zxing.client.j2se.CommandLineRunner",
        f"/app/{IMAGE_PATH}"
    ]
    print(f"Running ZXing: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("ZXing failed:")
        print(result.stderr)
        sys.exit(1)
    return result.stdout

def parse_zxing_output(output):
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    decoded_text = None
    points = []

    point_pattern = re.compile(r"Point\[(\d+),(\d+)\]")

    for line in lines:
        if "Raw text" in line or "decoded" in line.lower():
            decoded_text = line.split(":", 1)[1].strip()
        elif line.startswith("Point"):
            m = point_pattern.search(line)
            if m:
                x, y = int(m.group(1)), int(m.group(2))
                points.append((x, y))

    return decoded_text, points

def draw_polygon(image_path, points):
    img = cv2.imread(image_path)
    if img is None:
        print("Failed to load image for drawing.")
        return

    pts = cv2.convexHull(np.array(points, dtype=np.int32))
    cv2.polylines(img, [pts], isClosed=True, color=(0, 255, 0), thickness=3)
    cv2.putText(img, "BARCODE", (pts[0][0][0], pts[0][0][1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

    out_path = "annotated_barcode.png"
    cv2.imwrite(out_path, img)
    print(f"Annotated image saved → {out_path}")

# ====================== MAIN ======================
def main():
    print("=== ZXing Barcode Decoder (Docker) ===\n")
    check_files()
    pull_docker_image()
    zxing_output = run_zxing()

    print("\n--- ZXing Raw Output ---")
    print(zxing_output)

    text, points = parse_zxing_output(zxing_output)
    if not text:
        print("\nNo barcode decoded.")
        return

    print(f"\nDecoded Text: {text}")
    if len(points) >= 3:
        print(f"Detected {len(points)} corner points.")
        draw_polygon(IMAGE_PATH, points)
    else:
        print("Not enough points to draw bounding box.")

if __name__ == "__main__":
    main()