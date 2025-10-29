# --------------------------------------------------------------
# matrix/matrix.py – ZXing Barcode Decoder (Docker + Auto-Download JARs)
# --------------------------------------------------------------
import cv2
import subprocess
import sys
import re
import urllib.request
from pathlib import Path
import os

# ------------------- CONFIG -------------------
JARS = ["javase-3.5.3.jar", "core-3.5.3.jar", "jcommander-1.82.jar"]  # Updated versions
IMAGE_PATH = "./matrix/matrix.png"                  # Your DataMatrix image
DOCKER_IMAGE = "openjdk:17"                  # Stable, exists everywhere
MOUNT_DIR = Path.cwd().resolve()             # Full path for Windows
JAR_BASE_URL = "https://repo1.maven.org/maven2/"
# ------------------------------------------------

def download_jars():
    """Auto-download JARs if missing."""
    jar_dir = Path("jars")
    jar_dir.mkdir(exist_ok=True)
    
    for jar in JARS:
        jar_path = jar_dir / jar
        if not jar_path.exists():
            print(f"Downloading {jar}...")
            if jar == "javase-3.5.3.jar":
                url = f"{JAR_BASE_URL}com/google/zxing/javase/3.5.3/{jar}"
            elif jar == "core-3.5.3.jar":
                url = f"{JAR_BASE_URL}com/google/zxing/core/3.5.3/{jar}"
            else:  # jcommander
                url = f"{JAR_BASE_URL}com/beust/jcommander/1.82/{jar}"
            try:
                urllib.request.urlretrieve(url, jar_path)
                print(f"  → Saved {jar_path}")
            except Exception as e:
                print(f"  → Failed: {e}")
                sys.exit(1)

def check_image():
    if not Path(IMAGE_PATH).exists():
        print(f"Error: Image not found: {IMAGE_PATH}")
        sys.exit(1)

def pull_docker_image():
    print(f"Ensuring Docker image '{DOCKER_IMAGE}' is available...")
    try:
        subprocess.run(["docker", "inspect", DOCKER_IMAGE], 
                       check=True, capture_output=True)
        print("  → Image ready.")
    except subprocess.CalledProcessError:
        print("  → Pulling (one-time, ~300 MB)...")
        result = subprocess.run(["docker", "pull", DOCKER_IMAGE], 
                                capture_output=True, text=True)
        if result.returncode != 0:
            print("Pull failed – check internet/Docker Desktop.")
            print(result.stderr)
            sys.exit(1)
        print("  → Pull complete.")

def run_zxing():
    download_jars()  # Ensure JARs exist
    jar_dir = "jars"
    
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{MOUNT_DIR}:/app",
        "-w", "/app",
        DOCKER_IMAGE,
        "java", "-cp",
        f"/app/{jar_dir}:"
        + ":".join(f"/app/{jar_dir}/{jar}" for jar in JARS),
        "com.google.zxing.client.j2se.CommandLineRunner",
        f"/app/{IMAGE_PATH}"
    ]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("ZXing failed:")
        print(result.stderr)
        sys.exit(1)
    return result.stdout

def parse_output(text):
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    decoded = None
    points = []

    # ZXing output patterns
    point_re = re.compile(r"Point\[(\d+)\]: \((\d+), (\d+)\)")

    for ln in lines:
        if "Raw text:" in ln:
            decoded = ln.split(":", 1)[1].strip()
        elif m := point_re.search(ln):
            x, y = int(m.group(2)), int(m.group(3))
            points.append((x, y))

    return decoded, points

def draw_polygon(img_path, pts):
    img = cv2.imread(img_path)
    if img is None:
        print("Failed to load image for annotation.")
        return
    if len(pts) < 3:
        return

    hull = cv2.convexHull(np.array(pts, dtype=np.int32))
    cv2.polylines(img, [hull], isClosed=True, color=(0, 255, 0), thickness=3)
    cv2.putText(img, "DataMatrix", (hull[0][0][0], hull[0][0][1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

    out = "annotated_matrix.png"
    cv2.imwrite(out, img)
    print(f"Annotated image saved → {out}")

# ====================== MAIN ======================
def main():
    print("=== ZXing DataMatrix Decoder (Docker) ===\n")
    check_image()
    pull_docker_image()

    output = run_zxing()
    print("\n--- ZXing Output ---")
    print(output)

    text, points = parse_output(output)
    if not text:
        print("\nNo barcode decoded. Tips: Higher-res image? Better lighting?")
        return

    print(f"\nDecoded: {text}")
    if points:
        print(f"Found {len(points)} corner points.")
        draw_polygon(IMAGE_PATH, points)
    else:
        print("No bounding box points returned.")

if __name__ == "__main__":
    main()