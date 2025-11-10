import os, glob, time, subprocess, sys, shutil, platform
from datetime import datetime
from playwright.sync_api import sync_playwright

# --- Auto install moviepy jika belum ada ---
try:
    from moviepy.editor import VideoFileClip, concatenate_videoclips
except Exception:
    print("📦 Installing moviepy ...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "moviepy==1.0.3"])
    from moviepy.editor import VideoFileClip, concatenate_videoclips

# --- Simple colored logs ---
def green(t): return f"\033[92m{t}\033[0m"
def yellow(t): return f"\033[93m{t}\033[0m"
def red(t): return f"\033[91m{t}\033[0m"
def blue(t): return f"\033[94m{t}\033[0m"

# --- Paths ---
BASE = os.path.dirname(os.path.abspath(__file__))
INPUT = os.path.join(BASE, "input")
OUTPUT = os.path.join(BASE, "output")
PROFILES = os.path.join(BASE, "profiles")
SAFE_VIDEO = os.path.join(INPUT, "video_safe.mp4")

for f in [INPUT, OUTPUT, PROFILES]:
    os.makedirs(f, exist_ok=True)

os.environ["PLAYWRIGHT_DOWNLOADS_PATH"] = OUTPUT  # all downloads to output/

# --- Beep helper ---
def beep():
    try:
        if platform.system() == "Windows":
            import winsound
            winsound.Beep(880, 300)
        else:
            print("\a", end="")
    except:
        pass

# --- Highlight + robust click ---
def highlight_and_click(page, locator, click=True, selector_str=None):
    """Highlight + safe click (re-locate + JS fallback)."""
    try:
        el = locator.element_handle(timeout=5000)
        if not el and selector_str:
            locator = page.locator(selector_str)
            el = locator.element_handle(timeout=5000)
        if not el:
            print(yellow("⚠️ Elemen tidak ditemukan untuk diklik."))
            return False

        page.evaluate("""
            (el)=>{
                el.style.outline='3px solid lime';
                el.style.transition='outline 0.3s ease';
                setTimeout(()=>el.style.outline='',1500);
            }""", el)
        time.sleep(0.3)

        if click:
            try:
                locator.scroll_into_view_if_needed(timeout=3000)
                locator.click(timeout=3000)
                print(green("✅ Klik berhasil (normal)."))
            except Exception as e:
                print(yellow(f"⚠️ Klik normal gagal ({e}), mencoba klik via JS..."))
                try:
                    page.evaluate("(el)=>el.click()", el)
                    print(green("✅ Klik berhasil (via JavaScript)."))
                except Exception as e2:
                    print(red(f"❌ Klik gagal total: {e2}"))
                    return False
        return True
    except Exception as e:
        print(red(f"⚠️ highlight_and_click gagal total: {e}"))
        return False

# --- Video check ---
def convert_video():
    if not os.path.exists(SAFE_VIDEO):
        print(red(f"⚠️ {SAFE_VIDEO} tidak ditemukan. Jalankan main.py dulu."))
        return False
    print(blue(f"ℹ️ {SAFE_VIDEO} ditemukan."))
    return True

# --- Buka project (auto retry + multi selector) ---
def open_existing_project(page):
    print(blue("📂 Mencari project card pertama..."))
    time.sleep(2)
    try:
        page.wait_for_load_state("domcontentloaded", timeout=30000)
        card = page.locator("a[href*='/projects/']").first
        card.wait_for(state="visible", timeout=10000)
        print(green("✅ Project card ditemukan. Mengklik..."))
        highlight_and_click(page, card)
        print(blue("⏳ Menunggu halaman studio terbuka (max 90 detik)..."))

        selectors = [
            "button:has-text('upload audio')",
            "button:has-text('add audio')",
            "button:has-text('import audio')",
            "button:has-text('lipsync')",
            "button:has-text('generate')",
            "video"
        ]

        for attempt in range(3):
            for sel in selectors:
                if page.locator(sel).count() > 0:
                    print(green(f"✅ Halaman studio aktif (terdeteksi: {sel})"))
                    return True
            print(yellow(f"⚠️ Studio belum siap (percobaan {attempt+1}/3), scroll & tunggu..."))
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(10)

        print(red("❌ Tidak bisa memastikan halaman studio aktif."))
        page.screenshot(path=f"output/debug_studio_notready_{datetime.now().strftime('%H%M%S')}.png")
        return False

    except Exception as e:
        print(red(f"❌ Tidak bisa membuka project: {e}"))
        page.screenshot(path=f"output/debug_open_project_fail_{datetime.now().strftime('%H%M%S')}.png")
        return False

# --- Upload video & audio (tidak diubah) ---
def upload_media(page, audio_path, idx):
    print(blue("📤 Memulai upload video & audio..."))
    try:
        html = page.content().lower()
        if "<video" in html:
            print(yellow("ℹ️ Video sudah terpasang, skip upload video."))
        else:
            drop_candidates = [
                "div:has-text('choose a video to edit')",
                "div:has-text('choose video')",
                "div:has-text('upload video')",
            ]
            dropzone = None
            for sel in drop_candidates:
                loc = page.locator(sel)
                if loc.count() > 0:
                    dropzone = loc.first
                    print(green(f"✅ Area upload ditemukan: {sel}"))
                    break
            if not dropzone:
                raise Exception("Tidak menemukan area upload video.")
            dropzone.hover(force=True)
            time.sleep(1.5)
            upload_btn = page.get_by_text("upload", exact=False).first
            with page.expect_file_chooser() as fc_info:
                highlight_and_click(page, upload_btn)
            fc_info.value.set_files(SAFE_VIDEO)
            page.wait_for_selector("video", timeout=180000)  # Meningkatkan waktu tunggu menjadi 3 menit
            print(green("✅ Upload video berhasil!"))
    except Exception as e:
        print(red(f"❌ Gagal upload video: {e}"))
        page.screenshot(path=f"output/debug_video_upload_fail_{idx+1}_{datetime.now().strftime('%H%M%S')}.png")
        return False

    print(blue("🕒 Menunggu 10 detik sebelum upload audio..."))
    time.sleep(10)
    try:
        audio_btn = page.get_by_text("upload audio", exact=False).first
        with page.expect_file_chooser() as fc_audio:
            highlight_and_click(page, audio_btn)
        fc_audio.value.set_files(audio_path)
        print(green(f"✅ Audio diunggah: {audio_path}"))
        page.wait_for_selector("button", state="visible", timeout=120000)
        print(green("✅ Tombol Lipsync siap."))
    except Exception as e:
        print(red(f"❌ Upload audio gagal: {e}"))
        page.screenshot(path=f"output/debug_audio_upload_fail_{idx+1}_{datetime.now().strftime('%H%M%S')}.png")
        return False
    return True

# --- Klik tombol Lipsync ---
def click_lipsync(page):
    print(blue("🎬 Mencari dan mengklik tombol 'Lipsync'..."))
    try:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(3)

        for _ in range(10):
            if page.locator("#generate-button-lite-view").count() > 0:
                print(green("✅ Tombol Lipsync ditemukan via ID."))
                btn = page.locator("#generate-button-lite-view").first
                highlight_and_click(page, btn, selector_str="#generate-button-lite-view")
                time.sleep(1.5)
                highlight_and_click(page, btn, selector_str="#generate-button-lite-view")
                break
            print(yellow("⏳ Tombol belum muncul, tunggu 2 detik..."))
            time.sleep(2)

        print(blue("🕒 Menunggu tanda 'processing'..."))
        for _ in range(20):
            if "processing" in page.content().lower():
                print(green("✅ Proses Lipsync dimulai."))
                return True
            time.sleep(1)
        print(red("❌ Tidak muncul tanda 'processing'."))

        return False
    except Exception as e:
        print(red(f"❌ Gagal klik tombol Lipsync: {e}"))
        return False

# --- Download hasil (Smart + Manual Auto Rename) ---
def monitor_and_download(ctx, page, idx):
    print(blue(f"[{idx+1}] Menunggu 'processing' selesai..."))
    try:
        page.wait_for_selector("text=processing", state="detached", timeout=0)
        print(green(f"✅ [Profile {idx+1}] Rendering selesai."))
        time.sleep(5)

        selector_download = "button[data-sentry-source-file='download-button.tsx']"
        print(blue(f"[{idx+1}] Mencari tombol download (ikon SVG)..."))

        for i in range(30):
            if page.locator(selector_download).count() > 0:
                print(green(f"✅ Tombol download ditemukan (percobaan {i+1})."))
                break
            print(yellow(f"⏳ Menunggu tombol download muncul... ({i+1}/30)"))
            time.sleep(2)
        else:
            print(red("❌ Tidak menemukan tombol download setelah 60 detik."))
            ts = datetime.now().strftime("%H%M%S")
            page.screenshot(path=f"output/debug_download_notfound_{idx+1}_{ts}.png")
            return

        download_btn = page.locator(selector_download).first

        try:
            with page.expect_download() as dl_info:
                download_btn.click()
            download = dl_info.value
            download.save_as(os.path.join(OUTPUT, f"result_seg_{idx+1:02d}.mp4"))
            print(green(f"✅ [Profile {idx+1}] Download selesai: result_seg_{idx+1:02d}.mp4"))
            beep()

        except Exception as e:
            print(yellow(f"⚠️ Gagal auto-detect download: {e}"))
            try:
                page.evaluate("(el)=>el.click()", download_btn.element_handle())
                print(green("✅ Klik JS berhasil. Tunggu beberapa detik..."))
                time.sleep(15)
                beep()
            except Exception as e2:
                print(red(f"❌ Klik JS juga gagal: {e2}"))
                ts = datetime.now().strftime("%H%M%S")
                page.screenshot(path=f"output/debug_download_fail_{idx+1}_{ts}.png")

                # --- Manual click + Auto Rename ---
                print(yellow("👉 Silakan klik tombol download secara manual di browser."))
                before_files = set(os.listdir(OUTPUT))
                input("⏸ Tekan ENTER setelah file selesai diunduh...")
                after_files = set(os.listdir(OUTPUT))
                new_files = list(after_files - before_files)

                if not new_files:
                    print(red("⚠️ Tidak menemukan file baru di folder output."))
                else:
                    new_file = new_files[0]
                    old_path = os.path.join(OUTPUT, new_file)
                    new_path = os.path.join(OUTPUT, f"result_seg_{idx+1:02d}.mp4")
                    os.rename(old_path, new_path)
                    print(green(f"✅ File {new_file} otomatis diubah menjadi {new_path}"))
                    beep()

    except Exception as e:
        print(red(f"⚠️ [Profile {idx+1}] Error monitor download: {e}"))
        ts = datetime.now().strftime("%H%M%S")
        page.screenshot(path=f"output/debug_download_error_{idx+1}_{ts}.png")
    finally:
        try:
            ctx.close()
        except:
            pass

# --- Gabung video ---
def merge_videos():
    vids = sorted(glob.glob(os.path.join(OUTPUT, "result_seg_*.mp4")))
    if not vids:
        print(yellow("⚠️ Tidak ada video untuk digabung."))
        return
    print(blue(f"🎬 Menggabungkan {len(vids)} video..."))
    clips = [VideoFileClip(v) for v in vids]
    final = concatenate_videoclips(clips, method="compose")
    base = os.path.join(OUTPUT, "final_combined.mp4")
    i = 1
    while os.path.exists(base):
        base = os.path.join(OUTPUT, f"final_combined_{i}.mp4")
        i += 1
    final.write_videofile(base, codec="libx264", audio_codec="aac")
    print(green(f"✅ Final tersimpan di: {base}"))
    beep()

# --- Reset folder ---
def reset_folders():
    print(blue("🧹 Membersihkan folder proyek..."))
    for folder in [INPUT, OUTPUT, PROFILES]:
        for item in os.listdir(folder):
            path = os.path.join(folder, item)
            if "video_safe" in item or "final_combined" in item:
                continue
            try:
                if os.path.isfile(path): os.remove(path)
                else: shutil.rmtree(path)
            except: pass
    print(green("✅ Folder bersih."))

# --- Main ---
def main():
    print(blue("=== START generate_sync_final_v148_manual_autorename ==="))
    if not convert_video(): return
    audio_files = sorted(glob.glob(os.path.join(OUTPUT, "seg_*.mp3")))
    if not audio_files:
        print(red("⚠️ Tidak ada file segmen audio di folder output/.")) 
        return

    with sync_playwright() as pw:
        sessions = []
        for i, audio in enumerate(audio_files):
            profile = os.path.join(PROFILES, f"profile_{i+1:02d}")
            if not os.path.exists(profile):
                print(yellow(f"⚠️ Profil {profile} tidak ditemukan."))
                continue
            print(blue(f"\n=== [Profile {i+1}] ==="))
            ctx = pw.chromium.launch_persistent_context(
                user_data_dir=profile, headless=True, accept_downloads=True
            )
            page = ctx.new_page()
            page.goto("https://sync.so/projects", timeout=60000)

            if not open_existing_project(page): ctx.close(); continue
            if not upload_media(page, audio, i): ctx.close(); continue
            if not click_lipsync(page): ctx.close(); continue

            sessions.append((ctx, page, i))
            print(green(f"✅ Profil {i+1} siap untuk download."))

        print(blue("\n--- MONITORING & DOWNLOAD ---"))
        for ctx, page, idx in sessions:
            monitor_and_download(ctx, page, idx)

    merge_videos()
    ans = input("Ingin reset folder input/output/profiles? (y/n): ").lower()
    if ans == "y": reset_folders()

if __name__ == "__main__":
    main()
