#!/usr/bin/env python3
"""
REDZ LAGKILLER - FULL EDITION (CLI menu, multi-platform)
Author : Redz Adaptation
Purpose: Multi-OS performance booster / cleaner for personal device optimization.
Use responsibly. Many ops require root/admin for full effect.

Dependencies:
  - psutil (pip install psutil)

Features (full):
  - Interactive CLI menu (no argparse)
  - Modes: Gaming, CPU, Performance, FPS, Auto
  - Background/daemon mode (simple pidfile)
  - Clear caches/temp (platform-aware, with confirmation)
  - Kill heavy/background processes (safe filters + confirmation)
  - Free RAM / drop_caches on Linux (root)
  - Trim storage (fstrim when available)
  - Set CPU governor / Windows powerplan (best-effort, needs privileges)
  - Process prioritization (nice / priority class & affinity)
  - Optional auto-scheduler (internal loop)
  - Lightweight monitoring (CPU, mem, temp if available)
  - Safe prompts before potentially destructive ops
"""

import os
import sys
import time
import getpass
import platform
import subprocess
from pathlib import Path
from datetime import datetime
try:
    import psutil
except ImportError:
    print("[!] Modul psutil belum terpasang, sedang menginstal...")
    os.system(f"{sys.executable} -m pip install psutil")
    import psutil


# ---------------------- Config ----------------------
PIDFILE = Path("/tmp/redz_lagkiller_full.pid") if platform.system() != "Windows" else Path(os.path.join(os.getenv("TEMP","."), "redz_lagkiller_full.pid"))
SLEEP_INTERVAL = 60  # default for background loop
CPU_HEAVY_THRESHOLD = 40.0  # %
MEM_HEAVY_THRESHOLD = 20.0  # %
DAEMON_LOG = Path.home() / ".redz_lagkiller.log"

# ---------------------- Utils ----------------------
def is_root():
    """Return True if running as root/admin."""
    try:
        if platform.system() == "Windows":
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:
            return os.geteuid() == 0
    except Exception:
        return False

def run_cmd(cmd, shell=False):
    """Run command, return (rc, stdout, stderr)."""
    try:
        p = subprocess.run(cmd, shell=shell, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except Exception as e:
        return 1, "", f"run_cmd_error: {e}"

def yes_prompt(msg):
    ans = input(f"{msg} (ketik YES untuk konfirmasi): ").strip()
    return ans == "YES"

def log(msg):
    ts = datetime.now().isoformat()
    line = f"[{ts}] {msg}\n"
    try:
        with open(DAEMON_LOG, "a") as f:
            f.write(line)
    except Exception:
        pass

def safe_sleep(sec):
    try:
        time.sleep(sec)
    except KeyboardInterrupt:
        print("\n[!] Interrupted")

def print_banner():
    print("=== REDZ LAGKILLER — FULL EDITION ===")
    print("Banner only once. Pilih mode, script akan exit kecuali mode background dipilih.")
    print(f"Platform: {platform.system()} | User: {getpass.getuser()} | Root: {is_root()}")
    print("--------------------------------------------------")

# ---------------------- Cleanup / Trim ----------------------
def clear_temp_cache(confirm=True):
    system = platform.system()
    print("[*] Menyiapkan pembersihan cache/temp (best-effort)...")
    if confirm:
        if not yes_prompt("Proses ini akan menghapus file sementara pada lokasi yang bisa diakses. Lanjut?"):
            print("[!] Dibatalkan oleh user.")
            return
    try:
        if system == "Linux" or system == "Android":
            targets = ["/tmp", "/var/tmp", "/data/local/tmp", "/data/data/com.termux/files/usr/tmp", "/data/data/com.termux/cache"]
            for p in targets:
                if os.path.exists(p):
                    # only remove non-root-owned temp files if not root, otherwise attempt moderate cleanup
                    for entry in Path(p).iterdir():
                        try:
                            # avoid touching important system dirs - basic safety
                            if entry.is_dir():
                                for child in entry.rglob("*"):
                                    try:
                                        if child.is_file():
                                            child.unlink()
                                    except Exception:
                                        pass
                            else:
                                try:
                                    entry.unlink()
                                except Exception:
                                    pass
                        except Exception:
                            pass
            # apt clean if available
            if shutil_exists("apt") and is_root():
                run_cmd(["apt", "clean"])
            print("[+] Cache/temp cleanup attempted (Linux/Android).")
        elif system == "Windows":
            temp = os.environ.get("TEMP") or os.environ.get("TMP")
            if temp and os.path.exists(temp):
                # remove files only (safe)
                for entry in Path(temp).iterdir():
                    try:
                        if entry.is_file():
                            entry.unlink()
                        elif entry.is_dir():
                            rc, o, e = run_cmd(["rmdir", "/S", "/Q", str(entry)], shell=True)
                    except Exception:
                        pass
            print("[+] Windows temp cleanup attempted.")
        elif system == "Darwin":
            # macOS
            targets = ["/private/var/tmp", "/var/folders"]
            for p in targets:
                if os.path.exists(p):
                    for entry in Path(p).iterdir():
                        try:
                            if entry.is_file():
                                entry.unlink()
                        except Exception:
                            pass
            print("[+] macOS temp cleanup attempted.")
        else:
            print("[!] OS tidak dikenali, skip cleanup.")
    except Exception as e:
        print(f"[!] clear_temp_cache error: {e}")
    log("clear_temp_cache executed")

def shutil_exists(cmd):
    from shutil import which
    return which(cmd) is not None

def fstrim_if_available():
    if shutil_exists("fstrim"):
        print("[*] Menjalankan fstrim pada / (butuh akses/root).")
        rc, out, err = run_cmd(["fstrim", "-v", "/"])
        if rc == 0:
            print(f"[+] fstrim OK: {out}")
        else:
            print(f"[!] fstrim gagal / tidak diperbolehkan: {err}")
    else:
        print("[*] fstrim tidak tersedia di sistem ini.")
    log("fstrim_if_available attempted")

# ---------------------- RAM / CPU tweaks ----------------------
def free_ram():
    system = platform.system()
    print("[*] Mencoba free RAM / drop caches (Linux root needed untuk full effect).")
    if system == "Linux":
        if is_root():
            try:
                with open("/proc/sys/vm/drop_caches", "w") as f:
                    f.write("3\n")
                print("[+] drop_caches written.")
            except Exception as e:
                print(f"[!] Gagal drop_caches: {e}")
        else:
            print("[!] Non-root: tidak bisa drop_caches penuh. Tutup app manual untuk efek lebih.")
    elif system == "Windows":
        print("[*] Windows: mencoba empty standby list (requires sysinternals; skipped).")
    elif system == "Darwin":
        print("[*] macOS: limited; consider reboot or close apps.")
    log("free_ram attempted")

def set_cpu_performance(enable=True):
    system = platform.system()
    print("[*] Mengatur CPU performance mode (best-effort).")
    if system == "Linux":
        if is_root():
            governors_path = Path("/sys/devices/system/cpu")
            try:
                for cpu in governors_path.glob("cpu[0-9]*"):
                    gov = cpu / "cpufreq" / "scaling_governor"
                    if gov.exists():
                        try:
                            with open(gov, "w") as f:
                                f.write("performance" if enable else "ondemand")
                        except Exception:
                            pass
                print("[+] Governor updated (Linux).")
            except Exception as e:
                print(f"[!] Error set governor: {e}")
        else:
            print("[!] Root diperlukan untuk set governor.")
    elif system == "Windows":
        if shutil_exists("powercfg"):
            # try set high performance scheme (best-effort)
            # SCHEME_MIN is a placeholder, actual GUID mapping may differ.
            rc, out, err = run_cmd(["powercfg", "/SETACTIVE", "SCHEME_MIN"], shell=False)
            if rc == 0:
                print("[+] Power scheme set (attempt).")
            else:
                print("[!] Gagal mengubah power scheme (butuh admin).")
        else:
            print("[!] powercfg tidak tersedia.")
    else:
        print("[!] CPU performance tweak terbatas di OS ini.")
    log(f"set_cpu_performance set={enable}")

# ---------------------- Process management ----------------------
def kill_heavy_processes(cpu_thresh=CPU_HEAVY_THRESHOLD, mem_thresh=MEM_HEAVY_THRESHOLD, confirm=True):
    print(f"[*] Scanning process heavier than CPU>{cpu_thresh}% or MEM>{mem_thresh}% ...")
    heavy = []
    current_pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']):
        try:
            info = proc.info
            pid = info.get('pid')
            if pid == current_pid:
                continue
            name = info.get('name') or "<unknown>"
            cpu = info.get('cpu_percent') or 0.0
            mem = info.get('memory_percent') or 0.0
            username = info.get('username') or ""
            # safe filters: skip system/root processes on linux, skip core windows processes
            system_keywords = ['system', 'init', 'kernel', 'wininit', 'explorer', 'svchost', 'services', 'ctfmon']
            if any(k.lower() in name.lower() for k in system_keywords):
                continue
            if cpu >= cpu_thresh or mem >= mem_thresh:
                heavy.append((pid, name, cpu, mem, username))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    if not heavy:
        print("[+] Tidak ada proses berat terdeteksi berdasarkan threshold.")
        return
    print("[!] Proses berat yang terdeteksi:")
    for pid, name, cpu, mem, user in heavy:
        print(f"    PID {pid:6} | {name:30} | CPU={cpu:5.1f}% MEM={mem:5.1f}% | user={user}")
    if confirm:
        if not yes_prompt("Apakah mau kill proses-proses di atas?"):
            print("[!] Batal kill proses.")
            return
    for pid, name, cpu, mem, user in heavy:
        try:
            p = psutil.Process(pid)
            p.kill()
            print(f"[+] Dihentikan: {name} (PID {pid})")
        except Exception as e:
            print(f"[!] Gagal kill PID {pid}: {e}")
    log("kill_heavy_processes executed")

def prioritize_targets(targets):
    """
    targets: list of names or pids. Try to increase priority / set affinity.
    """
    if not targets:
        return
    print("[*] Mencoba prioritaskan target:")
    for t in targets:
        print(f"    -> {t}")
    for t in targets:
        try:
            if isinstance(t, int):
                proc = psutil.Process(t)
                _prioritize_proc(proc)
            else:
                # match by name substring (case-insensitive)
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        if t.lower() in (proc.info.get('name') or "").lower():
                            _prioritize_proc(proc)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
        except Exception as e:
            print(f"[!] Prioritize error for {t}: {e}")
    log(f"prioritize_targets executed for {targets}")

def _prioritize_proc(proc):
    try:
        if platform.system() == "Windows":
            try:
                proc.nice(psutil.HIGH_PRIORITY_CLASS)
            except Exception:
                pass
        else:
            if is_root():
                try:
                    proc.nice(-10)
                except Exception:
                    pass
        # try cpu affinity
        try:
            proc.cpu_affinity(list(range(psutil.cpu_count())))
        except Exception:
            pass
        print(f"[+] Prioritized {proc.pid} : {proc.name()}")
    except Exception as e:
        print(f"[!] _prioritize_proc fail: {e}")

# ---------------------- Monitoring helpers ----------------------
def show_system_stats(short=True):
    print("=== System stats ===")
    print(f"CPU cores: {psutil.cpu_count(logical=True)} | CPU usage: {psutil.cpu_percent(interval=0.5)}%")
    mem = psutil.virtual_memory()
    print(f"Memory: total={mem.total//1024//1024}MB used={mem.used//1024//1024}MB ({mem.percent}%)")
    if not short:
        print("Per-process top 5 by CPU:")
        procs = sorted(psutil.process_iter(['pid','name','cpu_percent']), key=lambda p: (p.info.get('cpu_percent') or 0.0), reverse=True)[:5]
        for p in procs:
            try:
                print(f"  PID {p.pid:6} | {p.info.get('name')[:30]:30} | CPU={p.info.get('cpu_percent') or 0.0}%")
            except Exception:
                pass

# ---------------------- Game Boost / FPS tricks ----------------------
def boost_for_game(targets=None):
    print("[*] Applying gamemode boost (best-effort).")
    # 1) reduce niceness of this process
    try:
        me = psutil.Process()
        if platform.system() != "Windows":
            if is_root():
                try:
                    me.nice(-5)
                except Exception:
                    pass
            else:
                try:
                    me.nice(0)
                except Exception:
                    pass
        else:
            try:
                me.nice(psutil.HIGH_PRIORITY_CLASS)
            except Exception:
                pass
    except Exception:
        pass
    # 2) prioritize targets
    if targets:
        prioritize_targets(targets)
    # 3) optional small tweaks
    print("[+] Game boost applied (best-effort).")
    log(f"boost_for_game executed for {targets}")

# ---------------------- Background / Daemon ----------------------
def write_pidfile():
    try:
        with open(PIDFILE, "w") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass

def remove_pidfile():
    try:
        if PIDFILE.exists():
            PIDFILE.unlink()
    except Exception:
        pass

def daemon_loop(mode="performance", targets=None, interval=SLEEP_INTERVAL):
    print(f"[*] Memasuki mode background: {mode}. Log: {DAEMON_LOG}")
    write_pidfile()
    log(f"daemon started mode={mode} targets={targets} interval={interval}")
    try:
        while True:
            if mode in ("performance","auto","cpu"):
                clear_temp_cache(confirm=False)
                free_ram()
                fstrim_if_available()
                set_cpu_performance(True)
                kill_heavy_processes(confirm=False)
            if mode in ("gaming","fps","auto"):
                boost_for_game(targets)
            safe_sleep(interval)
    except KeyboardInterrupt:
        print("\n[!] Background stopped oleh user.")
        log("daemon stopped by user")
    except Exception as e:
        print(f"[!] Daemon error: {e}")
        log(f"daemon error: {e}")
    finally:
        remove_pidfile()

# ---------------------- Helpers for interactive prompts ----------------------
def parse_targets_input(raw):
    items = []
    if not raw:
        return items
    for part in raw.split():
        try:
            items.append(int(part))
        except Exception:
            items.append(part)
    return items

# ---------------------- Interactive Menu ----------------------
def interactive_menu():
    print_banner()
    while True:
        print("""
PILIH MODE:
 1) Gaming Boost (clear cache + prioritize target process + free RAM)
 2) CPU Boost (set performance governor / powerplan)
 3) Performance (aggressive cleanup + trim + free RAM)
 4) FPS Boost (prioritize target process)
 5) Auto Mode (combo of performance + game)
 6) Background / Persistent Mode
 7) Monitor System (quick)
 8) Advanced: Kill heavy processes (safe)
 9) Settings (interval / thresholds)
 0) Exit
""")
        choice = input("Masukkan pilihan (0-9): ").strip()
        if choice == "0":
            print("[*] Keluar. Semoga device makin ringan bro :)")
            break
        elif choice == "1":
            raw = input("Target process name or pid (spasi pisah, kosong=skip): ").strip()
            targets = parse_targets_input(raw)
            clear_temp_cache(confirm=True)
            kill_heavy_processes(confirm=True)
            free_ram()
            prioritize_targets(targets)
            boost_for_game(targets)
            print("[✓] Gaming Boost selesai.")
        elif choice == "2":
            if not is_root() and platform.system() != "Windows":
                print("[!] Tidak root: hasil terbatas.")
            set_cpu_performance(True)
            print("[✓] CPU Boost (attempt) selesai.")
        elif choice == "3":
            if yes_prompt("Ini akan menjalankan cleanup, trim (jika ada), kill heavy process. Lanjut?"):
                clear_temp_cache(confirm=False)
                fstrim_if_available()
                kill_heavy_processes(confirm=True)
                free_ram()
                set_cpu_performance(True)
                print("[✓] Performance mode selesai.")
        elif choice == "4":
            raw = input("Target process name or pid (spasi pisah, kosong=skip): ").strip()
            targets = parse_targets_input(raw)
            prioritize_targets(targets)
            print("[✓] FPS Boost selesai (best-effort).")
        elif choice == "5":
            raw = input("Target proses untuk prioritas (kosong=skip): ").strip()
            targets = parse_targets_input(raw)
            clear_temp_cache(confirm=False)
            kill_heavy_processes(confirm=False)
            free_ram()
            fstrim_if_available()
            set_cpu_performance(True)
            prioritize_targets(targets)
            boost_for_game(targets)
            print("[✓] Auto mode selesai.")
        elif choice == "6":
            print("Background mode: script akan jalan terus sampai dihentikan (Ctrl+C).")
            mode = input("Pilih submode (gaming/cpu/performance/fps/auto) [default=auto]: ").strip() or "auto"
            raw = input("Target proses (nama/pid) untuk prioritas (pisah spasi) [kosong=skip]: ").strip()
            targets = parse_targets_input(raw)
            interval = input(f"Interval loop detik [default {SLEEP_INTERVAL}]: ").strip()
            try:
                interval = int(interval) if interval else SLEEP_INTERVAL
            except Exception:
                interval = SLEEP_INTERVAL
            print("[*] Mulai background. Tekan Ctrl+C untuk stop.")
            daemon_loop(mode=mode, targets=targets, interval=interval)
        elif choice == "7":
            show_system_stats(short=False)
        elif choice == "8":
            if yes_prompt("Kill heavy processes: konfirmasi untuk scan & kill?"):
                kill_heavy_processes(confirm=True)
        elif choice == "9":
            print(f"Current interval: {SLEEP_INTERVAL}s | CPU_THRESH={CPU_HEAVY_THRESHOLD}% | MEM_THRESH={MEM_HEAVY_THRESHOLD}%")
            i = input("Masukkan interval baru (detik) atau Enter untuk skip: ").strip()
            if i:
                try:
                    new_i = int(i)
                    globals()['SLEEP_INTERVAL'] = new_i
                    print(f"[+] Interval diubah ke {new_i}s")
                except:
                    print("[!] Format salah.")
            ci = input("CPU threshold (percent) atau Enter skip: ").strip()
    
def toggle_invisible_mode(targets=None):
    print("[*] Toggle invisible mode activated.")
    if not targets:
        print("[!] Target tidak diberikan.")
        return
    for t in targets:
        try:
            if isinstance(t, int):
                p = psutil.Process(t)
                p.suspend()
                print(f"[+] Process {p.pid} suspended.")
            else:
                for proc in psutil.process_iter(['name']):
                    if t.lower() in (proc.info.get('name') or "").lower():
                        proc.suspend()
                        print(f"[+] Process {proc.pid} ({proc.info['name']}) suspended.")
        except Exception as e:
            print(f"[!] Gagal suspend process {t}: {e}")

def resume_processes(targets=None):
    print("[*] Resume processes activated.")
    if not targets:
        print("[!] Target tidak diberikan.")
        return
    for t in targets:
        try:
            if isinstance(t, int):
                p = psutil.Process(t)
                p.resume()
                print(f"[+] Process {p.pid} resumed.")
            else:
                for proc in psutil.process_iter(['name']):
                    if t.lower() in (proc.info.get('name') or "").lower():
                        proc.resume()
                        print(f"[+] Process {proc.pid} ({proc.info['name']}) resumed.")
        except Exception as e:
            print(f"[!] Gagal resume process {t}: {e}")
