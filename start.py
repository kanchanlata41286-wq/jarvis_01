#!/usr/bin/env python3
"""
MARK LVI — START FILE (launcher + self-test + watchdog)

Run it in any of these ways:

    double-click  start.bat
    python start.py              launch the assistant
    python start.py --check      self-test: verifies everything WITHOUT
                                 opening the window and without hanging
    python start.py --install    force the dependency install, then exit

What it guarantees:

  * picks a supported interpreter (Python 3.11 – 3.13) and, if the one you
    started it with is wrong or empty, re-launches itself under the right one;
  * installs whatever is missing from requirements.txt the first time, with
    pip set to never wait for input (`--no-input`, `--timeout`, `--retries`),
    so a broken network produces an error instead of a frozen console;
  * pre-compiles the project in parallel the first time it starts, so the
    first window opens as fast as the later ones;
  * refuses to start a second copy (two assistants fight over the microphone);
  * raises the app to ABOVE-NORMAL CPU priority on Windows, so the avatar,
    lip-sync and audio callbacks keep their frames while the CPU is busy;
  * watches the child process: an early crash is reported as a failure with
    hints, and a silent-but-alive process is confirmed as "running" instead
    of leaving you staring at a console wondering whether it hung.

Stdlib only — nothing here is a project dependency, so it can run before
anything at all has been installed.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ── Console must survive a legacy code page ─────────────────────────────────
# The report uses ✓/✗/— and the launcher is often started straight from a
# cmd.exe sitting on cp1252 (Turkey/Russia/Japan differ again). Printing one
# character that code page cannot map raises UnicodeEncodeError *inside the
# report*, which is exactly the wrong place to die. UTF-8 with a replacement
# fallback costs nothing and makes the output identical everywhere.
for _stream in ("stdout", "stderr"):
    try:
        _s = getattr(sys, _stream, None)
        if _s is not None and hasattr(_s, "reconfigure"):
            _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass          # pythonw / redirected pipes / anything exotic — never fatal

MIN_PY = (3, 11)          # matches setup.py: below this the app will not parse
MAX_PY = (3, 13)          # matches setup.py: highest version it is tested on
INSTALL_TIMEOUT = 1800    # seconds — pip is stopped, never left running
IMPORT_TIMEOUT = 90       # seconds for `import main`
BOOT_TEST_SECONDS = 12    # seconds to watch the window before calling it good
FIRST_NOTICE = 8.0        # seconds of life before "it is running" is printed

# Modules that must exist before main.py can even be imported. Sourced from the
# module-scope imports of main.py, ui.py and the actions they pull in — the
# heavier libraries (cv2, mss, PIL, bs4, yt-dlp) are imported on first use and
# deliberately not gated here, so a missing optional extra never blocks launch.
CORE_MODULES = [
    "PyQt6",
    "numpy",
    "sounddevice",
    "google.genai",
    "httpx",
    "requests",
    "psutil",
]

LOCK_FILE = HERE / "MARK_LVI.running"

REEXEC_ENV = "MARK_LVI_START_CHILD"   # guards against an interpreter ping-pong


# ── console helpers ──────────────────────────────────────────────────────────

def out(msg: str = "") -> None:
    print(f"[START] {msg}" if msg else "", flush=True)


def check_line(n: int, name: str, ok: bool | None, detail: str = "") -> bool:
    """One row of the --check report. ok=None prints INFO rather than PASS/FAIL."""
    tag = "PASS" if ok is True else ("FAIL" if ok is False else "INFO")
    mark = "✓" if ok is not False else "✗"
    line = f"[CHECK] {n}. {name:<22} {mark} {tag:<4}"
    if detail:
        line += f"  {detail}"
    print(line, flush=True)
    return ok is not False


# ── project discovery ────────────────────────────────────────────────────────

def find_project() -> Path | None:
    """Locate the folder holding main.py.

    The launcher lives one level above the repository (Downloads\\Mark-LVI-main
    \\Mark-LVI-main\\main.py), but it also works when dropped inside the
    repository itself — either layout resolves without configuration."""
    candidates = [HERE / "Mark-LVI-main", HERE]
    if HERE.is_dir():
        candidates += sorted(
            (c for c in HERE.iterdir() if c.is_dir()),
            key=lambda p: p.name.lower(),
        )
    seen: set[Path] = set()
    for cand in candidates:
        cand = cand.resolve()
        if cand in seen:
            continue
        seen.add(cand)
        if (cand / "main.py").is_file():
            return cand
    return None


# ── interpreter discovery ────────────────────────────────────────────────────

_PROBE_TMPL = (
    "import sys, json, importlib.util as u\n"
    "mods = {mods!r}\n"
    "have = {{}}\n"
    "for m in mods:\n"
    "    try:\n"
    "        have[m] = u.find_spec(m) is not None\n"
    "    except Exception:\n"
    "        have[m] = False\n"
    "print(json.dumps({{'v': list(sys.version_info[:3]), 'have': have}}))\n"
)


def _probe(py: list[str]) -> dict | None:
    """(version, installed-modules) for one candidate interpreter, or None."""
    code = _PROBE_TMPL.format(mods=CORE_MODULES)
    try:
        r = subprocess.run(
            [*py, "-c", code],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=30, env=_env(unbuffered=True),
        )
    except Exception:
        return None
    if r.returncode != 0:
        return None
    try:
        data = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return None
    return {"version": tuple(int(x) for x in data["v"]), "have": data["have"]}


def _candidates() -> list[list[str]]:
    """Every interpreter worth trying, most preferred first."""
    cmds: list[list[str]] = [[sys.executable]]
    if sys.platform == "win32":
        py = shutil.which("py")
        if py:
            cmds += [[py, v] for v in ("-3.13", "-3.12", "-3.11")]
        for name in ("python3.13", "python3.12", "python3.11", "python"):
            p = shutil.which(name)
            if p:
                cmds.append([p])
    else:
        for name in ("python3.13", "python3.12", "python3.11", "python3"):
            p = shutil.which(name)
            if p:
                cmds.append([p])
    seen: set[str] = set()
    uniq: list[list[str]] = []
    for c in cmds:
        key = " ".join(c)
        if key.lower() in seen:
            continue
        seen.add(key.lower())
        uniq.append(c)
    return uniq


def _same_exe(a: str, b: str) -> bool:
    try:
        return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))
    except Exception:
        return a == b


def _rank(info: dict) -> tuple:
    """(supported range, core modules installed, version) — higher is better."""
    ver = tuple(info["version"])
    in_range = 1 if MIN_PY <= ver[:2] <= MAX_PY else 0
    filled = sum(1 for m in CORE_MODULES if info["have"].get(m))
    return (in_range, filled, ver)


def pick_interpreter() -> tuple[list[str], dict, dict | None] | None:
    """Best interpreter, probing in preference order and STOPS at the first
    perfect one.

    Every probe spawns a Python (0.5–1.5 s), so comparing all six candidates on
    every launch used to cost several seconds of the time the user is waiting
    for a window. The first candidate is the interpreter already running, so a
    launch through start.bat (which hands over py -3.11) stops after ONE probe.

    Returns (command, probe, current-interpreter probe). The third element is
    reused for the dependency check and the re-launch decision, so no probe is
    ever paid twice in the same run."""
    best: tuple[list[str], dict] | None = None
    best_key: tuple | None = None
    current: dict | None = None
    for index, cmd in enumerate(_candidates()):
        info = _probe(cmd)
        if info is None:
            continue
        if index == 0:
            current = info
        if tuple(info["version"]) < (3, 9):
            continue                      # too old to even parse this launcher
        key = _rank(info)
        if best_key is None or key > best_key:
            best_key, best = key, (cmd, info)
        if key[0] == 1 and key[1] == len(CORE_MODULES):
            break                         # supported AND complete — stop looking
    return (*best, current) if best else None


def maybe_reexec(cmd: list[str], info: dict, current: dict | None) -> None:
    """Re-run this file under the chosen interpreter when ours cannot do the job."""
    if os.environ.get(REEXEC_ENV) == "1":
        return
    if len(cmd) == 1 and _same_exe(cmd[0], sys.executable):
        return                                   # already the best one
    if current is not None and _rank(info) <= _rank(current):
        return                                   # no real gain — stay put

    ver = tuple(info["version"])
    print(f"[START] Re-launching under {ver[0]}.{ver[1]}.{ver[2]}  ({cmd[0]})",
          flush=True)
    env = _env(unbuffered=True)
    env[REEXEC_ENV] = "1"
    try:
        rc = subprocess.run([*cmd, os.path.abspath(__file__), *sys.argv[1:]],
                            env=env).returncode
    except Exception as e:
        out(f"could not re-launch ({e}) — continuing with this interpreter.")
        return
    raise SystemExit(rc)


# ── environment / process helpers ────────────────────────────────────────────

def _env(extra: dict | None = None, unbuffered: bool = False) -> dict:
    env = os.environ.copy()
    if unbuffered:
        # Logs appear the instant they are written. Without this, output sent to
        # a pipe is block-buffered and "nothing is happening" becomes impossible
        # to tell apart from "it is hung".
        env["PYTHONUNBUFFERED"] = "1"
    if extra:
        env.update(extra)
    return env


def _boost_priority(proc: subprocess.Popen) -> bool:
    """Windows only: ABOVE-NORMAL priority, best effort.

    The assistant renders an avatar, analyses audio 50× a second and talks to
    the network while your other work hogs the CPU. Above-normal keeps its
    frames and callbacks on time without starving anything else (that would be
    REALTIME, and it is deliberately not used)."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        PROCESS_SET_INFORMATION = 0x0200
        ABOVE_NORMAL_PRIORITY_CLASS = 0x00008000
        k32 = ctypes.windll.kernel32
        handle = k32.OpenProcess(PROCESS_SET_INFORMATION, False, proc.pid)
        if not handle:
            return False
        try:
            return bool(k32.SetPriorityClass(handle, ABOVE_NORMAL_PRIORITY_CLASS))
        finally:
            k32.CloseHandle(handle)
    except Exception:
        return False


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=10)
        except Exception:
            return False
        return "python" in (r.stdout or "").lower()
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False
    except Exception:
        return False


def existing_instance() -> int | None:
    """PID of an assistant already running, from the lock file — or None.

    Two copies double every microphone frame and answer each other; this is the
    cheapest possible guard against that. A stale lock (the process is gone) is
    simply ignored, so a crash can never lock the user out of the app."""
    try:
        pid = int(LOCK_FILE.read_text(encoding="utf-8").strip())
    except Exception:
        return None
    if pid == os.getpid():
        return None
    return pid if _pid_alive(pid) else None


def _write_lock(pid: int) -> None:
    try:
        LOCK_FILE.write_text(str(pid), encoding="utf-8")
    except Exception:
        pass


def _clear_lock(pid: int | None = None) -> None:
    try:
        if pid is not None:
            try:
                if int(LOCK_FILE.read_text(encoding="utf-8").strip()) != pid:
                    return                      # somebody else owns it now
            except Exception:
                return
        LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass


# ── dependencies ─────────────────────────────────────────────────────────────

def missing_modules(py: list[str], info: dict | None = None) -> list[str]:
    """Modules this interpreter is missing. `info` reuses the probe that already
    chose the interpreter — one subprocess instead of two per launch."""
    if info is None:
        info = _probe(py)
    if info is None:
        return CORE_MODULES[:]                   # cannot probe → assume the worst
    return [m for m in CORE_MODULES if not info["have"].get(m)]


def install_deps(py: list[str], project: Path) -> bool:
    req = project / "requirements.txt"
    if not req.is_file():
        out(f"requirements.txt not found in {project}")
        return False
    cmd = [*py, "-m", "pip", "install",
           "--disable-pip-version-check", "--no-input",
           "--timeout", "30", "--retries", "2",
           "-r", str(req)]
    out("Installing dependencies (one-time, minutes — live output below):")
    out("-" * 66)
    started = time.time()
    try:
        rc = subprocess.run(cmd, cwd=str(project), env=_env(unbuffered=True),
                            timeout=INSTALL_TIMEOUT).returncode
    except subprocess.TimeoutExpired:
        out(f"pip exceeded {INSTALL_TIMEOUT // 60} minutes and was stopped.")
        return False
    except KeyboardInterrupt:
        out("install cancelled.")
        return False
    out("-" * 66)
    out(f"pip finished in {time.time() - started:.0f}s (exit {rc}).")
    if rc != 0:
        out("pip reported an error — see the output above.")
        return False
    return True


def ensure_deps(py: list[str], project: Path, allow_install: bool,
                info: dict | None = None) -> bool:
    missing = missing_modules(py, info)
    if not missing:
        out("Dependencies: all present.")
        return True
    out(f"Dependencies missing: {', '.join(missing)}")
    if not allow_install:
        out("Run `python start.py --install` to install them.")
        return False
    if not install_deps(py, project):
        return False
    still = missing_modules(py)
    if still:
        out(f"STILL missing after install: {', '.join(still)}")
        out("Post this output — it usually means a package has no wheel for your"
            " Python; try Python 3.11–3.13.")
        return False
    out("Dependencies: installed.")
    return True


# ── bytecode pre-warm ────────────────────────────────────────────────────────

def _needs_warm(project: Path) -> bool:
    """True when at least one .py has no fresh .pyc beside it.

    Python compiles lazily on import, which makes the FIRST launch of a fresh
    clone pay for every file at once — right when the user is waiting for a
    window. Pre-warming costs the same work once, in parallel, ahead of time.

    os.walk with PRUNED directories rather than rglob: a repository's .git holds
    thousands of files that are never compiled, and walking them turned a check
    that should take tens of milliseconds into a second of every launch."""
    skip = {"__pycache__", ".git", ".hg", ".svn", "node_modules", "venv",
            ".venv", "build", "dist", ".pytest_cache"}
    for root, dirs, files in os.walk(project):
        dirs[:] = [d for d in dirs if d not in skip]
        for name in files:
            if not name.endswith(".py"):
                continue
            src = Path(root) / name
            try:
                src_mtime = src.stat().st_mtime
            except OSError:
                continue
            fresh = False
            cache = Path(root) / "__pycache__"
            if cache.is_dir():
                stem = name[:-3]
                for pyc in cache.glob(stem + ".*.pyc"):
                    try:
                        if pyc.stat().st_mtime >= src_mtime:
                            fresh = True
                            break
                    except OSError:
                        continue
            if not fresh:
                return True
    return False


def warm_bytecode(py: list[str], project: Path) -> float:
    """Compile what is missing, across all cores. Returns seconds spent (0.0 =
    nothing to do). Never fatal: an unreadable file only costs a warning."""
    if not _needs_warm(project):
        return 0.0
    jobs = str(os.cpu_count() or 2)
    started = time.time()
    try:
        subprocess.run([*py, "-m", "compileall", "-q", "-j", jobs, str(project)],
                       capture_output=True, timeout=300, env=_env(unbuffered=True))
    except Exception as e:
        out(f"bytecode warm-up skipped ({e})")
        return 0.0
    return time.time() - started


# ── launch ───────────────────────────────────────────────────────────────────

def launch(py: list[str], project: Path, force: bool, warm: bool) -> int:
    if not force:
        running = existing_instance()
        if running:
            out(f"MARK LVI is already running (PID {running}).")
            out("Two copies fight over the microphone — close the first one, or"
                " pass --force if you are certain it is gone.")
            return 3

    if warm:
        spent = warm_bytecode(py, project)
        if spent:
            out(f"Bytecode warmed in {spent:.1f}s — this launch pays nothing.")

    api_file = project / "config" / "api_keys.json"
    first_run = not api_file.exists()
    env = _env(unbuffered=True)

    out(f"Booting main.py  ({' '.join(py)}) …")
    try:
        proc = subprocess.Popen([*py, "main.py"], cwd=str(project), env=env)
    except Exception as e:
        out(f"could not start main.py: {e}")
        return 1

    boosted = _boost_priority(proc)
    if boosted:
        out("CPU priority: ABOVE NORMAL (Windows) — avatar and audio keep their"
            " frames under load.")
    _write_lock(proc.pid)

    started = time.time()
    noticed = False
    try:
        while True:
            rc = proc.poll()
            if rc is not None:
                break
            time.sleep(0.5)
            elapsed = time.time() - started
            if not noticed and elapsed >= FIRST_NOTICE:
                noticed = True
                if first_run:
                    out(f"Running for {elapsed:.0f}s — the setup window should be"
                        " on screen. FIRST RUN: paste your free Gemini API key"
                        " (https://aistudio.google.com/app/apikey) and press"
                        " INITIALISE SYSTEMS.")
                else:
                    out(f"Running for {elapsed:.0f}s — the JARVIS window should be"
                        " on screen. If it is not, the window may be behind"
                        " another one (Alt+Tab).")
    except KeyboardInterrupt:
        out("Ctrl+C — shutting the assistant down …")
        _stop(proc)
        _clear_lock(proc.pid)
        return 130

    elapsed = time.time() - started
    _clear_lock(proc.pid)

    if rc != 0:
        out(f"FAILED — main.py stopped with exit code {rc} after {elapsed:.1f}s.")
        if elapsed < 30:
            out("It died during STARTUP, so a dependency problem is the usual"
                " cause. The traceback is in the lines above:")
            out("  python start.py --check     full self-test, no window, no hang")
            out("  python start.py --install   reinstall the dependencies")
            out("  if it stops at 'import PyQt6' / 'import sounddevice' → missing"
                " packages (the install above).")
        else:
            out("It had already been running normally. If you did not close it"
                " yourself, the cause is in the lines above — re-check with:"
                " python start.py --check")
        return rc if rc > 0 else 1

    out(f"Exited cleanly after {elapsed:.1f}s.")
    return 0


def _stop(proc: subprocess.Popen) -> None:
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
            proc.wait(timeout=5)
        except Exception:
            pass


# ── self-test (never opens a window, never waits for input) ──────────────────

def _run(cmd: list[str], cwd: Path, timeout: int, env: dict | None = None
         ) -> tuple[int | None, str, bool]:
    """Run to completion. Returns (exit code | None, output, timed_out)."""
    try:
        r = subprocess.run(cmd, cwd=str(cwd), env=env or _env(unbuffered=True),
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "", True
    except Exception as e:
        return None, str(e), False
    return r.returncode, ((r.stdout or "") + (r.stderr or "")), False


def _tail(text: str, lines: int = 14) -> str:
    keep = [ln for ln in (text or "").splitlines() if ln.strip()]
    return "\n".join("         " + ln[:200] for ln in keep[-lines:])


def check(py: list[str], project: Path, allow_install: bool,
          info: dict | None = None) -> int:
    print("=" * 74, flush=True)
    print("[CHECK] MARK LVI self-test — no window opens, nothing waits for you.",
          flush=True)
    print("=" * 74, flush=True)
    results: list[bool] = []

    # 1 ─ interpreter
    ver = sys.version_info
    in_range = MIN_PY <= ver[:2] <= MAX_PY
    results.append(check_line(
        1, "Interpreter",
        in_range or None,
        f"Python {ver[0]}.{ver[1]}.{ver[2]}"
        + ("" if in_range else f"  (project is tested on "
           f"{MIN_PY[0]}.{MIN_PY[1]}–{MAX_PY[0]}.{MAX_PY[1]})")
        + f"  {' '.join(py)}"))

    # 2 ─ dependencies
    missing = missing_modules(py, info)
    if missing and allow_install:
        out(f"installing: {', '.join(missing)} …")
        install_deps(py, project)
        missing = missing_modules(py)
    results.append(check_line(
        2, "Dependencies",
        not missing,
        "all present" if not missing else "missing: " + ", ".join(missing)))
    if missing:
        out("        fix: python start.py --install")

    # 3 ─ bytecode cache (warm-up is the same work the first launch would do)
    spent = warm_bytecode(py, project)
    results.append(check_line(
        3, "Bytecode cache", True,
        "fresh" if spent == 0 else f"warmed in {spent:.1f}s"))

    # 4 ─ the real import: everything main.py pulls in, in a throwaway process
    if not missing:
        t = time.time()
        rc, text, timed_out = _run([*py, "-c", "import main"], project,
                                   IMPORT_TIMEOUT)
        took = time.time() - t
        if timed_out:
            results.append(check_line(4, "Import test", False,
                                      f"import main hung for {IMPORT_TIMEOUT}s"))
        elif rc != 0:
            results.append(check_line(4, "Import test", False,
                                      f"exit {rc} after {took:.1f}s"))
            print(_tail(text), flush=True)
        else:
            results.append(check_line(4, "Import test", True,
                                      f"import main OK in {took:.1f}s"))
    else:
        results.append(check_line(4, "Import test", False, "skipped — deps missing"))

    # 5 ─ actually construct the window (offscreen: no screen, no mic, no key)
    if not missing:
        ok, detail = _boot_test(py, project)
        results.append(check_line(5, "Window boot", ok, detail))
    else:
        results.append(check_line(5, "Window boot", False, "skipped — deps missing"))

    # 6 ─ API key (informational: the app asks for it on screen, not here)
    key_state = "not configured yet — the first launch will ask for it"
    has_key = False
    try:
        data = json.loads((project / "config" / "api_keys.json")
                          .read_text(encoding="utf-8"))
        has_key = bool(data.get("gemini_api_key"))
        key_state = "configured" if has_key else \
            "file present but empty — the app will ask again"
    except FileNotFoundError:
        pass
    except Exception as e:
        key_state = f"unreadable ({e}) — the app will ask again"
    results.append(check_line(6, "Gemini API key", None, key_state))

    print("-" * 74, flush=True)
    if all(results):
        print("[CHECK] RESULT: ALL GOOD — run  python start.py  to launch.",
              flush=True)
        return 0
    print("[CHECK] RESULT: PROBLEMS FOUND — each FAIL is listed above with its fix.",
          flush=True)
    return 1


def _boot_test(py: list[str], project: Path) -> tuple[bool, str]:
    """Start main.py offscreen for a few seconds.

    This is the only test that exercises the real window construction: plugins,
    actions, the HUD, the setup overlay. It is killed afterwards, and it is
    killed on purpose — a live process at the end of the window IS the pass."""
    env = _env(unbuffered=True, extra={"QT_QPA_PLATFORM": "offscreen"})
    try:
        proc = subprocess.Popen([*py, "main.py"], cwd=str(project), env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace",
                                bufsize=1)
    except Exception as e:
        return False, f"could not start: {e}"

    captured: list[str] = []

    def _drain() -> None:
        try:
            for line in proc.stdout:
                if len(captured) < 400:
                    captured.append(line.rstrip("\n"))
        except Exception:
            pass

    import threading
    threading.Thread(target=_drain, daemon=True).start()

    deadline = time.time() + BOOT_TEST_SECONDS
    while time.time() < deadline:
        if proc.poll() is not None:
            break
        time.sleep(0.25)

    alive = proc.poll() is None
    if alive:
        _stop(proc)
        return True, f"window stayed alive for {BOOT_TEST_SECONDS}s (offscreen)"
    rc = proc.returncode
    text = "\n".join(captured)
    if rc == 0:
        return False, "exited by itself before the test finished"
    print(_tail(text), flush=True)
    return False, f"crashed while building the window (exit {rc})"


# ── entry point ──────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(
        prog="start.py",
        description="MARK LVI launcher: boots the assistant, or self-tests it.",
    )
    ap.add_argument("--check", action="store_true",
                    help="run the self-test and exit (no window, no hang)")
    ap.add_argument("--install", action="store_true",
                    help="install/repair dependencies, then exit")
    ap.add_argument("--force", action="store_true",
                    help="start even if another copy seems to be running")
    ap.add_argument("--no-warm", action="store_true",
                    help="skip the bytecode pre-warm")
    args = ap.parse_args()

    t0 = time.time()

    project = find_project()
    if project is None:
        out("main.py not found next to this launcher.")
        out(f"Expected: {HERE / 'Mark-LVI-main' / 'main.py'}")
        return 2
    out(f"Project     : {project}")

    chosen = pick_interpreter()
    if chosen is None:
        out("No usable Python found.")
        out(f"Install Python {MIN_PY[0]}.{MIN_PY[1]}–{MAX_PY[0]}.{MAX_PY[1]} from"
            " https://www.python.org/downloads/ and tick 'Add python.exe to PATH'.")
        return 2
    py, info, current = chosen
    ver = tuple(info["version"])
    out(f"Interpreter : Python {ver[0]}.{ver[1]}.{ver[2]}  ({' '.join(py)})")
    if not (MIN_PY <= ver[:2] <= MAX_PY):
        out(f"⚠ Python {ver[0]}.{ver[1]} is outside the tested range "
            f"{MIN_PY[0]}.{MIN_PY[1]}–{MAX_PY[0]}.{MAX_PY[1]} — continuing, but a"
            " missing wheel may show up below.")
    maybe_reexec(py, info, current)

    if args.check:
        return check(py, project, allow_install=False, info=info)

    if args.install:
        ok = ensure_deps(py, project, allow_install=True, info=info)
        spent = warm_bytecode(py, project) if ok else 0.0
        if spent:
            out(f"Bytecode warmed in {spent:.1f}s.")
        out("Ready." if ok else "Problems remain — see above.")
        return 0 if ok else 1

    if not ensure_deps(py, project, allow_install=True, info=info):
        out("Startup stopped: the app cannot run without the above.")
        out("Fix the install, then run this file again.")
        return 1

    rc = launch(py, project, force=args.force, warm=not args.no_warm)
    out(f"Total session: {time.time() - t0:.0f}s")
    return rc


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print()
        raise SystemExit(130)
