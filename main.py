# ==========================================================
# gomain.py — Versi 100% Stabil untuk Google Colab
# ==========================================================
# ✅ Tanpa Rich (aman di Colab)
# ✅ Potong audio jadi segmen 59 detik
# ✅ Konversi video (H.264 + AAC) dengan fallback otomatis
# ✅ Timeout dan log FFmpeg aktif
# ==========================================================

import os
import asyncio
import subprocess
import shutil
from google.colab import files

INPUT = "/content/input"
OUTPUT = "/content/output"
os.makedirs(INPUT, exist_ok=True)
os.makedirs(OUTPUT, exist_ok=True)

USE_COLAB_UPLOAD = True


# ----------------------------------------------------------
# 📁 Upload file
# ----------------------------------------------------------
def upload_audio():
    if USE_COLAB_UPLOAD:
        print("🎧 Upload file audio (.mp3 / .wav):")
        uploaded = files.upload()
        for name in uploaded:
            path = os.path.join(INPUT, name)
            shutil.move(name, path)
            return path
    else:
        return os.path.join(INPUT, "audio.mp3")

def upload_video():
    if USE_COLAB_UPLOAD:
        print("🎞️ Upload file video (.mp4 / .mov / .avi):")
        uploaded = files.upload()
        for name in uploaded:
            path = os.path.join(INPUT, name)
            shutil.move(name, path)
            return path
    else:
        return os.path.join(INPUT, "video.mp4")


# ----------------------------------------------------------
# ⚙️ Jalankan FFmpeg dengan timeout
# ----------------------------------------------------------
async def run_ffmpeg(cmd: list, timeout: int = 120):
    print(f"\n⚙️ Menjalankan FFmpeg:\n{' '.join(cmd)}")
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        process.kill()
        await process.communicate()
        print("❌ Timeout: FFmpeg dihentikan otomatis.")
        raise

    if process.returncode != 0:
        print("──── FFmpeg stderr ────")
        print(stderr.decode(errors="ignore"))
        print("────────────────────────")
        raise RuntimeError("FFmpeg gagal dijalankan.")

    print("✅ FFmpeg selesai.")


# ----------------------------------------------------------
# 🎬 Proses utama
# ----------------------------------------------------------
async def process_media(audio_path, video_path):
    print("\n🎧 Memotong audio menjadi segmen 59 detik...")

    cmd_audio = [
        "ffmpeg", "-y",
        "-i", audio_path,
        "-f", "segment",
        "-segment_time", "59",
        "-acodec", "libmp3lame",
        f"{OUTPUT}/seg_%02d.mp3"
    ]
    await run_ffmpeg(cmd_audio, timeout=120)
    print("✅ Audio selesai dipotong.")

    print("\n🎞️ Mengonversi video ke format aman (H.264 + AAC)...")

    cmd_video = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vcodec", "libx264",
        "-acodec", "aac",
        "-preset", "veryfast",
        "-crf", "23",
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-movflags", "+faststart",
        "-b:v", "1M",
        "-b:a", "128k",
        f"{OUTPUT}/video_safe.mp4"
    ]

    try:
        await run_ffmpeg(cmd_video, timeout=240)
        print("✅ Video berhasil dikonversi ke video_safe.mp4")
    except Exception:
        print("⚠️ Gagal encode ulang — fallback ke copy stream.")
        fallback_cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vcodec", "copy",
            "-acodec", "copy",
            f"{OUTPUT}/video_safe.mp4"
        ]
        await run_ffmpeg(fallback_cmd, timeout=120)
        print("✅ Fallback sukses: video disalin tanpa re-encode.")

    segments = len([f for f in os.listdir(OUTPUT) if f.startswith("seg_")])
    print(f"🔢 Total segmen audio: {segments}")
    print(f"📂 Hasil tersimpan di folder: {OUTPUT}")
    return segments


# ----------------------------------------------------------
# 🚀 Fungsi utama
# ----------------------------------------------------------
async def main():
    print("LYPSTOOL COLAB MODE AKTIF 🧩")

    audio_path = upload_audio()
    video_path = upload_video()

    print(f"\n📁 Audio: {audio_path}")
    print(f"📁 Video: {video_path}")

    try:
        segments = await process_media(audio_path, video_path)
        print("\n✅ Semua selesai!")
        print(f"🔢 Total segmen audio: {segments}")
        print(f"📦 Cek hasil di folder: {OUTPUT}")
    except Exception as e:
        print(f"❌ Error utama: {e}")


# ----------------------------------------------------------
# 🧩 Jalankan manual
# ----------------------------------------------------------
if __name__ == "__main__":
    asyncio.run(main())
