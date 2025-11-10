import os, glob, time, re, sys, shutil, subprocess
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# 🎨 Tambahkan warna & emoji dengan rich
try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
except ImportError:
    os.system("pip install rich")
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

console = Console()

# ============================================================
# Konfigurasi & Konstanta
# ============================================================

BASE = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(BASE, "output")
PROFILES = os.path.join(BASE, "profiles")
MAIL_URL = "https://zanmail.co-id.id/"
SIGNUP_URL = "https://sync.so/signup"


OTP_TIMEOUT = 180
OTP_CHECK_INTERVAL = 2

# ============================================================
# Fungsi Log Berwarna
# ============================================================

def log(msg, color="white", emoji=None, style=None):
    """Menampilkan log dengan warna, emoji, dan waktu."""
    time_str = datetime.now().strftime("%H:%M:%S")
    prefix = f"{emoji} " if emoji else ""
    if style:
        console.print(f"[{time_str}] {prefix}[{color}][{style}]{msg}[/{style}][/{color}]")
    else:
        console.print(f"[{time_str}] {prefix}[{color}]{msg}[/{color}]")

# ============================================================
# FUNGSI MAIL.TWIBON
# ============================================================

def extract_otp_from_page(page):
    try:
        spans = page.locator("div.prose.max-w-none span")
        digits = []
        for i in range(spans.count()):
            txt = spans.nth(i).inner_text().strip()
            if txt.isdigit():
                digits.append(txt)
        otp = "".join(digits)
        return otp if otp else None
    except Exception:
        return None

def wait_and_click_sync_email(page, timeout=OTP_TIMEOUT):
    log("Menunggu email baru dari Sync.so...", "yellow", "⏳")
    end_time = time.time() + timeout

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("📬 Cek inbox zan mail...", total=None)

        while time.time() < end_time:
            try:
                sync_msg = page.locator("div.space-y-2.max-h-96.overflow-y-auto div:has-text('sync')")
                if sync_msg.count() > 0:
                    sync_msg.first.click()
                    log("Pesan dari Sync.so ditemukan dan diklik.", "green", "📩")
                    return True
            except Exception:
                pass
            time.sleep(OTP_CHECK_INTERVAL)

    log("Tidak ada pesan dari Sync.so setelah waktu tunggu habis.", "red", "❌")
    return False

def get_current_email(page):
    try:
        page.wait_for_selector("code.text-lg.font-mono.text-indigo-600", timeout=30000)
        return page.locator("code.text-lg.font-mono.text-indigo-600").first.inner_text().strip()
    except Exception:
        return None

def reset_email(page):
    try:
        log("Reset email...", "cyan", "🔁")
        page.click("button.bg-red-500", timeout=5000)
        page.wait_for_timeout(2000)
        new_email = get_current_email(page)
        if new_email:
            log(f"Email baru: {new_email}", "green", "✅")
        else:
            log("Gagal mendapatkan email baru.", "yellow", "⚠️")
        return new_email
    except Exception as e:
        log(f"Gagal reset email: {e}", "red", "⚠️")
        return None

def check_invalid_email(signup_page):
    try:
        err = signup_page.locator("text=Invalid email address")
        return err.count() > 0 and err.first.is_visible()
    except Exception:
        return False

# ============================================================
# PROSES SIGNUP DAN LOGIN
# ============================================================

def signup_accounts():
    os.makedirs(PROFILES, exist_ok=True)
    audio_files = sorted(glob.glob(os.path.join(OUTPUT, "seg_*.mp3")))
    if not audio_files:
        log("Tidak ada file audio di output/.", "yellow", "⚠️")
        return False

    console.rule("[bold cyan]🌍 MEMBUAT AKUN SYNC.SO OTOMATIS[/bold cyan]")

    try:
        with sync_playwright() as pw:
            for i, _ in enumerate(audio_files, start=1):
                console.rule(f"[bold magenta]Akun {i}[/bold magenta]")
                profile_dir = os.path.join(PROFILES, f"profile_{i:02d}")

                if os.path.isdir(profile_dir):
                    shutil.rmtree(profile_dir, ignore_errors=True)
                os.makedirs(profile_dir, exist_ok=True)

                ctx = pw.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    headless=True,
                    accept_downloads=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"]
                )

                mail_page = ctx.new_page()
                mail_page.goto(MAIL_URL, timeout=60000, wait_until="load")
                email = get_current_email(mail_page)
                if not email:
                    log("Email tidak terbaca.", "yellow", "⚠️")
                    ctx.close()
                    continue
                log(f"Email: {email}", "green", "📧")

                signup_page = ctx.new_page()
                signup_page.goto(SIGNUP_URL, timeout=60000, wait_until="load")
                signup_page.fill("input[type=email]", email)
                signup_page.keyboard.press("Enter")
                log("Email dikirim ke Sync.so", "cyan", "📨")

                time.sleep(3)
                if check_invalid_email(signup_page):
                    log("Email invalid, reset...", "red", "❌")
                    new_email = reset_email(mail_page)
                    if not new_email:
                        ctx.close()
                        continue
                    signup_page.fill("input[type=email]", new_email)
                    signup_page.keyboard.press("Enter")
                    email = new_email

                found = wait_and_click_sync_email(mail_page)
                otp = None
                if found:
                    start = time.time()
                    with Progress(SpinnerColumn(), TextColumn("Menunggu OTP..."), TimeElapsedColumn(), console=console, transient=True) as progress:
                        task = progress.add_task("waiting", total=None)
                        while time.time() - start < OTP_TIMEOUT:
                            otp = extract_otp_from_page(mail_page)
                            if otp:
                                break
                            time.sleep(1)
                if not otp:
                    otp = input("Masukkan OTP manual (atau skip): ").strip()
                    if not otp or otp.lower() == "skip":
                        log("Proses signup gagal. Melakukan login manual.", "red", "❌")
                        manual_login(ctx)  # Menambahkan login manual jika signup gagal
                        ctx.close()
                        continue

                log(f"OTP: {otp}", "yellow", "🔐")
                otp_input = signup_page.locator("input").first
                otp_input.fill(otp)
                otp_input.press("Enter")

                signup_page.wait_for_url("**/studio**", timeout=60000, wait_until="load")
                log("Login berhasil!", "green", "🎉")

                ctx.close()
                log(f"Profil {i} selesai disimpan ({profile_dir})", "green", "✅")

    except Exception as e:
        log(f"ERROR: {e}", "bold red", "💥")
        return False

    console.rule("[bold green]🎉 Semua akun berhasil dibuat![/bold green]")
    return True

# ============================================================
# Fungsi Login Manual jika Signup Gagal
# ============================================================

def manual_login(ctx):
    """Fungsi untuk login manual menggunakan email dan OTP yang dimasukkan oleh pengguna di terminal."""
    print("💬 Masukkan email dan OTP secara manual untuk login.")
    email = input("Masukkan Email: ").strip()
    otp = input("Masukkan OTP: ").strip()

    try:
        signup_page = ctx.new_page()
        signup_page.goto(SIGNUP_URL, timeout=60000, wait_until="load")
        signup_page.fill("input[type=email]", email)
        signup_page.keyboard.press("Enter")
        time.sleep(3)

        otp_input = signup_page.locator("input").first
        otp_input.fill(otp)
        otp_input.press("Enter")

        signup_page.wait_for_url("**/studio**", timeout=60000, wait_until="load")
        log("Login manual berhasil!", "green", "🎉")
    except Exception as e:
        log(f"Login manual gagal: {e}", "red", "❌")

# ============================================================
# EKSEKUSI UTAMA
# ============================================================

if __name__ == "__main__":
    if signup_accounts():
        log("Jalankan generate_sync_final.py ...", "cyan", "➡️")
        try:
            subprocess.run([sys.executable, os.path.join(BASE, "generate_sync_final.py")])
        except Exception as e:
            log(f"Gagal menjalankan generate_sync_final.py: {e}", "red", "⚠️")
    else:
        log("Signup gagal.", "red", "❌")
    log("Selesai.", "cyan", "✅")
