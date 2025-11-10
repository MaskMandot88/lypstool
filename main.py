# =====================================================================
# main.py — Versi Google Colab (tanpa Tkinter)
# Fungsi:
# 1️⃣ Upload file audio/video via Colab
# 2️⃣ Potong audio & konversi video
# 3️⃣ Jalankan signup & generate otomatis
# =====================================================================

import os
import json
import ffmpeg
import asyncio
from google.colab import files
from signup_terminal_input import signup_akun_sync
from generate_sync_final import generate_sync_final

# ----------------------------------------------------------
# KONFIGURASI DASAR
# ----------------------------------------------------------
INPUT = "/content/input"
OUTPUT = "/content/output"
PROFILES = "/content/profiles"

os.makedirs(INPUT, exist_ok=True)
os.makedirs(OUTPUT, exist_ok=True)
os.makedirs(PROFILES, exist_ok=True)


# ----------------------------------------------------------
# FUNGSI UPLOAD FILE (GANTI TKINTER PICKER)
# ----------------------------------------------------------
def pilih_file_audio():
    print("🎧 Upload file audio (.wav / .mp3):")
    uploaded = files.upload()
    for name, data in uploaded.items():
        path = os.path.join(INPUT, name)
        with open(path, "wb") as f:
            f.write(data)
        print(f"✅ Audio tersimpan: {path}")
        return path
    return None


def pilih_file_video():
    print("🎞️ Upload file video (.mp4 / .mov / .avi):")
    uploaded = files.upload()
    for name, data in uploaded.items():
        path = os.path.join(INPUT, name)
        with open(path, "wb") as f:
            f.write(data)
        print(f"✅ Video tersimpan: {path}")
        return path
    return None


# ----------------------------------------------------------
# FUNGSI MEDIA PROCESS (AUDIO & VIDEO)
# ----------------------------------------------------------
def process_media(audio_path, video_path):
    print("\n🎧 Memotong audio jadi segmen 59 detik...")
    (
        ffmpeg.input(audio_path)
        .output(f"{OUTPUT}/seg_%02d.mp3", f="segment", segment_time=59, acodec="libmp3lame")
        .run(quiet=True, overwrite_output=True)
    )
    print("✅ Audio selesai dipotong.")

    print("🎞️ Mengonversi video...")
    (
        ffmpeg.input(video_path)
        .output(f"{OUTPUT}/video_safe.mp4", vcodec="libx264", acodec="aac", s="1280x?")
        .run(quiet=True, overwrite_output=True)
    )
    print("✅ Video dikonversi.")

    segments = len([f for f in os.listdir(OUTPUT) if f.startswith("seg_")])
    print(f"🔢 Total segmen: {segments}")
    return segments


# ----------------------------------------------------------
# MAIN FUNCTION (JALUR UTAMA)
# ----------------------------------------------------------
async def main():
    print("📦 Persiapan direktori...")
    for folder in [INPUT, OUTPUT, PROFILES]:
        os.makedirs(folder, exist_ok=True)

    # Upload file audio & video
    audio_path = pilih_file_audio()
    video_path = pilih_file_video()
    if not audio_path or not video_path:
        print("❌ Gagal: File audio/video belum diunggah.")
        return

    # Proses media
    total_segments = process_media(audio_path, video_path)

    # Buat akun sync.so via Twibon (signup)
    for i in range(1, total_segments + 1):
        print(f"\n🚀 Membuat akun untuk segmen {i}/{total_segments}...")
        await signup_akun_sync(i)

    # Generate konten sinkron (final process)
    print("\n🎬 Memulai proses generate video sinkron...")
    await generate_sync_final()
    print("✅ Semua proses selesai!")


# ----------------------------------------------------------
# ENTRY POINT
# ----------------------------------------------------------
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ Terjadi kesalahan: {e}")
