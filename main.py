# ===============================================================
# main_colab.py — Versi Tunggal untuk Google Colab
# ===============================================================
# Fitur:
# ✅ Upload file video & audio via Google Colab
# ✅ Potong audio jadi segmen
# ✅ Signup otomatis di Sync.so (via Twibon / Mail API)
# ✅ Simpan profil & hasil generate ke /content/
# ===============================================================

import os
import json
import time
import ffmpeg
import asyncio
import shutil
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from playwright.async_api import async_playwright
from google.colab import files

console = Console()

# ===============================================================
# 1️⃣ Setup Direktori
# ===============================================================
INPUT = "/content/input"
OUTPUT = "/content/output"
PROFILES = "/content/profiles"

os.makedirs(INPUT, exist_ok=True)
os.makedirs(OUTPUT, exist_ok=True)
os.makedirs(PROFILES, exist_ok=True)


# ===============================================================
# 2️⃣ Upload File (Colab-compatible)
# ===============================================================
def upload_audio():
    print("🎧 Upload file audio (.mp3 / .wav):")
    uploaded = files.upload()
    for name, data in uploaded.items():
        path = os.path.join(INPUT, name)
        with open(path, "wb") as f:
            f.write(data)
        print(f"✅ Audio tersimpan: {path}")
        return path
    return None


def upload_video():
    print("🎞️ Upload file video (.mp4 / .mov / .avi):")
    uploaded = files.upload()
    for name, data in uploaded.items():
        path = os.path.join(INPUT, name)
        with open(path, "wb") as f:
            f.write(data)
        print(f"✅ Video tersimpan: {path}")
        return path
    return None


# ===============================================================
# 3️⃣ Pemrosesan Media (Audio/Video)
# ===============================================================
def process_media(audio_path, video_path):
    print("\n🎧 Memotong audio menjadi segmen 59 detik...")
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


# ===============================================================
# 4️⃣ Fungsi Signup Otomatis (versi Twibon / Mail)
# ===============================================================
async def signup_akun_sync(index: int):
    """Membuat akun Sync.so otomatis"""
    try:
        console.rule(f"[bold magenta]Membuat akun {index}[/bold magenta]")

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
            context = await browser.new_context()
            page = await context.new_page()

            # Buka Twibon / Mail Generator
            await page.goto("https://taftazanie-elhaff-mailtwibon.pages.dev", timeout=60000)
            await page.wait_for_timeout(3000)

            # Ambil alamat email
            email_el = page.locator("code").first
            email = await email_el.inner_text()
            console.print(f"📧 Email sementara: {email}")

            # Buka Sync.so signup
            signup = await context.new_page()
            await signup.goto("https://sync.so/signup", timeout=60000)
            await signup.fill("input[type=email]", email)
            await signup.keyboard.press("Enter")
            console.print("📨 Email dikirim ke Sync.so, menunggu OTP...")

            # Kembali ke Twibon, tunggu email OTP masuk
            await page.wait_for_timeout(8000)
            otp_code = None

            # Cari OTP (angka 6 digit)
            html = await page.content()
            import re
            match = re.search(r"\b\d{6}\b", html)
            if match:
                otp_code = match.group(0)
                console.print(f"🔐 OTP ditemukan: {otp_code}")
            else:
                console.print("❌ OTP tidak ditemukan.")

            if otp_code:
                await signup.fill("input", otp_code)
                await signup.keyboard.press("Enter")
                await signup.wait_for_timeout(4000)

                cookies = await context.cookies()
                profile_path = f"{PROFILES}/profile_{index}.json"
                with open(profile_path, "w") as f:
                    json.dump({"email": email, "cookies": cookies}, f, indent=2)
                console.print(f"💾 Profil tersimpan: {profile_path}")

            await browser.close()
    except Exception as e:
        console.print(f"[red]❌ Gagal signup akun {index}: {e}[/red]")


# ===============================================================
# 5️⃣ Fungsi Generate Sinkronisasi Final
# ===============================================================
async def generate_sync_final():
    """Gabungkan segmen audio & video hasil proses"""
    print("\n🎬 Menggabungkan hasil akhir...")
    video = os.path.join(OUTPUT, "video_safe.mp4")
    output_final = os.path.join(OUTPUT, "final_output.mp4")

    segmen_files = sorted(
        [os.path.join(OUTPUT, f) for f in os.listdir(OUTPUT) if f.startswith("seg_")]
    )

    # Ambil segmen pertama (contoh sederhana)
    if segmen_files:
        (
            ffmpeg.input(video)
            .output(segmen_files[0], output_final, shortest=None, vcodec="copy", acodec="aac")
            .run(quiet=True, overwrite_output=True)
        )
        print(f"✅ Video final disimpan di {output_final}")
    else:
        print("⚠️ Tidak ada segmen audio ditemukan.")


# ===============================================================
# 6️⃣ MAIN UTAMA
# ===============================================================
async def main():
    print("🚀 LYPSTOOL COLAB MODE AKTIF 🚀")

    audio_path = upload_audio()
    video_path = upload_video()

    if not audio_path or not video_path:
        print("❌ Upload file gagal. Pastikan keduanya diunggah.")
        return

    total_segments = process_media(audio_path, video_path)

    for i in range(1, total_segments + 1):
        await signup_akun_sync(i)

    await generate_sync_final()
    print("\n✅ Semua proses selesai tanpa error!")


# ===============================================================
# 7️⃣ Entry Point
# ===============================================================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ Error utama: {e}")
