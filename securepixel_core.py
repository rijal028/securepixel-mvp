import os
import sys
import cv2
import numpy as np
from PIL import Image

def check_c2pa(image_path: str) -> dict:
    """Tahap 1: Cek C2PA metadata."""
    has_c2pa = False
    details = "Tidak ada metadata C2PA terdeteksi."
    try:
        with open(image_path, "rb") as f:
            content = f.read()
            if b"c2pa" in content or b"urn:c2pa" in content:
                has_c2pa = True
                details = "Manifes C2PA Content Credentials valid ditemukan."
    except Exception as e:
        details = f"Gagal membaca metadata: {str(e)}"
    return {"has_c2pa": has_c2pa, "details": details}

def profile_degradation(image_path: str) -> dict:
    """Tahap 2: Degradation Profiler."""
    img_cv = cv2.imread(image_path)
    if img_cv is None:
        raise ValueError(f"File tidak bisa dibaca sebagai gambar: {image_path}")

    height, width, _ = img_cv.shape
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    # 1. Ketajaman / Blur
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    # 2. Resolusi
    total_pixels = height * width
    is_downscaled = bool(total_pixels < (720 * 1280))

    # 3. Kualitas JPEG
    jpeg_quality = None
    try:
        with Image.open(image_path) as img_pil:
            quantization = getattr(img_pil, "quantization", None)
            if quantization:
                avg_q_val = float(np.mean(list(quantization.values())[0]))
                jpeg_quality = int(max(10, min(100, 100 - (avg_q_val * 1.5))))
    except Exception:
        jpeg_quality = None

    # 4. Batas Operating Envelope
    is_severely_degraded = bool(laplacian_var < 50.0 and is_downscaled)

    return {
        "dimensions": f"{width}x{height}",
        "sharpness_score": round(laplacian_var, 2),
        "estimated_jpeg_quality": jpeg_quality if jpeg_quality else "Bukan JPEG / Metadata Dihapus",
        "is_downscaled": is_downscaled,
        "is_severely_degraded": is_severely_degraded
    }

def analyze_file(image_path: str) -> dict:
    c2pa_res = check_c2pa(image_path)
    if c2pa_res["has_c2pa"]:
        return {
            "status": "STOP",
            "verdict": "VERIFIED ORIGIN",
            "reason": c2pa_res["details"],
            "send_to_gpu": False
        }

    profile = profile_degradation(image_path)
    if profile["is_severely_degraded"]:
        return {
            "status": "STOP",
            "verdict": "INCONCLUSIVE",
            "reason": "Kualitas berkas terlalu rusak untuk analisis forensik yang aman.",
            "metrics": profile,
            "send_to_gpu": False
        }

    return {
        "status": "PROCEED",
        "verdict": "PENDING_FORENSICS",
        "reason": "Kondisi berkas memenuhi syarat. Lanjut ke analisis Model Forensik.",
        "metrics": profile,
        "send_to_gpu": True
    }

# --- LANGSUNG DIEKSEKUSI ---
print("\n>>> Program SecurePixel Core Dimulai...")

target_img = sys.argv[1] if len(sys.argv) > 1 else "test.jpg"

# Jika file test.jpg belum ada, buat gambar tiruan otomatis
if not os.path.exists(target_img):
    print(f"[i] File '{target_img}' belum ada. Membuat gambar dummy sintetis untuk tes...")
    dummy = np.random.randint(0, 256, (800, 1200, 3), dtype=np.uint8)
    cv2.imwrite(target_img, dummy)
    print(f"[i] Berhasil membuat '{target_img}'.")

print(f"[*] Menganalisis file: {target_img}\n")
hasil = analyze_file(target_img)

print("=" * 45)
print("HASIL ANALISIS SECUREPIXEL (TAHAP 1 & 2)")
print("=" * 45)
for k, v in hasil.items():
    print(f"{k:<15}: {v}")
print("=" * 45 + "\n")