import cv2
import numpy as np
import os

print("[*] Membuat file-file simulasi uji coba...")

# 1. BIKIN GAMBAR ASLI BERSIH (Normal)
clean_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
# Gambar beberapa pola tajam agar nilai Laplacian tinggi
cv2.rectangle(clean_img, (200, 200), (800, 800), (0, 255, 0), -1)
cv2.putText(clean_img, "SecurePixel Test Clean", (300, 500), 
            cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 4)
cv2.imwrite("sample_clean.jpg", clean_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
print("[+] 'sample_clean.jpg' berhasil dibuat (Gambar Tajam & Bersih).")


# 2. BIKIN GAMBAR DENGAN TANDA C2PA (Simulasi Provenance)
# Kita ambil file clean tadi, lalu inject byte marker standar C2PA (urn:c2pa / jumbf)
with open("sample_clean.jpg", "rb") as f:
    raw_data = f.read()

# Sisipkan penanda byte C2PA di akhir file (simulasi container manifest C2PA)
c2pa_simulated_data = raw_data + b"\x00\x00c2pa_manifest_block_urn:c2pa:test_signature_valid\x00"

with open("sample_with_c2pa.jpg", "wb") as f:
    f.write(c2pa_simulated_data)
print("[+] 'sample_with_c2pa.jpg' berhasil dibuat (Simulasi ada segel C2PA).")


# 3. BIKIN GAMBAR RUSAK PARAH (Simulasi Terdegradasi Ekstrem)
# Perkecil resolusi jadi sangat mini (120x90) + beri efek blur berat
degraded = cv2.resize(clean_img, (160, 120))
degraded = cv2.GaussianBlur(degraded, (15, 15), 0)
cv2.imwrite("sample_degraded.jpg", degraded, [cv2.IMWRITE_JPEG_QUALITY, 20])
print("[+] 'sample_degraded.jpg' berhasil dibuat (Simulasi Rusak Parah).")

print("\n[V] Selesai! Kamu sekarang punya 3 skenario file untuk dites.")