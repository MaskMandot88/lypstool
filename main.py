# ==========================================================
# gomain.py — Versi AutoFix & Diagnostik untuk Google Colab
# ==========================================================
# ✅ Upload file audio & video via Colab
# ✅ Potong audio jadi segmen 59 detik
# ✅ Konversi video otomatis (fallback ke copy stream)
# ✅ Tampilkan log FFmpeg lengkap jika gagal
# ✅ Simpan hasil di /content/output
# ==========================================================

import os
import ffmpeg
import shutil
import asyncio
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from google.colab import files

console = Console()

INPUT = "/content/input"
OUTPUT = "/content/output"
os.makedirs(INPUT, exist_ok=True)
os.makedirs(OUTPUT, exist_ok=True)

USE_COLAB_UPLOAD = True

# ==========================================================
# 🟢 Upload
# ==========================================================
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

# ==========================================================
# 🧠 Helper: Jalankan FFmpeg dan tampilkan log
# ==========================================================
def run_ffmpeg(cmd):
    try:
        print("⚙️  Menjalankan FFmpeg...")
        out, err = cmd.run(capture_stdout=True, capture_stderr=True)
        if err:
            print(err.decode(errors="ignore"))
    except ffmpeg.Error as e:
        print("❌ FFmpeg Error:")
        if e.stderr:
            print("──── FFmpeg stderr ────")
            print(e.stderr.decode(errors="ignore"))
            print("────────────────────────")
        raise

# ==========================================================
# 🎬 Proses media
# ==========================================================
def process_media(audio_path, video_path):
    print("\n🎧 Memotong audio jadi segmen 59 detik...")

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio tidak ditemukan: {audio_path}")
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video tidak ditemukan: {video_path}")

    # ---- Potong Audio ----
    try:
        run_ffmpeg(
            ffmpeg
            .input(audio_path)
            .output(
                f"{OUTPUT}/seg_%02d.mp3",
                f="segment",
                segment_time=59,
                acodec="libmp3lame"
            )
            .overwrite_output()
        )
        print("✅ Audio selesai dipotong.")
    except Exception as e:
        print(f"❌ Gagal potong audio: {e}")
        raise

    # ---- Konversi Video ----
    print("\n🎞️ Mengonversi video (H.264 + AAC)...")
    try:
        run_ffmpeg(
            ffmpeg
            .input(video_path)
            .output(
                f"{OUTPUT}/video_safe.mp4",
                vcodec="libx264",
                acodec="aac",
                preset="veryfast",
                crf=23,
                vf="scale=trunc(iw/2)*2:trunc(ih/2)*2",
                movflags="+faststart",
                video_bitrate="1M",
                audio_bitrate="128k",
                **{'threads': 2}
            )
            .overwrite_output()
        )
        print("✅ Video berhasil dikonversi ke video_safe.mp4")

    except ffmpeg.Error:
        print("⚠️  Konversi penuh gagal — mencoba fallback mode (copy stream)...")
        # fallback: hanya copy stream (tidak encode ulang)
        run_ffmpeg(
            ffmpeg
            .input(video_path)
            .output(
                f"{OUTPUT}/video_safe.mp4",
                vcodec="copy",
                acodec="copy"
            )
            .overwrite_output()
        )
        print("✅ Fallback sukses: video disalin tanpa re-encode")

    # Hitung jumlah segmen
    segments = len([f for f in os.listdir(OUTPUT) if f.startswith("seg_")])
    print(f"🔢 Total segmen audio: {segments}")
    print(f"📂 Hasil disimpan di folder: {OUTPUT}")
    return segments

# ==========================================================
# 🚀 Fungsi utama
# ==========================================================
async def main():
    console.print("[bold cyan]LYPSTOOL COLAB MODE AKTIF 🧩[/bold cyan]")

    audio_path = upload_audio()
    video_path = upload_video()

    console.print(f"\n📁 Audio: [green]{audio_path}[/green]")
    console.print(f"📁 Video: [green]{video_path}[/green]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task("⏳ Memproses media...", start=False)
        progress.start_task(task)
        await asyncio.sleep(1)
        try:
            segments = process_media(audio_path, video_path)
            progress.update(task, description="✅ Proses selesai!")
        except Exception as e:
            console.print(f"[red]❌ Error utama: {e}[/red]")
            return

    console.print(f"\n✅ Semua selesai! Segmen audio: {segments}")
    console.print(f"📦 Cek hasil di: [bold yellow]{OUTPUT}[/bold yellow]")

# ==========================================================
# 🧩 Jalankan manual
# ==========================================================
if __name__ == "__main__":
    asyncio.run(main())
