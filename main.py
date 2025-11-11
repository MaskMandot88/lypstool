# ============================================================
# main.py — Full Color (Rich) wrapper around the original logic
# (Behavior unchanged; only console output/styling changed)
# ============================================================

import os
import subprocess
import sys
from tkinter import Tk, filedialog
from pydub import AudioSegment, silence
import shutil
import builtins
from datetime import datetime

# --- rich console for colored output ---
try:
    from rich.console import Console
    console = Console()
except Exception:
    console = None

# Enhanced log function (keperluan konsistensi)
def log(msg: str, color: str = "white", emoji: str = None):
    time_str = datetime.now().strftime("%H:%M:%S")
    prefix = f"{emoji} " if emoji else ""
    if console:
        console.print(f"[{time_str}] {prefix}[{color}]{msg}[/{color}]")
    else:
        builtins.print(f"[{time_str}] {prefix}{msg}")

# Override built-in print so all old prints use rich styling
_original_print = builtins.print
def _rich_print(*args, **kwargs):
    txt = " ".join(str(a) for a in args)
    if console:
        console.print(txt)
    else:
        _original_print(txt)
builtins.print = _rich_print

# -----------------------
# Original main.py content below (unchanged logic)
# -----------------------

# Fungsi untuk memilih file
def pilih_file_audio():
    Tk().withdraw()  # Menyembunyikan jendela utama Tkinter
    file_audio = filedialog.askopenfilename(title="Pilih file audio", filetypes=[("Audio Files", "*.wav *.mp3")])
    return file_audio

def pilih_file_video():
    Tk().withdraw()  # Menyembunyikan jendela utama Tkinter
    file_video = filedialog.askopenfilename(title="Pilih file video", filetypes=[("Video Files", "*.mp4 *.avi *.mov")])
    return file_video

# Fungsi untuk reset folder input, output, dan profiles
def reset_folders():
    """Menghapus isi folder input, output, dan profiles."""
    folders = [INPUT, OUTPUT, PROFILES]
    for folder in folders:
        if os.path.exists(folder):
            print(f"🧹 Menghapus isi folder: {folder}")
            for file_name in os.listdir(folder):
                file_path = os.path.join(folder, file_name)
                try:
                    if os.path.isdir(file_path):
                        shutil.rmtree(file_path)  # Menghapus folder beserta isinya
                    else:
                        os.remove(file_path)  # Menghapus file
                    print(f"✅ Dihapus: {file_path}")
                except Exception as e:
                    print(f"⚠️ Gagal menghapus {file_path}: {e}")
        else:
            os.makedirs(folder, exist_ok=True)  # Membuat folder jika tidak ada
            print(f"ℹ️ Folder {folder} tidak ada, membuat folder baru.")

# --- Path Absolut ---
BASE = os.path.dirname(os.path.abspath(__file__))
INPUT = os.path.join(BASE, "input")
OUTPUT = os.path.join(BASE, "output")
PROFILES = os.path.join(BASE, "profiles")
os.makedirs(INPUT, exist_ok=True)
os.makedirs(OUTPUT, exist_ok=True)
os.makedirs(PROFILES, exist_ok=True)

# Fungsi untuk memotong audio
def slice_audio(AUDIO_FILE):
    try:
        if not os.path.exists(AUDIO_FILE):
            print(f"⚠️ File audio tidak ditemukan: {AUDIO_FILE}")
            return 0

        print(f"🎧 Memotong {AUDIO_FILE} (mencari jeda)...")
        audio = AudioSegment.from_wav(AUDIO_FILE)
        
        chunk_target_ms = 59 * 1000  # target 59 detik
        silence_search_back_ms = 8000  # maksimal mundur 8 detik untuk cari jeda
        min_silence_len = 500  # 0.5 detik jeda
        silence_thresh = -45  # threshold dB (atur sesuai audio)
        
        pos = 0
        i = 1
        total_segments = 0
        
        while pos < len(audio):
            target_end = pos + chunk_target_ms
            if target_end > len(audio):
                target_end = len(audio)
            
            segment_to_check = audio[pos:target_end]
            
            silences = silence.detect_silence(
                segment_to_check,
                min_silence_len=min_silence_len,
                silence_thresh=silence_thresh
            )
            
            cut_point_absolute = target_end  # fallback = potong paksa di target
            
            if silences:
                start_silence, end_silence = silences[-1]
                if end_silence >= (len(segment_to_check) - silence_search_back_ms):
                    cut_point_absolute = pos + end_silence 

            if target_end == len(audio):
                cut_point_absolute = len(audio)
            
            if cut_point_absolute <= pos:
                if target_end == len(audio):
                    break
                else:
                    cut_point_absolute = target_end

            final_segment = audio[pos:cut_point_absolute]
            output_path = os.path.join(OUTPUT, f"seg_{i:02d}.mp3")
            final_segment.export(output_path, format="mp3")
            print(f"✅ dibuat: {output_path} (Durasi: {len(final_segment)/1000.0}s)")
            
            total_segments += 1
            pos = cut_point_absolute
            i += 1
            if pos == len(audio):
                break

        print(f"\nTotal potongan audio: {total_segments}")
        return total_segments 
        
    except Exception as e:
        print(f"❌ Gagal memotong audio: {e}")
        return 0 

# Fungsi untuk mengonversi video
def convert_video(RAW_VIDEO_FILE):
    SAFE_VIDEO = os.path.join(INPUT, "video_safe.mp4")
    if not os.path.exists(RAW_VIDEO_FILE):
        print(f"⚠️ Tidak ada {RAW_VIDEO_FILE} untuk dikonversi.")
        return False
    
    if os.path.exists(SAFE_VIDEO):
        print(f"ℹ️ {SAFE_VIDEO} sudah ada, skip konversi.")
        return True
        
    print(f"🎞️ Mengonversi {RAW_VIDEO_FILE} ke format aman (H.264 + AAC)...")
    cmd = [
        "ffmpeg", "-y", "-i", RAW_VIDEO_FILE,
        "-vf", "scale=1280:-2,fps=30,format=yuv420p",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        SAFE_VIDEO
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"✅ Video dikonversi aman: {SAFE_VIDEO}")
        return True
    except Exception as e:
        print(f"❌ Gagal konversi video dengan FFmpeg: {e}")
        return False

def main():
    print("=== START main.py ===")

    # Reset folder input, output, dan profiles
    reset_folders()

    # Memilih file audio dan video dari pengguna
    AUDIO_FILE = pilih_file_audio()
    RAW_VIDEO_FILE = pilih_file_video()

    if not AUDIO_FILE or not RAW_VIDEO_FILE:
        print("❌ Proses dihentikan karena file audio atau video tidak dipilih.")
        return

    # 1. Potong audio
    total_segments = slice_audio(AUDIO_FILE)
    
    if total_segments == 0:
        print("❌ Proses dihentikan karena audio gagal dipotong.")
        return
        
    # 2. Konversi Video
    if not convert_video(RAW_VIDEO_FILE):
        print("❌ Proses dihentikan karena video gagal dikonversi.")
        return

    # 3. Lanjutkan ke proses sign-up
    print("\n➡️ Melanjutkan ke proses sign-up...")
    try:
        # Jalankan menggunakan command `py -3.11` untuk menjalankan skrip
        result = subprocess.run(["py", "-3.11", "signup_terminal_input.py"], check=True)
        print("➡️ Proses sign-up selesai!")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Gagal menjalankan signup_terminal_input.py. Proses dihentikan. Error: {e}")
    except FileNotFoundError:
        print("❌ File 'signup_terminal_input.py' tidak ditemukan.")
    
    print("\n➡️ Proses selesai!")

if __name__ == "__main__":
    main()
