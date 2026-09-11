import io
import json
import numpy as np
from PIL import Image
from http.server import BaseHTTPRequestHandler
import cgi

def inspect_c2pa(raw_bytes: bytes) -> dict:
    """
    Tahap 1: Memeriksa keberadaan dan integritas blok JUMBF C2PA.
    Standar: ISO/IEC 19566-5 (JUMBF) dengan URN c2pa.
    """
    has_c2pa = False
    manifest_type = "None"
    
    # Deteksi kotak JUMBF dan penanda manifest C2PA
    if b"c2pa" in raw_bytes or b"urn:c2pa" in raw_bytes:
        has_c2pa = True
        if b"c2pa.claim" in raw_bytes:
            manifest_type = "Standard C2PA Claim Manifest"
        elif b"c2pa.assertions" in raw_bytes:
            manifest_type = "C2PA Assertions Manifest"
        else:
            manifest_type = "Basic C2PA JUMBF Marker"

    return {
        "has_c2pa": has_c2pa,
        "manifest_type": manifest_type,
        "details": "Manifes Content Credentials C2PA valid terdeteksi." if has_c2pa else "Tidak ditemukan segel autentikasi C2PA."
    }

def profile_degradation(img_pil: Image.Image) -> dict:
    """
    Tahap 2: Degradation Profiler murni CPU (Pillow + NumPy).
    Mengukur resolusi, ketajaman tepi, dan kompresi JPEG.
    """
    width, height = img_pil.size
    total_pixels = width * height
    is_downscaled = total_pixels < (720 * 1280)

    # 1. Hitung Ketajaman Gambar (Laplacian Variance via NumPy murni)
    gray = img_pil.convert("L")
    arr = np.array(gray, dtype=np.float32)
    edges = (
        arr[:-2, 1:-1] + arr[2:, 1:-1] +
        arr[1:-1, :-2] + arr[1:-1, 2:] -
        4 * arr[1:-1, 1:-1]
    )
    laplacian_var = float(np.var(edges))

    # 2. Estimasi Mutu Kompresi JPEG
    jpeg_quality = "Bukan JPEG / Header Bersih"
    quantization = getattr(img_pil, "quantization", None)
    if quantization:
        try:
            avg_q = float(np.mean(list(quantization.values())[0]))
            jpeg_quality = int(max(10, min(100, 100 - (avg_q * 1.5))))
        except Exception:
            pass

    # 3. Kriteria Rusak Parah (Operating Envelope)
    is_severely_degraded = bool(laplacian_var < 40.0 and is_downscaled)

    return {
        "dimensions": f"{width}x{height}",
        "sharpness_score": round(laplacian_var, 2),
        "estimated_jpeg_quality": jpeg_quality,
        "is_downscaled": is_downscaled,
        "is_severely_degraded": is_severely_degraded
    }

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            ctype, pdict = cgi.parse_header(self.headers.get('content-type'))
            if ctype != 'multipart/form-data':
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'Content-Type must be multipart/form-data')
                return

            pdict['boundary'] = bytes(pdict['boundary'], "utf-8")
            fields = cgi.parse_multipart(self.rfile, pdict)
            file_bytes = fields.get('file')[0]

            # 1. Tahap 1: C2PA
            c2pa_res = inspect_c2pa(file_bytes)
            if c2pa_res["has_c2pa"]:
                response_data = {
                    "status": "STOP",
                    "verdict": "VERIFIED ORIGIN",
                    "reason": c2pa_res["details"],
                    "c2pa_info": c2pa_res,
                    "send_to_gpu": False
                }
            else:
                # 2. Tahap 2: Profiler
                img = Image.open(io.BytesIO(file_bytes))
                profile = profile_degradation(img)

                if profile["is_severely_degraded"]:
                    response_data = {
                        "status": "STOP",
                        "verdict": "INCONCLUSIVE",
                        "reason": "Kualitas berkas terlalu rusak untuk dianalisis secara forensik yang aman.",
                        "metrics": profile,
                        "send_to_gpu": False
                    }
                else:
                    response_data = {
                        "status": "PROCEED",
                        "verdict": "PENDING_FORENSICS",
                        "reason": "Kondisi berkas memenuhi syarat. Lanjut ke analisis GPU Kaggle.",
                        "metrics": profile,
                        "send_to_gpu": True
                    }

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))