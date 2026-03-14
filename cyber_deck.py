"""
CYBER-DECK v3.3 - Multi-Level Hacker Game
Changelog v3.3:
  + Keys and doors (key must be collected before reaching the server)
  + Time limit per level (reset without penalty)
  + Encrypted save progress (XOR + base64)
  + Hidden debug menu (F3+F4, password-protected)
  + Massive maps up to 501x401 on later levels
  + Pre-rendered maze surfaces (no lag on large maps)
  + Hardcore neon cyberpunk visuals overhaul
Requirements: pip install colorama pygame numpy
"""

import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import sys, time, random, math, subprocess, json, base64
import numpy as np
sys.setrecursionlimit(100000)

# ════════════════════════════════════════════════════════════════
#  VERSION & AUTO-UPDATER
# ════════════════════════════════════════════════════════════════

VERSION = "3.3"
VERSION_URL = "https://raw.githubusercontent.com/xxkretxx/cyber-deck/refs/heads/main/version.txt"
SCRIPT_URL  = "https://raw.githubusercontent.com/xxkretxx/cyber-deck/refs/heads/main/cyber_deck.py"

# ── Encrypted save ─────────────────────────────────────────────
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyberdeck.sav")
_XOR_KEY  = b"CyberDeck_v3.3_SaveKey_XOR_2025!"

def _xor(data: bytes) -> bytes:
    key = _XOR_KEY
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

def save_progress(data: dict):
    """Saves progress as an encrypted binary file."""
    try:
        raw   = json.dumps(data).encode()
        enc   = _xor(raw)
        b64   = base64.b64encode(enc)
        with open(SAVE_FILE, "wb") as f:
            f.write(b64)
    except Exception as e:
        print(f"  [SAVE] Write error: {e}")

def load_progress() -> dict:
    """Loads progress. Returns {} if missing or corrupted."""
    try:
        with open(SAVE_FILE, "rb") as f:
            b64 = f.read()
        enc = base64.b64decode(b64)
        raw = _xor(enc)
        return json.loads(raw.decode())
    except Exception:
        return {}

# ════════════════════════════════════════════════════════════════
#  AUTO-UPDATER
# ════════════════════════════════════════════════════════════════

def check_for_update(print_fn):
    if not VERSION_URL or not SCRIPT_URL:
        print_fn("  [UPDATE] No update server configured - skipping.")
        return False, VERSION
    try:
        import urllib.request
        print_fn("  [UPDATE] Connecting to update server...")
        time.sleep(0.3)
        with urllib.request.urlopen(VERSION_URL, timeout=5) as r:
            latest = r.read().decode().strip()
        if latest != VERSION:
            print_fn("  [UPDATE] New version found: v" + latest + "  (current: v" + VERSION + ")")
            return True, latest
        else:
            print_fn("  [UPDATE] Already up to date  (v" + VERSION + ")")
            return False, VERSION
    except Exception as e:
        print_fn("  [UPDATE] Could not reach server: " + str(e))
        return False, VERSION


def apply_update(print_fn):
    try:
        import urllib.request
        print_fn("  [UPDATE] Downloading update...")
        with urllib.request.urlopen(SCRIPT_URL, timeout=15) as r:
            new_code = r.read()
        script_path = os.path.abspath(sys.argv[0])
        if getattr(sys, "frozen", False):
            update_path = script_path + ".update"
            with open(update_path, "wb") as f:
                f.write(new_code)
            print_fn("  [UPDATE] Downloaded. Restart the game to apply.")
            time.sleep(2)
            return False
        else:
            with open(script_path, "wb") as f:
                f.write(new_code)
            print_fn("  [UPDATE] Applied! Relaunching...")
            time.sleep(1.5)
            os.execv(sys.executable, [sys.executable] + sys.argv)
            return True
    except Exception as e:
        print_fn("  [UPDATE] Update failed: " + str(e))
        return False


def _apply_pending_exe_update():
    if not getattr(sys, "frozen", False):
        return
    exe_path = os.path.abspath(sys.argv[0])
    update_path = exe_path + ".update"
    if os.path.exists(update_path):
        try:
            bat = exe_path + "_updater.bat"
            with open(bat, "w") as f:
                f.write(
                    '@echo off\n'
                    'timeout /t 2 /nobreak >nul\n'
                    'move /y "' + update_path + '" "' + exe_path + '"\n'
                    'start "" "' + exe_path + '"\n'
                    'del "%~f0"\n'
                )
            subprocess.Popen(bat, shell=True)
            sys.exit(0)
        except Exception:
            pass


# ════════════════════════════════════════════════════════════════
#  SOUND GENERATOR
# ════════════════════════════════════════════════════════════════

SR = 44100

def _stereo(data, vol):
    d = np.clip(data * vol * 32767, -32767, 32767).astype(np.int16)
    return np.column_stack([d, d])

def make_sound(freq=440, dur=0.1, vol=0.4, wave="sine",
               fade=True, freq2=None):
    import pygame
    n = int(SR * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    if wave == "sine":
        d = np.sin(2*np.pi*freq*t)
    elif wave == "square":
        d = np.sign(np.sin(2*np.pi*freq*t))
    elif wave == "saw":
        d = 2*(t*freq - np.floor(t*freq+0.5))
    elif wave == "noise":
        d = np.random.uniform(-1, 1, n)
    elif wave == "sweep" and freq2:
        d = np.sin(2*np.pi*np.cumsum(np.linspace(freq,freq2,n))/SR)
    else:
        d = np.sin(2*np.pi*freq*t)
    if fade:
        d *= np.linspace(1.0, 0.0, n)
    return pygame.sndarray.make_sound(_stereo(d, vol))

def make_melody(notes):
    import pygame
    chunks = []
    for freq, dur, vol in notes:
        n = int(SR * dur)
        t = np.linspace(0, dur, n, endpoint=False)
        c = np.zeros(n) if freq == 0 else np.sin(2*np.pi*freq*t)*np.linspace(1,0,n)
        chunks.append(c * vol)
    d = np.clip(np.concatenate(chunks)*32767, -32767, 32767).astype(np.int16)
    return pygame.sndarray.make_sound(np.column_stack([d, d]))

# ════════════════════════════════════════════════════════════════
#  TERMINAL PHASE
# ════════════════════════════════════════════════════════════════

def terminal_phase():
    try:
        from colorama import init, Fore, Style
        init(autoreset=True)
    except ImportError:
        print("pip install colorama"); sys.exit(1)

    G  = Fore.GREEN
    BG = Fore.CYAN
    DG = Fore.LIGHTGREEN_EX
    Y  = Fore.YELLOW
    W  = Fore.WHITE
    RS = Style.RESET_ALL
    BD = Style.BRIGHT

    BLK = chr(0x2588)
    TL  = chr(0x2554); TR  = chr(0x2557)
    BLC = chr(0x255A); BRC = chr(0x255D)
    HZ  = chr(0x2550); VT  = chr(0x2551)
    HR  = chr(0x2500)
    ARR = chr(0x25BA); ARL = chr(0x25C4)

    def slow_print(text, delay=0.03, color=""):
        for ch in text:
            print(color + ch, end="", flush=True)
            time.sleep(delay)
        print(RS)

    def progress_bar(label, total_time=1.5, status="OK"):
        spin = ["|", "/", "-", "\\"]
        step_delay = 0.07
        steps = int(total_time / step_delay)
        sc = DG if status == "OK" else Y if status == "DONE" else Fore.RED
        for i in range(steps):
            frame = spin[i % len(spin)]
            sys.stdout.write("\r" + DG + "  " + label + "  " + frame + RS)
            sys.stdout.flush()
            time.sleep(step_delay)
        sys.stdout.write("\r" + sc + BD + "  " + label + "  " + status + RS + "\n")
        sys.stdout.flush()

    M  = Fore.MAGENTA; R  = Fore.RED
    LB = Fore.LIGHTBLUE_EX; LY = Fore.LIGHTYELLOW_EX
    LR = Fore.LIGHTRED_EX;  LM = Fore.LIGHTMAGENTA_EX

    _apply_pending_exe_update()
    print("\033[2J\033[H", end="")

    print(G + "  Checking for updates..." + RS, flush=True)
    has_update, latest_ver = check_for_update(lambda s: print(G + s + RS, flush=True))
    if has_update:
        print(Y + BD + "  New version available! Updating now..." + RS, flush=True)
        updated = apply_update(lambda s: print(G + s + RS, flush=True))
        if not updated:
            print(RS, flush=True)
            print(Y + BD + "  +-------------------------------------------------+" + RS, flush=True)
            print(Y + BD + "  |  Update downloaded!                             |" + RS, flush=True)
            print(Y + BD + "  |  Please RESTART the game to apply the update.  |" + RS, flush=True)
            print(Y + BD + "  +-------------------------------------------------+" + RS, flush=True)
            print(RS, flush=True)
            print(G + "  Press ENTER to continue with the current version..." + RS, flush=True)
            input()
    time.sleep(0.5)
    print("\033[2J\033[H", end="")

    ART = [
        r"  ______             __                                        __                      __       ",
        r" /      \           |  \                                      |  \                    |  \      ",
        r"|  $$$$$$\ __    __ | $$____    ______    ______          ____| $$  ______    _______ | $$   __ ",
        r"| $$   \$$|  \  |  \| $$    \  /      \  /      \        /      $$ /      \  /       \| $$  /  \ ",
        r"| $$      | $$  | $$| $$$$$$$\|  $$$$$$\|  $$$$$$\      |  $$$$$$$|  $$$$$$\|  $$$$$$$| $$_/  $$",
        r"| $$   __ | $$  | $$| $$  | $$| $$    $$| $$   \$$      | $$  | $$| $$    $$| $$      | $$   $$ ",
        r"| $$__/  \| $$__/ $$| $$__/ $$| $$$$$$$$| $$            | $$__| $$| $$$$$$$$| $$_____ | $$$$$$\ ",
        r" \$$    $$ \$$    $$| $$    $$ \$$     \| $$             \$$    $$ \$$     \ \$$     \| $$  \$$\ ",
        r"  \$$$$$$  _\$$$$$$$ \$$$$$$$   \$$$$$$$ \$$              \$$$$$$$  \$$$$$$$  \$$$$$$$ \$$   \$$",
        r"          |  \__| $$                                                                            ",
        r"           \$$    $$                                                                            ",
        r"            \$$$$$$                                                                             ",
    ]

    for line in ART:
        print(W + BD + line + RS)
        time.sleep(0.06)

    time.sleep(0.3)
    slow_print("          [ v3.3  //  MULTI-NODE BREACH EDITION ]", 0.035, G + BD)

    sys.stdout.write(G)
    for i in range(54):
        sys.stdout.write(HR)
        sys.stdout.flush()
        time.sleep(0.03)
    print(RS)
    time.sleep(0.3)

    boot_lines = [
        "  > Initializing kernel...             READY",
        "  > Loading crypto modules...          READY",
        "  > Calibrating network signal...      READY",
        "  > Injecting payload drivers...       READY",
        "  > Enabling stealth protocols...      READY",
    ]
    for txt in boot_lines:
        slow_print(txt, 0.010, G)
        time.sleep(0.05)

    print()
    slow_print("  " + TL + HZ * 44 + TR, 0.006, Y + BD)
    slow_print("  " + VT + "       USER AUTHORIZATION REQUIRED          " + VT, 0.006, Y + BD)
    slow_print("  " + BLC + HZ * 44 + BRC, 0.006, Y + BD)
    print()

    # Check for existing save
    save = load_progress()
    saved_nick = save.get("nickname", "")
    saved_level = save.get("level", 0)
    saved_score = save.get("score", 0)

    if saved_nick:
        sys.stdout.write(Y + BD + f"  Detected save: [{saved_nick}] Level {saved_level+1} Score {saved_score}\n" + RS)
        sys.stdout.write(Y + BD + "  Continue? [Y/N]: " + W + BD)
        choice = input().strip().upper()
        print(RS)
        if choice == "Y":
            nick = saved_nick
            slow_print(f"  >> Save loaded for [{nick}]", 0.02, G + BD)
            time.sleep(0.3)

            for label, dur, status in [
                ("  Restoring session      ", 0.8, "OK"),
                ("  Decrypting save data   ", 0.7, "OK"),
                ("  Reconnecting to nodes  ", 1.0, "DONE"),
            ]:
                progress_bar(label, dur, status)

            print()
            slow_print("  Launching visual interface...", 0.04, LY + BD)
            for i in range(3, 0, -1):
                sys.stdout.write(BG + "\r  Starting in: " + LY + BD + str(i) + BG + "...  " + RS)
                sys.stdout.flush()
                time.sleep(0.6)
            print(G + BD + "\r  Launching game!              ")
            time.sleep(0.4)
            return nick, saved_level, saved_score

    sys.stdout.write(Y + BD + "  Enter your Hacker Nickname: " + W + BD)
    nick = input().strip() or "Ghost"
    print(RS)

    slow_print("  >> Verifying identity: [" + nick + "]...", 0.03, G + BD)
    time.sleep(0.4)

    for label, dur, status in [
        ("  Connecting to VPN      ", 1.0, "OK"),
        ("  AES-256 Encryption     ", 0.9, "OK"),
        ("  Bypassing firewalls    ", 1.4, "OK"),
        ("  MAC anonymization      ", 0.8, "OK"),
        ("  Scanning 50 target nodes", 1.5, "OK"),
        ("  Obtaining root access  ", 1.7, "DONE"),
    ]:
        progress_bar(label, dur, status)

    time.sleep(0.3)
    print()
    ip = ".".join(str(random.randint(100, 255)) for _ in range(4))
    slow_print("  [INFO] Route:      TOR --> " + ip + " --> TARGET_NETWORK_v3", 0.012, DG)
    slow_print("  [INFO] Session:    " + nick.upper() + "@CYBERDECK-v3.3",      0.012, DG)
    slow_print("  [INFO] Nodes:      50 available  //  Difficulty: ADAPTIVE",    0.012, BG)
    slow_print("  [INFO] Encryption: AES-256-GCM   //  Proxy: TOR",             0.012, BG)
    print()

    for _ in range(3):
        sys.stdout.write("\r  " + G + BD + ARR + " ACCESS GRANTED " + ARL + RS + "  ")
        sys.stdout.flush()
        time.sleep(0.4)
        sys.stdout.write("\r" + " " * 32 + "\r")
        time.sleep(0.3)
    print(G + BD + "  " + ARR + " ACCESS GRANTED " + ARL + RS)
    print()
    slow_print("  Launching visual interface...", 0.04, LY + BD)
    for i in range(4, 0, -1):
        sys.stdout.write(BG + "\r  Starting in: " + LY + BD + str(i) + BG + "...  " + RS)
        sys.stdout.flush()
        time.sleep(0.6)
    print(G + BD + "\r  Launching game!              ")
    time.sleep(0.4)
    return nick, 0, 0


# ════════════════════════════════════════════════════════════════
#  PROCEDURAL MAZE GENERATOR
# ════════════════════════════════════════════════════════════════

def generate_maze(cols, rows, rng):
    if cols % 2 == 0: cols += 1
    if rows % 2 == 0: rows += 1

    grid = [[1]*cols for _ in range(rows)]

    def carve(cx, cy):
        dirs = [(0,-2),(0,2),(-2,0),(2,0)]
        rng.shuffle(dirs)
        for dx, dy in dirs:
            nx, ny = cx+dx, cy+dy
            if 1 <= nx < cols-1 and 1 <= ny < rows-1 and grid[ny][nx] == 1:
                grid[cy+dy//2][cx+dx//2] = 0
                grid[ny][nx] = 0
                carve(nx, ny)

    grid[1][1] = 0
    carve(1, 1)

    for r in range(rows-2, 0, -1):
        for c in range(cols-2, 0, -1):
            if grid[r][c] == 0:
                grid[r][c] = 2
                return grid, cols, rows
    grid[rows-2][cols-2] = 2
    return grid, cols, rows


# ════════════════════════════════════════════════════════════════
#  LEVEL METADATA
# ════════════════════════════════════════════════════════════════

_NAMES = [
    "Firewall Entry",    "Packet Sniffer",    "Buffer Overflow",   "SQL Injection",
    "Zero Day",          "Root Escalation",   "Kernel Panic",      "Network Breach",
    "DNS Hijack",        "VPN Tunnel",        "Data Exfil",        "Port Scanner",
    "Trojan Horse",      "Keylogger Grid",    "Botnet Node",       "C2 Server",
    "Darknet Gateway",   "Memory Dump",       "Stack Smash",       "Heap Spray",
    "ROP Chain",         "Shellcode Inject",  "Firmware Crack",    "BIOS Override",
    "CPU Exploit",       "GPU Hijack",        "Quantum Cipher",    "Neural Net Hack",
    "AI Adversary",      "Deep Fake Core",    "Satellite Link",    "Power Grid",
    "SCADA System",      "Nuclear Protocol",  "Ghost Protocol",    "Black Ice",
    "ICE Breaker",       "Phantom Node",      "Shadow Server",     "Dark Mirror",
    "Void Matrix",       "Omega Subnet",      "Null Sector",       "Bit Reaper",
    "Zero Matrix",       "Entropy Engine",    "Chaos Protocol",    "Final Cipher",
    "Mainframe Omega",   "SYSTEM ROOT",
]

_SUBTITLES = [
    "Break through the first line of defence",
    "Intercept the encrypted data stream",
    "Overflow the stack and hijack execution",
    "Inject your payload into the database",
    "Exploit an unknown vulnerability",
    "Escalate privileges to root",
    "Crash the kernel and gain control",
    "Infiltrate the corporate network",
    "Redirect DNS to your rogue server",
    "Tunnel through the firewall undetected",
    "Extract classified data from the vault",
    "Scan all open ports without triggering IDS",
    "Deploy your Trojan into the target system",
    "Capture every keystroke on the network",
    "Compromise another node in the botnet",
    "Seize the command and control server",
    "Enter the hidden darknet gateway",
    "Dump process memory for credentials",
    "Smash the stack and overwrite the return address",
    "Spray the heap and control execution flow",
    "Build a return-oriented programming chain",
    "Inject shellcode into a running process",
    "Crack the firmware signing key",
    "Override the BIOS to persist your implant",
    "Exploit a CPU microcode vulnerability",
    "Hijack the GPU for parallel cracking",
    "Break the quantum-encrypted channel",
    "Poison the neural network weights",
    "Defeat the rogue AI security system",
    "Corrupt the deep-fake verification core",
    "Compromise the satellite uplink",
    "Take control of the power grid SCADA",
    "Infiltrate the industrial control system",
    "Initiate the nuclear protocol override",
    "Execute the ghost infiltration protocol",
    "Melt through the Black Ice defence layer",
    "Break through the ICE barrier",
    "Reach the phantom node deep in the net",
    "Shadow the traffic to the hidden server",
    "Mirror yourself into the dark network",
    "Navigate the void of the null matrix",
    "Reach the omega subnet endpoint",
    "Corrupt the null sector completely",
    "Reap every bit from the target drive",
    "Collapse the zero matrix firewall",
    "Feed entropy into the authentication engine",
    "Execute the chaos protocol override",
    "Break the final cipher layer",
    "FINAL TARGET -- Seize the Mainframe Omega",
    "ENDGAME -- You are now SYSTEM ROOT",
]

_THEMES = [
    {"wall":(20,55,20),  "edge":(0,200,70),   "floor":(8,20,8),   "grid":(12,35,12),
     "player":(0,255,110),"target":(255,55,55), "text":(0,230,80)},
    {"wall":(10,28,68),  "edge":(0,140,255),  "floor":(4,10,28),  "grid":(7,18,48),
     "player":(60,180,255),"target":(255,100,0),"text":(60,200,255)},
    {"wall":(58,18,8),   "edge":(255,120,0),  "floor":(22,8,4),   "grid":(38,14,6),
     "player":(255,180,0),"target":(255,0,80),  "text":(255,160,40)},
    {"wall":(38,0,58),   "edge":(180,0,255),  "floor":(14,0,24),  "grid":(26,0,40),
     "player":(220,100,255),"target":(0,255,200),"text":(200,80,255)},
    {"wall":(55,45,0),   "edge":(255,220,0),  "floor":(20,16,0),  "grid":(35,28,0),
     "player":(255,255,80),"target":(255,30,30),"text":(255,230,0)},
    {"wall":(0,45,55),   "edge":(0,220,255),  "floor":(0,16,20),  "grid":(0,28,35),
     "player":(80,255,255),"target":(255,0,150),"text":(0,220,255)},
    {"wall":(55,0,20),   "edge":(255,0,80),   "floor":(20,0,8),   "grid":(35,0,14),
     "player":(255,80,120),"target":(0,255,150),"text":(255,60,100)},
    {"wall":(30,45,10),  "edge":(120,255,0),  "floor":(12,18,4),  "grid":(20,30,8),
     "player":(180,255,60),"target":(255,60,200),"text":(140,255,40)},
    {"wall":(40,20,50),  "edge":(200,100,255),"floor":(15,8,20),  "grid":(28,14,35),
     "player":(255,150,255),"target":(0,230,130),"text":(220,130,255)},
    {"wall":(50,35,10),  "edge":(200,160,0),  "floor":(18,12,4),  "grid":(30,20,6),
     "player":(255,200,80),"target":(80,200,255),"text":(210,170,40)},
]

_ALL_PUZZLES = [
    {"q":"2 + 2 = ?",                                        "a":"4",       "hint":"Very basic"},
    {"q":"Complete: 2, 4, 8, 16, __",                        "a":"32",      "hint":"Powers of 2"},
    {"q":"7 x 8 = ?",                                        "a":"56",      "hint":"Times table"},
    {"q":"How many bits in one byte: __",                    "a":"8",       "hint":"Basic unit"},
    {"q":"Base of hexadecimal: __",                          "a":"16",      "hint":"0 through F"},
    {"q":"2^8 = ?",                                          "a":"256",     "hint":"Eight bits"},
    {"q":"2^10 = ?",                                         "a":"1024",    "hint":"One kilobyte"},
    {"q":"2^16 = ?",                                         "a":"65536",   "hint":"64K"},
    {"q":"2^32 = ?",                                         "a":"4294967296","hint":"IPv4 space"},
    {"q":"1 KB = __ bytes",                                  "a":"1024",    "hint":"2^10"},
    {"q":"1 MB = __ KB",                                     "a":"1024",    "hint":"2^10"},
    {"q":"1 GB = __ MB",                                     "a":"1024",    "hint":"2^10"},
    {"q":"256 XOR 170 = ?",                                  "a":"86",      "hint":"11111111 XOR 10101010"},
    {"q":"0xFF in decimal = ?",                              "a":"255",     "hint":"16^2 - 1"},
    {"q":"0b11111111 in decimal = ?",                        "a":"255",     "hint":"All 8 bits set"},
    {"q":"0b00001111 in decimal = ?",                        "a":"15",      "hint":"Lower nibble"},
    {"q":"0xFF AND 0x0F = ? (decimal)",                      "a":"15",      "hint":"Mask lower nibble"},
    {"q":"NOT 10101010 (8-bit) in decimal = ?",              "a":"85",      "hint":"Flip: 01010101"},
    {"q":"0xA + 0xB = ? (decimal)",                          "a":"21",      "hint":"10 + 11"},
    {"q":"0xDEAD in decimal = ?",                            "a":"57005",   "hint":"D=13 E=14 A=10 D=13"},
    {"q":"Hex: F0 OR 0F = ? (hex)",                          "a":"FF",      "hint":"11110000 OR 00001111"},
    {"q":"0b1010 XOR 0b0110 = ? (binary)",                   "a":"1100",    "hint":"Bitwise XOR each bit"},
    {"q":"Left shift 1 by 4 = ? (decimal)",                  "a":"16",      "hint":"1 << 4"},
    {"q":"Right shift 128 by 3 = ? (decimal)",               "a":"16",      "hint":"128 >> 3"},
    {"q":"Complete: 1, 1, 2, 3, 5, 8, 13, __",              "a":"21",      "hint":"Fibonacci"},
    {"q":"Complete: 1, 4, 9, 16, 25, __",                    "a":"36",      "hint":"Perfect squares"},
    {"q":"Complete: 1, 8, 27, 64, __",                       "a":"125",     "hint":"Cubes"},
    {"q":"log2(256) = ?",                                    "a":"8",       "hint":"2^? = 256"},
    {"q":"log2(1024) = ?",                                   "a":"10",      "hint":"2^? = 1024"},
    {"q":"log10(1000) = ?",                                  "a":"3",       "hint":"10^? = 1000"},
    {"q":"sqrt(144) = ?",                                    "a":"12",      "hint":"12 x 12"},
    {"q":"Mersenne prime: 2^7 - 1 = ?",                      "a":"127",     "hint":"128 minus 1"},
    {"q":"2^7 = ?",                                          "a":"128",     "hint":"Seven bits"},
    {"q":"12! / 11! = ?",                                    "a":"12",      "hint":"Factorials cancel"},
    {"q":"Prime after 89 = ?",                               "a":"97",      "hint":"Check 90-96"},
    {"q":"GCD of 48 and 18 = ?",                             "a":"6",       "hint":"Euclidean algorithm"},
    {"q":"ASCII code for 'A': __",                           "a":"65",      "hint":"Uppercase starts at 65"},
    {"q":"ASCII code for 'a': __",                           "a":"97",      "hint":"Lowercase starts at 97"},
    {"q":"ASCII code for '0': __",                           "a":"48",      "hint":"Digits start at 48"},
    {"q":"ASCII code for space: __",                         "a":"32",      "hint":"Lowest printable"},
    {"q":"ASCII code for DEL: __",                           "a":"127",     "hint":"Last 7-bit ASCII"},
    {"q":"ASCII 90 in char = ?",                             "a":"Z",       "hint":"Last uppercase letter"},
    {"q":"ROT13('A') = ?",                                   "a":"N",       "hint":"Shift 13 in alphabet"},
    {"q":"ROT13('Z') = ?",                                   "a":"M",       "hint":"Wraps around"},
    {"q":"ROT13('H') = ?",                                   "a":"U",       "hint":"H + 13"},
    {"q":"Caesar shift 3: 'D' decodes to?",                  "a":"A",       "hint":"D minus 3"},
    {"q":"Caesar shift 13: 'N' decodes to?",                 "a":"A",       "hint":"Same as ROT13"},
    {"q":"SHA-256 produces __ bits",                         "a":"256",     "hint":"Name says it"},
    {"q":"SHA-512 produces __ bits",                         "a":"512",     "hint":"Name says it"},
    {"q":"MD5 produces __ bits",                             "a":"128",     "hint":"16 bytes"},
    {"q":"AES key size options (bits): 128, 192, __",        "a":"256",     "hint":"Three sizes"},
    {"q":"RSA is based on which math problem?",              "a":"factoring","hint":"Factoring large numbers"},
    {"q":"Diffie-Hellman is used for?",                      "a":"key exchange","hint":"Sharing secrets"},
    {"q":"One-time pad is theoretically?",                   "a":"unbreakable","hint":"Perfect secrecy"},
    {"q":"Port for HTTP: __",                                "a":"80",      "hint":"Unsecured web"},
    {"q":"Port for HTTPS: __",                               "a":"443",     "hint":"Secure web"},
    {"q":"Port for SSH: __",                                 "a":"22",      "hint":"Secure shell"},
    {"q":"Port for FTP: __",                                 "a":"21",      "hint":"File transfer"},
    {"q":"Port for DNS: __",                                 "a":"53",      "hint":"Domain names"},
    {"q":"Port for SMTP: __",                                "a":"25",      "hint":"Email sending"},
    {"q":"IPv4 has __ bit addresses",                        "a":"32",      "hint":"Four octets"},
    {"q":"IPv6 has __ bit addresses",                        "a":"128",     "hint":"16 bytes"},
    {"q":"How many octets in IPv4: __",                      "a":"4",       "hint":"e.g. 192.168.1.1"},
    {"q":"How many octets in IPv6: __",                      "a":"16",      "hint":"128 / 8"},
    {"q":"Loopback address IPv4: __",                        "a":"127.0.0.1","hint":"Home"},
    {"q":"Class A private range starts with: __",            "a":"10",      "hint":"10.x.x.x"},
    {"q":"Class C private range: 192.168.__.__",             "a":"0",       "hint":"RFC 1918"},
    {"q":"TTL in DNS stands for: Time To __",                "a":"Live",    "hint":"How long to cache"},
    {"q":"ICMP is used by which tool?",                      "a":"ping",    "hint":"Network diagnostic"},
    {"q":"TCP handshake has __ steps",                       "a":"3",       "hint":"SYN SYN-ACK ACK"},
    {"q":"UDP is __ (reliable or unreliable)?",              "a":"unreliable","hint":"No handshake"},
    {"q":"OSI model has __ layers",                          "a":"7",       "hint":"Physical to App"},
    {"q":"SQL injection uses which character to escape?",    "a":"'",       "hint":"Single quote"},
    {"q":"XSS stands for Cross-Site __",                     "a":"Scripting","hint":"Injects scripts"},
    {"q":"CSRF stands for Cross-Site Request __",            "a":"Forgery", "hint":"Forged requests"},
    {"q":"DDoS: Distributed Denial of __ attack",           "a":"Service", "hint":"Overwhelm the target"},
    {"q":"A buffer overflow overwrites the return __",       "a":"address", "hint":"Control flow hijack"},
    {"q":"Privilege escalation goes from user to __",        "a":"root",    "hint":"Top level"},
    {"q":"NOP sled uses opcode: __",                         "a":"0x90",    "hint":"No-operation"},
    {"q":"ASLR stands for Address Space Layout __",          "a":"Randomization","hint":"Makes exploits harder"},
    {"q":"DEP stands for Data Execution __",                 "a":"Prevention","hint":"No-execute bit"},
    {"q":"A reverse shell connects __ to attacker",         "a":"target",  "hint":"Victim initiates"},
    {"q":"Metasploit default listener: msfconsole __",      "a":"handler", "hint":"Payload catcher"},
    {"q":"Nmap flag for OS detection: __",                   "a":"-O",      "hint":"Capital letter O"},
    {"q":"Nmap flag for all ports: __",                      "a":"-p-",     "hint":"Dash p dash"},
    {"q":"Netcat command to listen: nc -l -p __",           "a":"4444",    "hint":"Common test port"},
    {"q":"Wireshark captures which type of data?",          "a":"packets", "hint":"Network traffic"},
    {"q":"A honeypot is designed to?",                      "a":"deceive attackers","hint":"Lure and trap"},
    {"q":"Zero-day means the vendor has had __ days to fix","a":"0",       "hint":"Unknown vulnerability"},
    {"q":"CVE stands for Common __ Exposure",               "a":"Vulnerabilities","hint":"Security database"},
    {"q":"CVSS scores range from 0 to __",                  "a":"10",      "hint":"Critical = 10"},
    {"q":"Linux root user UID = __",                         "a":"0",       "hint":"Lowest UID"},
    {"q":"chmod 777 gives __ permissions",                  "a":"all",     "hint":"rwxrwxrwx"},
    {"q":"chmod 644 owner can: read and __",                "a":"write",   "hint":"rw-r--r--"},
    {"q":"Linux command to find SUID files: find / -perm __","a":"-4000",  "hint":"Set user ID bit"},
    {"q":"/etc/shadow stores hashed __",                    "a":"passwords","hint":"Login credentials"},
    {"q":"Windows SAM database stores __",                  "a":"passwords","hint":"Security accounts"},
    {"q":"Registry hive for user data: HKEY_CURRENT___",   "a":"USER",    "hint":"Your profile"},
    {"q":"PowerShell execution policy to bypass: __",       "a":"Bypass",  "hint":"Set-ExecutionPolicy"},
    {"q":"1337 in leet speak means: __",                    "a":"leet",    "hint":"Elite"},
    {"q":"The term 'phishing' derives from: __",            "a":"fishing", "hint":"Luring victims"},
    {"q":"Kevin Mitnick was famous for __",                 "a":"social engineering","hint":"Hacking humans"},
    {"q":"The movie WarGames features which game?",         "a":"chess",   "hint":"WOPR plays it"},
    {"q":"DEFCON is held in which city?",                   "a":"Las Vegas","hint":"Nevada, USA"},
    {"q":"Black hat = __. White hat = __.  Gray = ?",       "a":"gray",    "hint":"You already know 2"},
    {"q":"Shodan is a search engine for __",                "a":"devices", "hint":"IoT and servers"},
    {"q":"The dark web uses which browser?",                "a":"Tor",     "hint":"Onion routing"},
    {"q":"Kali Linux is based on __",                       "a":"Debian",  "hint":"Popular distro"},
    {"q":"The tool Burp Suite is used for __",              "a":"web",     "hint":"Proxy for web apps"},
]

# ── Time limit per level (seconds) — increases gradually ───────
def _level_size(idx):
    """
    Map size by difficulty tier (must stay ODD for the maze carver):
      Levels  1-10 : small    (21x17)
      Levels 11-20 : medium   (51x41)
      Levels 21-30 : large    (101x81)
      Levels 31-40 : huge     (201x161)
      Levels 41-50 : massive  (501x401)
    """
    if idx < 10:   cols, rows = 21,  17
    elif idx < 20: cols, rows = 51,  41
    elif idx < 30: cols, rows = 101, 81
    elif idx < 40: cols, rows = 201, 161
    else:          cols, rows = 501, 401
    if cols % 2 == 0: cols += 1
    if rows % 2 == 0: rows += 1
    return cols, rows

def _level_time(idx):
    """Time scales with map size."""
    if idx < 10:   return 120
    elif idx < 20: return 240
    elif idx < 30: return 480
    elif idx < 40: return 900
    else:          return 1800

# ── Number of guards per level ────────────────────────────────
def _guard_count(idx):
    return 0  # guards removed

def _build_levels():
    rng = random.Random(42)
    levels = []
    total = 50
    for i in range(total):
        cols, rows = _level_size(i)
        maze, c, r = generate_maze(cols, rows, rng)
        theme   = _THEMES[i % len(_THEMES)]
        pool    = _ALL_PUZZLES[:]
        rng.shuffle(pool)
        puzzles = pool[:5]

        # BFS from start (1,1) to get path-distance to every open cell
        from collections import deque
        dist_map = {}
        q = deque([(1, 1, 0)])
        dist_map[(1, 1)] = 0
        while q:
            cr, cc2, d = q.popleft()
            for dr2, dc2 in ((0,1),(0,-1),(1,0),(-1,0)):
                nr2, nc2 = cr+dr2, cc2+dc2
                if (0 <= nr2 < r and 0 <= nc2 < c
                        and maze[nr2][nc2] != 1
                        and (nr2, nc2) not in dist_map):
                    dist_map[(nr2, nc2)] = d + 1
                    q.append((nr2, nc2, d + 1))

        # Find server cell (placed at far corner by generate_maze)
        tgt_cell = None
        for rr in range(r):
            for cc in range(c):
                if maze[rr][cc] == 2:
                    tgt_cell = (rr, cc)

        tgt_dist = dist_map.get(tgt_cell, 1) if tgt_cell else 1

        # BFS from server to get server-side distances
        srv_dist = {}
        if tgt_cell:
            qs = deque([(tgt_cell[0], tgt_cell[1], 0)])
            srv_dist[tgt_cell] = 0
            while qs:
                cr, cc2, d = qs.popleft()
                for dr2, dc2 in ((0,1),(0,-1),(1,0),(-1,0)):
                    nr2, nc2 = cr+dr2, cc2+dc2
                    if (0 <= nr2 < r and 0 <= nc2 < c
                            and maze[nr2][nc2] != 1
                            and (nr2, nc2) not in srv_dist):
                        srv_dist[(nr2, nc2)] = d + 1
                        qs.append((nr2, nc2, d + 1))

        # Key at 45-55% of path from start AND 45-55% from server
        # This places it roughly in the middle of the maze, far from both ends
        lo = int(tgt_dist * 0.45)
        hi = int(tgt_dist * 0.55)
        min_srv = int(tgt_dist * 0.45)
        key_candidates = [
            cell for cell, d in dist_map.items()
            if lo <= d <= hi
            and cell != (1, 1)
            and cell != tgt_cell
            and srv_dist.get(cell, 0) >= min_srv
        ]
        if not key_candidates:
            # Fallback: cell furthest from both start and server combined
            key_candidates = sorted(
                [c for c in dist_map if c != (1,1) and c != tgt_cell],
                key=lambda c: dist_map[c] + srv_dist.get(c, 0),
                reverse=True
            )[:10]
        key_pos = rng.choice(key_candidates)

        levels.append({
            "name":       f"NODE-{i+1:02d} // {_NAMES[i]}",
            "subtitle":   _SUBTITLES[i],
            "cols": c, "rows": r,
            "colors":     theme,
            "maze":       maze,
            "puzzles":    puzzles,
            "time_limit": _level_time(i),
            "guard_count": 0,
            "key_pos":    key_pos,
        })
    return levels

LEVELS = _build_levels()

# ════════════════════════════════════════════════════════════════
#  GAME PHASE
# ════════════════════════════════════════════════════════════════

def game_phase(nickname: str, start_level: int = 0, start_score: int = 0):
    try:
        import pygame
    except ImportError:
        print("pip install pygame"); sys.exit(1)

    pygame.mixer.pre_init(SR, -16, 2, 512)
    pygame.init()
    pygame.mixer.init(SR, -16, 2, 512)

    W, H = 960, 680
    TILE = 48
    FPS  = 60

    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption(f"CYBER-DECK v3.3  //  {nickname}@root")

    def resource_path(filename):
        if getattr(sys, "_MEIPASS", None):
            return os.path.join(sys._MEIPASS, filename)
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

    try:
        icon_img = pygame.image.load(resource_path("icon.png"))
        icon_img = pygame.transform.scale(icon_img, (32, 32))
        pygame.display.set_icon(icon_img)
        if os.name == "nt" and os.path.exists(resource_path("icon.ico")):
            import ctypes
            hwnd = pygame.display.get_wm_info()["window"]
            ico  = ctypes.windll.user32.LoadImageW(
                0, resource_path("icon.ico"), 1, 0, 0, 0x10 | 0x2)
            ctypes.windll.user32.SendMessageW(hwnd, 0x80, 0, ico)
            ctypes.windll.user32.SendMessageW(hwnd, 0x80, 1, ico)
    except Exception as e:
        pass

    clock = pygame.time.Clock()

    def load_font(size, bold=False):
        for name in ["Consolas", "Courier New", "Lucida Console", "DejaVu Sans Mono"]:
            try:
                return pygame.font.SysFont(name, size, bold=bold)
            except Exception:
                continue
        return pygame.font.SysFont(None, size, bold=bold)

    fn_mono  = load_font(17)
    fn_big   = load_font(25, bold=True)
    fn_title = load_font(32, bold=True)
    fn_small = load_font(13)
    fn_huge  = load_font(40, bold=True)

    # ── Sounds ──────────────────────────────────────────────────
    snd_step    = make_sound(800,  .04,  .10, "square")
    snd_wall    = make_sound(70,   .10,  .26, "square")
    snd_server  = make_sound(300,  .55,  .42, "sweep",  False, 1100)
    snd_type    = make_sound(1400, .025, .16, "sine")
    snd_back    = make_sound(700,  .03,  .13, "sine")
    snd_success = make_melody([(523,.09,.4),(659,.09,.4),(784,.09,.4),(1047,.28,.55)])
    snd_fail    = make_melody([(320,.07,.5),(220,.07,.5),(140,.17,.5)])
    snd_lvstart = make_melody([(330,.07,.4),(0,.03,0),(440,.07,.4),(0,.03,0),(550,.15,.5)])
    snd_lvclear = make_melody([(392,.08,.4),(0,.02,0),(523,.08,.4),(0,.02,0),
                               (659,.08,.4),(0,.02,0),(784,.10,.5),(0,.03,0),(1047,.35,.6)])
    snd_gamend  = make_melody([(262,.1,.4),(330,.1,.4),(392,.1,.4),(523,.1,.5),
                               (0,.05,0),(523,.1,.5),(659,.1,.5),(784,.1,.5),(1047,.4,.6)])
    snd_nav     = make_sound(600,  .04,  .11, "sine")
    snd_select  = make_melody([(440,.06,.3),(660,.12,.4)])
    snd_ambient = make_sound(55, 3.0, .055, "sine", False)
    # New sounds
    snd_key     = make_melody([(880,.06,.4),(1100,.10,.5)])            # key collected
    snd_ambient.play(loops=-1)

    # ── Ustawienia ──────────────────────────────────────────────
    DEFAULT_BINDS = {
        "up":    [pygame.K_UP,    pygame.K_w],
        "down":  [pygame.K_DOWN,  pygame.K_s],
        "left":  [pygame.K_LEFT,  pygame.K_a],
        "right": [pygame.K_RIGHT, pygame.K_d],
    }
    binds = {k: list(v) for k, v in DEFAULT_BINDS.items()}

    settings = {
        "vol_master": 0.8,
        "vol_sfx":    0.8,
        "vol_ambient":0.5,
        "show_hints": True,
        "crt_effect": True,
        "show_fps":   False,
    }

    def apply_volume():
        pygame.mixer.music.set_volume(settings["vol_master"])
        snd_ambient.set_volume(settings["vol_master"] * settings["vol_ambient"])
        for s in [snd_step, snd_wall, snd_server, snd_type, snd_back,
                  snd_success, snd_fail, snd_lvstart, snd_lvclear,
                  snd_gamend, snd_nav, snd_select, snd_key]:
            s.set_volume(settings["vol_master"] * settings["vol_sfx"])
    apply_volume()

    # ── Stan gry ────────────────────────────────────────────────
    cur_level   = start_level
    total_score = start_score
    state       = "MENU"
    glow        = 0
    scan_y      = 0
    particles   = []
    float_texts = []
    matrix_drops = [(random.randint(0,W), random.randint(0,H), random.randint(5,20)) for _ in range(80)]

    menu_sel     = 0
    settings_sel = 0
    keybind_sel  = 0
    waiting_key  = None

    # Player
    px, py   = 1, 1
    mv_cd    = 0
    step_cd  = 0
    MVDELAY  = 7

    # Klucz
    has_key  = False

    # Timer
    timer_frames = 0   # frames remaining
    tick_played  = False

    # Puzzle
    p_input       = ""
    p_result      = None
    p_timer       = 0
    fail_flash    = 0
    active_puzzle = None
    hacked_jingle = False
    close_overlay = -1

    # Reset flash
    reset_flash   = 0

    intro_t  = 0
    clear_t  = 0
    done_t   = 0
    cam_x, cam_y = 0.0, 0.0
    maze_surf      = None   # pre-rendered maze surface, rebuilt on level load
    minimap_surf   = None   # pre-rendered minimap background, rebuilt on level load

    # ── Debug menu ──────────────────────────────────────────────
    # Password is XOR+b64 encoded — not human-readable in source.
    # F3 held + F4 opens the password prompt from any state.
    _DBG_TOKEN   = b'BDYmKD0AIFpS'   # encodes the debug password
    _DBG_XOR_KEY = _XOR_KEY
    _dbg_f3_held = False
    _dbg_active  = False   # True = debug menu is open
    _dbg_input   = ""      # password typing buffer
    _dbg_authed  = False   # True = correct password was entered this session
    _dbg_sel     = 0       # selected action in debug menu
    _DBG_ACTIONS = [
        "Give Key",
        "Skip Level",
        "Set Level...",
        "Max Timer",
        "Complete Puzzle",
        "Close",
    ]
    _dbg_set_level_mode = False
    _dbg_set_level_buf  = ""


    def load_level(idx):
        nonlocal px, py, mv_cd, step_cd, p_input, p_result, p_timer
        nonlocal fail_flash, active_puzzle, hacked_jingle, close_overlay
        nonlocal cam_x, cam_y, has_key, timer_frames, tick_played, maze_surf, minimap_surf
        px, py = 1, 1
        mv_cd = step_cd = 0
        p_input = ""; p_result = None; p_timer = 0
        fail_flash = 0; active_puzzle = None
        hacked_jingle = False; close_overlay = -1
        particles.clear(); float_texts.clear()
        cam_x = float(px * TILE)
        cam_y = float(py * TILE)
        has_key = False
        lv_ = LEVELS[idx]
        timer_frames = lv_["time_limit"] * FPS
        tick_played  = False
        # Pre-render the entire maze to a single Surface.
        # Cost: once per level load.  Benefit: O(1) blit every frame.
        _mz   = lv_["maze"]
        _mc   = lv_["cols"]
        _mr   = lv_["rows"]
        _C    = lv_["colors"]
        maze_surf = pygame.Surface((_mc * TILE, _mr * TILE))
        maze_surf.fill(_C["floor"])
        # Subtle floor dot-grid pattern
        _fd = tuple(min(255, v + 8) for v in _C["floor"])
        for _r in range(_mr):
            for _c in range(_mc):
                _rx, _ry = _c * TILE, _r * TILE
                if _mz[_r][_c] != 1:
                    # Dot at cell centre
                    pygame.draw.circle(maze_surf, _fd, (_rx + TILE//2, _ry + TILE//2), 1)
        # Walls: filled + bright neon top/left edge for pseudo-3D depth
        _dim_wall  = tuple(max(0, v - 15) for v in _C["wall"])
        _bright_e  = tuple(min(255, int(v * 1.4)) for v in _C["edge"])
        _mid_e     = _C["edge"]
        for _r in range(_mr):
            for _c in range(_mc):
                _rx, _ry = _c * TILE, _r * TILE
                if _mz[_r][_c] == 1:
                    # Base wall — slightly darker on right/bottom for depth
                    pygame.draw.rect(maze_surf, _C["wall"],   (_rx,    _ry,    TILE,   TILE))
                    pygame.draw.rect(maze_surf, _dim_wall,    (_rx+2,  _ry+2,  TILE-2, TILE-2))
                    # Neon top edge
                    pygame.draw.line(maze_surf, _bright_e, (_rx, _ry), (_rx+TILE-1, _ry), 2)
                    # Neon left edge
                    pygame.draw.line(maze_surf, _bright_e, (_rx, _ry), (_rx, _ry+TILE-1), 2)
                    # Dim bottom/right edge
                    pygame.draw.line(maze_surf, _mid_e, (_rx, _ry+TILE-1), (_rx+TILE-1, _ry+TILE-1), 1)
                    pygame.draw.line(maze_surf, _mid_e, (_rx+TILE-1, _ry), (_rx+TILE-1, _ry+TILE-1), 1)
                else:
                    # Floor grid lines — very dim
                    pygame.draw.rect(maze_surf, _C["grid"], (_rx, _ry, TILE, TILE), 1)
        # Pre-render minimap walls to a cached surface (160x120)
        _MM_W, _MM_H = 160, 120
        _cw = _MM_W / _mc
        _ch = _MM_H / _mr
        _wall_col = (int(_C['edge'][0]*0.5), int(_C['edge'][1]*0.5), int(_C['edge'][2]*0.5))
        minimap_surf = pygame.Surface((_MM_W, _MM_H), pygame.SRCALPHA)
        minimap_surf.fill((0, 0, 0, 180))
        for _r in range(_mr):
            for _c in range(_mc):
                if _mz[_r][_c] == 1:
                    pygame.draw.rect(minimap_surf, _wall_col,
                        (int(_c*_cw), int(_r*_ch), max(1,int(_cw)), max(1,int(_ch))))
        pygame.draw.rect(minimap_surf, _C['edge'], (0, 0, _MM_W, _MM_H), 1)


    def find_target(maze):
        for r, row in enumerate(maze):
            for c, v in enumerate(row):
                if v == 2: return (r, c)
        return None

    def add_particles(x, y, color, count=14):
        for _ in range(count):
            particles.append({"x":float(x),"y":float(y),
                "vx":random.uniform(-3.5,3.5),"vy":random.uniform(-3.5,3.5),
                "life":random.randint(24,64),"color":color})

    def add_float(x, y, text, color):
        float_texts.append({"x":float(x),"y":float(y),"vy":-1.2,
                            "text":text,"color":color,"life":80,"maxlife":80})

    def draw_c(surf, text, font, color, cx, cy):
        s = font.render(text, True, color)
        surf.blit(s, (cx - s.get_width()//2, cy - s.get_height()//2))

    def draw_glow(surf, color, rect, r=6):
        # Wide dim outer bloom
        outer = r * 3
        gs = pygame.Surface((rect[2]+outer*2, rect[3]+outer*2), pygame.SRCALPHA)
        for i in range(outer, 0, -1):
            alpha = int(40 * (i / outer) ** 1.6)
            pygame.draw.rect(gs, (*color, alpha),
                (outer-i, outer-i, rect[2]+i*2, rect[3]+i*2), border_radius=4)
        surf.blit(gs, (rect[0]-outer, rect[1]-outer))
        # Tight bright inner glow
        gs2 = pygame.Surface((rect[2]+r*2, rect[3]+r*2), pygame.SRCALPHA)
        for i in range(r, 0, -1):
            alpha = int(120 * (i / r) ** 2)
            pygame.draw.rect(gs2, (*color, alpha),
                (r-i, r-i, rect[2]+i*2, rect[3]+i*2), border_radius=3)
        surf.blit(gs2, (rect[0]-r, rect[1]-r))

    def draw_panel(surf, x, y, w, h, border_col, alpha=200):
        # Dark translucent background with subtle scanlines
        bg = pygame.Surface((w, h), pygame.SRCALPHA)
        bg.fill((2, 6, 14, alpha))
        # Horizontal scanline texture
        for _sy in range(0, h, 4):
            sl = pygame.Surface((w, 1), pygame.SRCALPHA)
            sl.fill((border_col[0]//12, border_col[1]//12, border_col[2]//12, 30))
            bg.blit(sl, (0, _sy))
        surf.blit(bg, (x, y))
        # Outer dim border
        _dc = tuple(max(0, v//3) for v in border_col)
        pygame.draw.rect(surf, _dc, (x-1, y-1, w+2, h+2), 1, border_radius=7)
        # Inner bright border
        pygame.draw.rect(surf, border_col, (x, y, w, h), 2, border_radius=6)
        # Corner tick-marks (cyberpunk accent)
        _tl = 10
        for _cx, _cy, _dx, _dy in [(x,y,1,1),(x+w,y,-1,1),(x,y+h,1,-1),(x+w,y+h,-1,-1)]:
            pygame.draw.line(surf, border_col, (_cx, _cy+_dy*4), (_cx, _cy+_dy*(_tl+4)), 2)
            pygame.draw.line(surf, border_col, (_cx+_dx*4, _cy), (_cx+_dx*(_tl+4), _cy), 2)

    def draw_bg_art(surf, tick):
        surf.fill((4, 8, 4))
        for i, (mx, my, spd) in enumerate(matrix_drops):
            ch = chr(random.randint(0x21, 0x7E))
            c = min(255, 30 + int(30 * abs(math.sin(tick * 0.02 + mx))))
            s = fn_small.render(ch, True, (0, c, 0))
            surf.blit(s, (mx, my))
            matrix_drops[i] = (mx, (my + spd) % H, spd)
        for gy in range(0, H, 60):
            alpha = int(20 + 10 * abs(math.sin(tick * 0.015 + gy)))
            ls = pygame.Surface((W, 1), pygame.SRCALPHA)
            ls.fill((0, alpha, 0, alpha))
            surf.blit(ls, (0, gy))

    MENU_ITEMS    = ["START GAME", "CONTINUE", "SETTINGS", "KEY BINDS", "QUIT"]
    SETTINGS_KEYS = ["vol_master", "vol_sfx", "vol_ambient", "show_hints", "crt_effect", "show_fps"]
    SETTINGS_LBLS = ["Master Volume", "SFX Volume", "Ambient Volume", "Show Hints", "CRT Effect", "Show FPS"]
    KEYBIND_KEYS  = ["up", "down", "left", "right"]
    KEYBIND_LBLS  = ["Move Up", "Move Down", "Move Left", "Move Right"]

    def settings_val_str(key):
        v = settings[key]
        if isinstance(v, bool): return "ON" if v else "OFF"
        return f"{int(v*100)}%"

    def key_name(k):
        return pygame.key.name(k).upper()

    def change_setting(key, direction):
        v = settings[key]
        if isinstance(v, bool):
            settings[key] = not v
        else:
            settings[key] = max(0.0, min(1.0, v + direction * 0.05))
        apply_volume()

    def do_reset_level():
        """Reset aktualnego poziomu bez kary punktowej."""
        nonlocal reset_flash
        reset_flash = 40
        load_level(cur_level)

    # ════════════════════════════════════════════════════════════
    #  MAIN LOOP
    # ════════════════════════════════════════════════════════════
    running = True
    while running:
        clock.tick(FPS)
        glow   = (glow + 1) % 10000
        scan_y = (scan_y + 1) % H
        if mv_cd   > 0: mv_cd   -= 1
        if step_cd > 0: step_cd -= 1
        if p_timer > 0: p_timer -= 1
        if fail_flash > 0: fail_flash -= 1
        if intro_t  > 0: intro_t  -= 1
        if clear_t  > 0: clear_t  -= 1
        if done_t   > 0: done_t   -= 1
        if reset_flash > 0: reset_flash -= 1

        lv   = LEVELS[cur_level]
        C    = lv["colors"]
        maze = lv["maze"]
        ROWS = lv["rows"]
        COLS = lv["cols"]
        tgt  = find_target(maze)
        key_pos = lv["key_pos"]

        # ── Timer ────────────────────────────────────────────────
        if state == "PLAYING":
            if timer_frames > 0:
                timer_frames -= 1
                if timer_frames <= 10 * FPS and timer_frames % FPS == 0 and timer_frames > 0:
                    pass  # tick warning removed with guards
                if timer_frames == 0:
                    add_float(W//2, H//2 - 40, "TIME OUT!", (255, 80, 0))
                    do_reset_level()

        # Camera
        target_cam_x = float(px * TILE) - W / 2 + TILE / 2
        target_cam_y = float(py * TILE) - H / 2 + TILE / 2
        cam_x += (target_cam_x - cam_x) * 0.15
        cam_y += (target_cam_y - cam_y) * 0.15
        off_x = int(cam_x)
        off_y = int(cam_y)

        # Zamknij overlay po sukcesie
        if close_overlay > 0 and glow >= close_overlay:
            close_overlay = -1
            state = "LEVEL_CLEAR"
            clear_t = 220
            snd_lvclear.play()
            # Save after completing a level
            save_progress({
                "nickname": nickname,
                "level":    cur_level,
                "score":    total_score,
            })

        if state == "LEVEL_INTRO" and intro_t == 0:
            state = "PLAYING"; snd_lvstart.play()

        if state == "LEVEL_CLEAR" and clear_t == 0:
            if cur_level + 1 < len(LEVELS):
                cur_level += 1
                load_level(cur_level)
                state = "LEVEL_INTRO"; intro_t = 160
            else:
                state = "GAME_COMPLETE"; done_t = 600
                snd_gamend.play()

        if p_timer == 0 and p_result == "fail" and state == "PUZZLE":
            p_result = None; p_input = ""

        # ── Events ───────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # ── F3 held-state tracking ───────────────────────────
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F3:
                _dbg_f3_held = True
            if event.type == pygame.KEYUP and event.key == pygame.K_F3:
                _dbg_f3_held = False

            # ── F3 + F4 → open debug password prompt ─────────────
            if (event.type == pygame.KEYDOWN and event.key == pygame.K_F4
                    and _dbg_f3_held and not _dbg_active):
                _dbg_active = True
                _dbg_input  = ""
                _dbg_sel    = 0
                _dbg_set_level_mode = False
                _dbg_set_level_buf  = ""
                continue

            # ── Debug menu input ──────────────────────────────────
            if _dbg_active and event.type == pygame.KEYDOWN:
                if not _dbg_authed:
                    # Password entry phase
                    if event.key == pygame.K_ESCAPE:
                        _dbg_active = False; _dbg_input = ""
                    elif event.key == pygame.K_BACKSPACE:
                        _dbg_input = _dbg_input[:-1]
                    elif event.key == pygame.K_RETURN:
                        # Verify password without ever storing it plain
                        import base64 as _b64
                        _dec = bytes(
                            b ^ _DBG_XOR_KEY[i % len(_DBG_XOR_KEY)]
                            for i, b in enumerate(_b64.b64decode(_DBG_TOKEN))
                        ).decode()
                        if _dbg_input == _dec:
                            _dbg_authed = True
                            _dbg_input  = ""
                        else:
                            _dbg_input = ""   # wrong — clear silently
                    elif event.unicode.isprintable() and len(_dbg_input) < 32:
                        _dbg_input += event.unicode
                else:
                    # Set-level sub-prompt
                    if _dbg_set_level_mode:
                        if event.key == pygame.K_ESCAPE:
                            _dbg_set_level_mode = False; _dbg_set_level_buf = ""
                        elif event.key == pygame.K_BACKSPACE:
                            _dbg_set_level_buf = _dbg_set_level_buf[:-1]
                        elif event.key == pygame.K_RETURN:
                            try:
                                tgt_lv = int(_dbg_set_level_buf) - 1
                                tgt_lv = max(0, min(tgt_lv, len(LEVELS)-1))
                                cur_level = tgt_lv
                                total_score = 0
                                load_level(cur_level)
                                state = "LEVEL_INTRO"; intro_t = 180
                            except ValueError:
                                pass
                            _dbg_set_level_mode = False
                            _dbg_set_level_buf  = ""
                            _dbg_active = False
                        elif event.unicode.isdigit() and len(_dbg_set_level_buf) < 3:
                            _dbg_set_level_buf += event.unicode
                    else:
                        # Navigate actions
                        if event.key in (pygame.K_UP, pygame.K_w):
                            _dbg_sel = (_dbg_sel - 1) % len(_DBG_ACTIONS)
                        elif event.key in (pygame.K_DOWN, pygame.K_s):
                            _dbg_sel = (_dbg_sel + 1) % len(_DBG_ACTIONS)
                        elif event.key == pygame.K_ESCAPE:
                            _dbg_active = False
                        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                            action = _DBG_ACTIONS[_dbg_sel]
                            if action == "Give Key":
                                has_key = True
                                add_float(W//2, H//2-40, "DEBUG: KEY GIVEN", (0,255,180))
                                _dbg_active = False
                            elif action == "Skip Level":
                                state = "LEVEL_CLEAR"; clear_t = 220
                                snd_lvclear.play(); _dbg_active = False
                            elif action == "Set Level...":
                                _dbg_set_level_mode = True
                                _dbg_set_level_buf  = ""
                            elif action == "Max Timer":
                                timer_frames = lv["time_limit"] * FPS
                                add_float(W//2, H//2-40, "DEBUG: TIMER RESET", (0,255,180))
                                _dbg_active = False
                            elif action == "Complete Puzzle":
                                if state == "PUZZLE" and p_result is None:
                                    pts = max(100, 350 - cur_level * 40)
                                    total_score += pts
                                    p_result = "ok"
                                    close_overlay = glow + 120
                                    p_timer = 240
                                    snd_success.play()
                                _dbg_active = False
                            elif action == "Close":
                                _dbg_active = False
                continue  # debug consumed this event

            if event.type == pygame.KEYDOWN:
                if waiting_key is not None:
                    if event.key != pygame.K_ESCAPE:
                        binds[waiting_key][0] = event.key
                    waiting_key = None
                    continue

                if state == "MENU":
                    if event.key in (pygame.K_UP,   pygame.K_w): menu_sel = (menu_sel-1)%len(MENU_ITEMS); snd_nav.play()
                    if event.key in (pygame.K_DOWN, pygame.K_s): menu_sel = (menu_sel+1)%len(MENU_ITEMS); snd_nav.play()
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        snd_select.play()
                        item = MENU_ITEMS[menu_sel]
                        if item == "START GAME":
                            cur_level = 0; total_score = 0
                            load_level(0); state = "LEVEL_INTRO"; intro_t = 180
                        elif item == "CONTINUE":
                            # Kontynuuj od zapisanego poziomu
                            save = load_progress()
                            if save:
                                cur_level   = save.get("level", 0)
                                total_score = save.get("score", 0)
                            load_level(cur_level)
                            state = "LEVEL_INTRO"; intro_t = 180
                        elif item == "SETTINGS":
                            state = "SETTINGS"; settings_sel = 0
                        elif item == "KEY BINDS":
                            state = "KEYBINDS"; keybind_sel = 0
                        elif item == "QUIT":
                            running = False
                    if event.key == pygame.K_ESCAPE: running = False

                elif state == "SETTINGS":
                    if event.key in (pygame.K_UP,   pygame.K_w): settings_sel = (settings_sel-1)%len(SETTINGS_KEYS); snd_nav.play()
                    if event.key in (pygame.K_DOWN, pygame.K_s): settings_sel = (settings_sel+1)%len(SETTINGS_KEYS); snd_nav.play()
                    if event.key in (pygame.K_LEFT,  pygame.K_a): change_setting(SETTINGS_KEYS[settings_sel], -1); snd_nav.play()
                    if event.key in (pygame.K_RIGHT, pygame.K_d): change_setting(SETTINGS_KEYS[settings_sel],  1); snd_nav.play()
                    if event.key == pygame.K_ESCAPE: state = "MENU"

                elif state == "KEYBINDS":
                    if event.key in (pygame.K_UP,   pygame.K_w): keybind_sel = (keybind_sel-1)%len(KEYBIND_KEYS); snd_nav.play()
                    if event.key in (pygame.K_DOWN, pygame.K_s): keybind_sel = (keybind_sel+1)%len(KEYBIND_KEYS); snd_nav.play()
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        waiting_key = KEYBIND_KEYS[keybind_sel]; snd_select.play()
                    if event.key == pygame.K_r:
                        for k, v in DEFAULT_BINDS.items(): binds[k] = list(v)
                    if event.key == pygame.K_ESCAPE: state = "MENU"

                elif state == "LEVEL_INTRO":
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE): intro_t = 1

                elif state == "PLAYING":
                    if event.key == pygame.K_ESCAPE: state = "MENU"

                elif state == "PUZZLE":
                    if p_result is None:
                        if event.key == pygame.K_RETURN:
                            # Case-insensitive, whitespace-tolerant answer check
                            given   = p_input.strip().lower()
                            correct = active_puzzle["a"].strip().lower()
                            if given == correct:
                                pts = max(100, 350 - cur_level * 40)
                                total_score += pts
                                p_result = "ok"
                                close_overlay = glow + 120
                                p_timer = 240
                                snd_success.play()
                                add_particles(W//2, H//2, C["target"], 60)
                                add_float(W//2, H//2 - 60, f"+{pts} PTS", (0, 255, 120))
                            else:
                                total_score = max(0, total_score - 20)
                                p_result = "fail"; fail_flash = 22; p_timer = 150
                                snd_fail.play()
                                add_float(W//2, H//2 - 60, "-20 PTS", (255, 60, 60))
                        elif event.key == pygame.K_BACKSPACE:
                            if p_input: p_input = p_input[:-1]; snd_back.play()
                        elif event.key == pygame.K_ESCAPE:
                            state = "PLAYING"; p_input = ""; p_result = None
                        else:
                            if len(p_input) < 32 and event.unicode.isprintable() and event.unicode:
                                p_input += event.unicode; snd_type.play()

                elif state in ("LEVEL_CLEAR", "GAME_COMPLETE"):
                    if event.key == pygame.K_ESCAPE: state = "MENU"

        # ── Ruch gracza ──────────────────────────────────────────
        if state == "PLAYING" and mv_cd == 0:
            keys = pygame.key.get_pressed()
            nc, nr = px, py
            if any(keys[k] for k in binds["left"]):  nc -= 1
            if any(keys[k] for k in binds["right"]): nc += 1
            if any(keys[k] for k in binds["up"]):    nr -= 1
            if any(keys[k] for k in binds["down"]):  nr += 1
            if (nc, nr) != (px, py):
                if 0 <= nr < ROWS and 0 <= nc < COLS:
                    if maze[nr][nc] != 1:
                        px, py = nc, nr; mv_cd = MVDELAY
                        if step_cd == 0: snd_step.play(); step_cd = MVDELAY

                        # Zbierz klucz
                        if (py, px) == key_pos and not has_key:
                            has_key = True
                            snd_key.play()
                            add_float(px*TILE - off_x, py*TILE - off_y - 20, "KEY OBTAINED!", (255, 230, 0))
                            add_particles(px*TILE - off_x + TILE//2, py*TILE - off_y + TILE//2, (255, 220, 0), 30)

                        # Dotarcie do serwera
                        if tgt and (py, px) == tgt:
                            if not has_key:
                                # No key — server is locked
                                add_float(W//2, H//2 - 40, "NEED KEY FIRST!", (255, 80, 0))
                                snd_wall.play()
                            else:
                                active_puzzle = random.choice(lv["puzzles"])
                                p_input = ""; p_result = None
                                state = "PUZZLE"; snd_server.play()
                    else:
                        snd_wall.play(); mv_cd = MVDELAY // 2

        if p_result == "ok" and not hacked_jingle:
            hacked_jingle = True

        # ════════════════════════════════════════════════════════
        #  DRAW
        # ════════════════════════════════════════════════════════
        draw_bg_art(screen, glow)

        # ─ MENU ─────────────────────────────────────────────────
        if state == "MENU":
            ov = pygame.Surface((W, H), pygame.SRCALPHA); ov.fill((0,0,0,130)); screen.blit(ov,(0,0))
            pw, ph = 600, 360
            ppx, ppy = (W-pw)//2, 60
            draw_panel(screen, ppx, ppy, pw, ph, (0, 200, 60))

            p = abs((glow%80)-40)/40.0
            tc = (0, int(160+95*p), int(50+50*p))
            draw_c(screen, "CYBER-DECK  v3.3", fn_huge, tc, W//2, ppy+55)
            draw_c(screen, "MULTI-NODE BREACH EDITION", fn_mono, (0,150,70), W//2, ppy+100)
            draw_c(screen, "-" * 52, fn_small, (0,70,28), W//2, ppy+122)

            for i, item in enumerate(MENU_ITEMS):
                sel  = (i == menu_sel)
                col  = (0,255,100) if sel else (0,160,60)
                prefix = ">> " if sel else "   "
                draw_c(screen, f"{prefix}{item}{prefix[::-1]}", fn_big, col, W//2, ppy+155+i*38)

            save_data = load_progress()
            if save_data:
                save_info = f"Save: {save_data.get('nickname','?')} | Lvl {save_data.get('level',0)+1} | Score {save_data.get('score',0)}"
            else:
                save_info = "No save file found"
            draw_c(screen, save_info, fn_small, (0,140,50), W//2, ppy+338)

            # Node list panel
            npw, nph = 580, len(LEVELS)*22+40
            npx, npy = (W-npw)//2, ppy+ph+18
            draw_panel(screen, npx, npy, npw, nph, (0,120,40), 160)
            draw_c(screen, "TARGET NODES", fn_mono, (0,180,60), W//2, npy+18)
            for i, lv2 in enumerate(LEVELS):
                col = (0,220,80) if i < cur_level else (0,140,50)
                draw_c(screen, f"{i+1}. {lv2['name']}", fn_small, col, W//2, npy+32+i*20)

        # ─ SETTINGS ─────────────────────────────────────────────
        elif state == "SETTINGS":
            ov = pygame.Surface((W, H), pygame.SRCALPHA); ov.fill((0,0,0,150)); screen.blit(ov,(0,0))
            pw, ph = 560, len(SETTINGS_KEYS)*52+110
            ppx, ppy = (W-pw)//2, (H-ph)//2
            draw_panel(screen, ppx, ppy, pw, ph, (0,200,60))
            draw_c(screen, "=== SETTINGS ===", fn_title, (0,230,80), W//2, ppy+30)
            draw_c(screen, "LEFT/RIGHT to change  |  ESC = back", fn_small, (0,120,40), W//2, ppy+58)
            for i, key in enumerate(SETTINGS_KEYS):
                sel = (i == settings_sel)
                col = (0,255,100) if sel else (0,160,60)
                lbl = SETTINGS_LBLS[i]
                val = settings_val_str(key)
                prefix = "> " if sel else "  "
                draw_c(screen, f"{prefix}{lbl:<22} {val:>6}", fn_mono, col, W//2, ppy+90+i*52)
                if sel and isinstance(settings[key], float):
                    bar_w = 200; bx = W//2 - bar_w//2; by2 = ppy+106+i*52
                    pygame.draw.rect(screen, (0,40,0), (bx, by2, bar_w, 8), border_radius=4)
                    pygame.draw.rect(screen, col, (bx, by2, int(bar_w*settings[key]), 8), border_radius=4)

        # ─ KEYBINDS ─────────────────────────────────────────────
        elif state == "KEYBINDS":
            ov = pygame.Surface((W, H), pygame.SRCALPHA); ov.fill((0,0,0,150)); screen.blit(ov,(0,0))
            pw, ph = 520, len(KEYBIND_KEYS)*56+140
            ppx, ppy = (W-pw)//2, (H-ph)//2
            draw_panel(screen, ppx, ppy, pw, ph, (0,180,255))
            draw_c(screen, "=== KEY BINDINGS ===", fn_title, (60,200,255), W//2, ppy+30)
            draw_c(screen, "ENTER = rebind   R = reset all   ESC = back", fn_small, (40,140,200), W//2, ppy+58)
            for i, key in enumerate(KEYBIND_KEYS):
                sel = (i == keybind_sel)
                col = (60,255,200) if sel else (40,150,180)
                lbl = KEYBIND_LBLS[i]
                k1  = key_name(binds[key][0])
                k2  = key_name(binds[key][1]) if len(binds[key]) > 1 else "-"
                prefix = "> " if sel else "  "
                draw_c(screen, f"{prefix}{lbl:<16}  [{k1}] / [{k2}]", fn_mono, col, W//2, ppy+94+i*52)
            if waiting_key:
                draw_c(screen, f"Press new key for  [{waiting_key.upper()}]...", fn_big,
                       (255,230,0) if (glow//20)%2==0 else (180,150,0), W//2, ppy+ph-36)

        # ─ LEVEL INTRO ───────────────────────────────────────────
        elif state == "LEVEL_INTRO":
            ov = pygame.Surface((W, H), pygame.SRCALPHA); ov.fill((0,0,0,190)); screen.blit(ov,(0,0))
            p = abs((glow%60)-30)/30.0
            nc = C["text"]
            c2 = tuple(min(255, int(v*(0.5+0.5*p))) for v in nc)
            draw_c(screen, f"LEVEL {cur_level+1} / {len(LEVELS)}", fn_huge, c2, W//2, H//2-100)
            draw_c(screen, lv["name"],     fn_big,  nc,         W//2, H//2-40)
            draw_c(screen, lv["subtitle"], fn_mono, (0,160,80), W//2, H//2+10)

            draw_c(screen, f"Time: {lv['time_limit']}s   |   Key required", fn_small, (0,170,80), W//2, H//2+52)
            bc = nc if (glow//25)%2==0 else tuple(v//3 for v in nc)
            draw_c(screen, "[ ENTER / SPACE ] -- START", fn_mono, bc, W//2, H//2+95)

        # ─ PLAYING / PUZZLE / LEVEL_CLEAR ────────────────────────
        elif state in ("PLAYING", "PUZZLE", "LEVEL_CLEAR"):

            # Maze — single blit of pre-rendered surface (fast even at 501x401)
            if maze_surf:
                screen.blit(maze_surf, (-off_x, -off_y))

            # Key pickup — spinning diamond + sparkle
            if not has_key:
                kr, kc = key_pos
                kx = kc*TILE - off_x; ky = kr*TILE - off_y
                if -TILE < kx < W+TILE and -TILE < ky < H+TILE:
                    _kcx = kx + TILE//2; _kcy = ky + TILE//2
                    _kp  = abs((glow % 40) - 20) / 20.0
                    _ka  = glow * 3          # rotation angle degrees
                    _kr  = 12 + int(3 * _kp)
                    _kcol = (255, int(200 + 55*_kp), 0)
                    # Glow bloom
                    draw_glow(screen, (220, 180, 0), (_kcx-_kr, _kcy-_kr, _kr*2, _kr*2), r=12)
                    # Rotating outer diamond
                    _ang = math.radians(_ka)
                    _kpts = []
                    for _a in (_ang, _ang+math.pi/2, _ang+math.pi, _ang+3*math.pi/2):
                        _kpts.append((_kcx + int(_kr * math.cos(_a)),
                                      _kcy + int(_kr * math.sin(_a))))
                    pygame.draw.polygon(screen, _kcol, _kpts)
                    # Inner bright diamond (counter-rotate)
                    _ang2 = math.radians(-_ka * 1.5)
                    _kr2  = 6
                    _kpts2 = []
                    for _a in (_ang2, _ang2+math.pi/2, _ang2+math.pi, _ang2+3*math.pi/2):
                        _kpts2.append((_kcx + int(_kr2 * math.cos(_a)),
                                       _kcy + int(_kr2 * math.sin(_a))))
                    pygame.draw.polygon(screen, (255, 255, 180), _kpts2)
                    # Sparkle dots orbiting
                    for _si in range(4):
                        _sa = math.radians(_ka * 2 + _si * 90)
                        _sx = _kcx + int((_kr + 8) * math.cos(_sa))
                        _sy = _kcy + int((_kr + 8) * math.sin(_sa))
                        _ss = 2 + int(2 * abs(math.sin(glow * 0.1 + _si)))
                        pygame.draw.circle(screen, (255, 240, 100), (_sx, _sy), _ss)

            # Target server — hexagonal frame + scan beam
            if tgt:
                tr, tc2 = tgt
                tx = tc2*TILE - off_x; ty = tr*TILE - off_y
                if -TILE < tx < W+TILE and -TILE < ty < H+TILE:
                    _scx = tx + TILE//2; _scy = ty + TILE//2
                    _spl = abs((glow % 60) - 30) / 30.0
                    if has_key:
                        _sc  = tuple(min(255, int(v + 40*_spl)) for v in C["target"])
                        _sgc = C["target"]
                        _sgr = 12
                    else:
                        _sc  = (80, 80, 100)
                        _sgc = (60, 60, 80)
                        _sgr = 5
                    # Glow
                    draw_glow(screen, _sgc, (tx+2, ty+2, TILE-4, TILE-4), r=_sgr)
                    # Hexagon body
                    _shr = TILE//2 - 5
                    _shpts = []
                    for _hi in range(6):
                        _ha = math.radians(60 * _hi - 30)
                        _shpts.append((_scx + int(_shr * math.cos(_ha)),
                                       _scy + int(_shr * math.sin(_ha))))
                    pygame.draw.polygon(screen, _sc, _shpts)
                    # Inner hexagon outline
                    _shr2 = _shr - 6
                    _shpts2 = []
                    for _hi in range(6):
                        _ha = math.radians(60 * _hi - 30)
                        _shpts2.append((_scx + int(_shr2 * math.cos(_ha)),
                                        _scy + int(_shr2 * math.sin(_ha))))
                    _ic = tuple(min(255, int(v*1.6)) for v in _sc)
                    pygame.draw.polygon(screen, _ic, _shpts2, 2)
                    # Scan beam (animated horizontal line sweeping down the hex)
                    if has_key:
                        _beam_y = ty + 6 + int((TILE - 12) * ((glow % 40) / 40.0))
                        _bs = pygame.Surface((TILE - 8, 2), pygame.SRCALPHA)
                        _bs.fill((*C["target"], 180))
                        screen.blit(_bs, (tx + 4, _beam_y))
                    # Label
                    _lbl = fn_small.render("SRV" if has_key else "LCK", True,
                                           (255,255,255) if has_key else (130,130,150))
                    screen.blit(_lbl, (_scx - _lbl.get_width()//2, _scy - _lbl.get_height()//2))



            # Player — diamond with pulse ring
            _pcx = px*TILE - off_x + TILE//2
            _pcy = py*TILE - off_y + TILE//2
            _pr  = TILE//2 - 4
            # Outer pulse ring
            _ring_r = _pr + 6 + int(4 * abs(math.sin(glow * 0.08)))
            _ring_a = 80 + int(60 * abs(math.sin(glow * 0.08)))
            _rs = pygame.Surface((_ring_r*2+4, _ring_r*2+4), pygame.SRCALPHA)
            pygame.draw.circle(_rs, (*C["player"], _ring_a), (_ring_r+2, _ring_r+2), _ring_r, 2)
            screen.blit(_rs, (_pcx - _ring_r - 2, _pcy - _ring_r - 2))
            # Glow bloom
            draw_glow(screen, C["player"], (_pcx-_pr, _pcy-_pr, _pr*2, _pr*2), r=10)
            # Diamond body
            _pts = [(_pcx, _pcy-_pr), (_pcx+_pr, _pcy), (_pcx, _pcy+_pr), (_pcx-_pr, _pcy)]
            pygame.draw.polygon(screen, C["player"], _pts)
            # Bright inner diamond
            _pr2 = _pr - 6
            _wc  = tuple(min(255, int(v*1.5)) for v in C["player"])
            _pts2 = [(_pcx, _pcy-_pr2), (_pcx+_pr2, _pcy), (_pcx, _pcy+_pr2), (_pcx-_pr2, _pcy)]
            pygame.draw.polygon(screen, _wc, _pts2)
            # Cross hair centre
            pygame.draw.line(screen, (255,255,255), (_pcx-4, _pcy), (_pcx+4, _pcy), 1)
            pygame.draw.line(screen, (255,255,255), (_pcx, _pcy-4), (_pcx, _pcy+4), 1)
            # Key icon badge
            if has_key:
                ks = fn_small.render("K", True, (255, 230, 0))
                screen.blit(ks, (_pcx + _pr - 2, _pcy - _pr - 2))

            # Float texts
            for ft in float_texts[:]:
                ft["y"] += ft["vy"]; ft["life"] -= 1
                if ft["life"] <= 0: float_texts.remove(ft); continue
                alpha = min(255, int(255 * ft["life"] / ft["maxlife"]))
                s = fn_big.render(ft["text"], True, ft["color"])
                s.set_alpha(alpha)
                screen.blit(s, (int(ft["x"]) - s.get_width()//2, int(ft["y"])))

            # Particles
            for p2 in particles[:]:
                p2["x"]+=p2["vx"]; p2["y"]+=p2["vy"]; p2["life"]-=1
                if p2["life"]<=0: particles.remove(p2); continue
                s = pygame.Surface((4,4),pygame.SRCALPHA)
                s.fill((*p2["color"], min(255,p2["life"]*4)))
                screen.blit(s,(int(p2["x"]),int(p2["y"])))

            # CRT
            if settings["crt_effect"]:
                sl2 = pygame.Surface((W,2),pygame.SRCALPHA); sl2.fill((0,255,80,18))
                screen.blit(sl2,(0,scan_y))

            # HUD top — dark bar with neon accent line + level progress
            hp = pygame.Surface((W, 36), pygame.SRCALPHA)
            hp.fill((2, 4, 12, 230))
            screen.blit(hp, (0, 0))
            # Neon accent line at bottom of HUD
            pygame.draw.line(screen, C["edge"], (0, 35), (W, 35), 1)
            _hglow = pygame.Surface((W, 1), pygame.SRCALPHA)
            _hglow.fill((*C["edge"], 60))
            screen.blit(_hglow, (0, 34))
            # Level progress bar (thin strip under accent line)
            _prog = (cur_level) / max(1, len(LEVELS)-1)
            pygame.draw.rect(screen, (20, 30, 20), (0, 35, W, 3))
            pygame.draw.rect(screen, C["edge"], (0, 35, int(W * _prog), 3))
            # Text
            hud_txt = (f"[ CYBER-DECK v3.3 ]  {nickname.upper()}@root  |  "
                       f"Level {cur_level+1}/{len(LEVELS)}  |  Score: {total_score}  |  ESC=menu")
            screen.blit(fn_small.render(hud_txt, True, C["text"]), (8, 10))

            if settings["show_fps"]:
                fps_s = fn_small.render(f"FPS:{int(clock.get_fps())}", True, (100,100,100))
                screen.blit(fps_s, (W-60, 8))

            # Timer HUD — text + animated bar
            secs_left  = timer_frames // FPS
            secs_total = lv["time_limit"]
            timer_col  = (0, 220, 80)
            if secs_left <= 30: timer_col = (255, 180, 0)
            if secs_left <= 10: timer_col = (255, 40,  40)
            timer_str  = f"TIME: {secs_left:3d}s"
            ts = fn_big.render(timer_str, True, timer_col)
            _tx = W - 160 - 8 - ts.get_width() - 8
            screen.blit(ts, (_tx, 42))
            # Timer bar beneath text
            _bar_w = ts.get_width()
            _bar_f = max(0.0, secs_left / max(1, secs_total))
            pygame.draw.rect(screen, (20, 20, 20), (_tx, 42 + ts.get_height() + 2, _bar_w, 4), border_radius=2)
            pygame.draw.rect(screen, timer_col,    (_tx, 42 + ts.get_height() + 2, int(_bar_w * _bar_f), 4), border_radius=2)

            # Key status HUD
            key_str  = "KEY: YES" if has_key else "KEY: NO "
            key_col  = (255, 230, 0) if has_key else (180, 80, 80)
            ks2 = fn_small.render(key_str, True, key_col)
            screen.blit(ks2, (8, H - 40))

            # HUD bottom
            bp2 = pygame.Surface((W,22),pygame.SRCALPHA); bp2.fill((0,12,0,200))
            screen.blit(bp2,(0,H-22))
            goal = "Collect [KEY] then reach [SRV]  |  WASD / Arrow keys"
            screen.blit(fn_small.render(goal, True, C["text"]), (8, H-18))

            # Minimap — blit cached wall surface, then draw dynamic dots only
            MM_W, MM_H = 160, 120
            MM_X, MM_Y = W - MM_W - 8, 38
            cell_w = MM_W / COLS
            cell_h = MM_H / ROWS
            if minimap_surf:
                mm_surf = minimap_surf.copy()
            else:
                mm_surf = pygame.Surface((MM_W, MM_H), pygame.SRCALPHA)
                mm_surf.fill((0,0,0,180))
            # Key dot
            if not has_key:
                kr2, kc2 = key_pos
                pygame.draw.rect(mm_surf, (255, 220, 0),
                    (int(kc2*cell_w), int(kr2*cell_h), max(2,int(cell_w)+1), max(2,int(cell_h)+1)))
            # Server dot
            if tgt:
                tr2, tc3 = tgt
                t_col_mm = C["target"] if has_key else (100, 100, 100)
                pygame.draw.rect(mm_surf, t_col_mm,
                    (int(tc3*cell_w), int(tr2*cell_h), max(2,int(cell_w)+1), max(2,int(cell_h)+1)))
            # Player dot
            pygame.draw.rect(mm_surf, C["player"],
                (int(px*cell_w), int(py*cell_h), max(3,int(cell_w)+2), max(3,int(cell_h)+2)))
            # Neon minimap frame
            pygame.draw.rect(screen, C["edge"], (MM_X-2, MM_Y-2, MM_W+4, MM_H+4), 1, border_radius=3)
            _mml = fn_small.render("MAP", True, C["edge"])
            screen.blit(_mml, (MM_X + MM_W//2 - _mml.get_width()//2, MM_Y - 14))
            screen.blit(mm_surf, (MM_X, MM_Y))

            # Fail flash
            if fail_flash > 0:
                fl = pygame.Surface((W,H),pygame.SRCALPHA)
                fl.fill((255,0,0,int(70*fail_flash/22))); screen.blit(fl,(0,0))

            # Reset flash (caught by guard / timeout)
            if reset_flash > 0:
                rf = pygame.Surface((W,H),pygame.SRCALPHA)
                rf.fill((255,50,0,int(120*reset_flash/40))); screen.blit(rf,(0,0))

            # ─ PUZZLE overlay ─
            if state == "PUZZLE":
                ov = pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((0,0,0,200)); screen.blit(ov,(0,0))
                bw,bh = 620,310; bx=(W-bw)//2; by=(H-bh)//2
                bp3 = int(abs((glow%60)-30)*1.8)
                draw_panel(screen, bx, by, bw, bh, (0, min(185+bp3,255), 55))
                draw_c(screen, "! DATA TERMINAL -- ACCESS VERIFICATION !", fn_mono, C["text"], W//2, by+28)
                draw_c(screen, "-"*72, fn_small, (0,85,30), W//2, by+50)
                q = active_puzzle["q"]
                for li, line in enumerate([q[i:i+60] for i in range(0,len(q),60)]):
                    draw_c(screen, line, fn_mono, C["text"], W//2, by+80+li*24)
                if settings["show_hints"]:
                    draw_c(screen, f"Hint: {active_puzzle['hint']}", fn_small, (0,135,50), W//2, by+148)
                ir = pygame.Rect(bx+90, by+170, bw-180, 36)
                pygame.draw.rect(screen, (0,15,0), ir, border_radius=4)
                pygame.draw.rect(screen, C["text"], ir, 1, border_radius=4)
                cur2 = "|" if (glow//20)%2==0 else " "
                screen.blit(fn_big.render(f"> {p_input}{cur2}", True, C["text"]), (ir.x+10, ir.y+4))
                draw_c(screen, "[ENTER] confirm    [ESC] retreat", fn_small, (0,115,45), W//2, by+230)
                if p_result == "ok":
                    draw_c(screen, "ACCESS GRANTED!  SYSTEM BREACHED!", fn_big, (0,255,100), W//2, by+268)
                elif p_result == "fail":
                    draw_c(screen, "WRONG ANSWER!  TRY AGAIN  (-20 pts)", fn_big, (255,60,60), W//2, by+268)

            # ─ LEVEL CLEAR ─
            if state == "LEVEL_CLEAR":
                ov = pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((0,0,0,170)); screen.blit(ov,(0,0))
                p2 = abs((glow%60)-30)/30.0
                cc = tuple(min(255,int(v+int(55*p2))) for v in C["text"])
                draw_c(screen, f"NODE {cur_level+1} HACKED!", fn_huge, cc, W//2, H//2-60)
                draw_c(screen, lv["name"], fn_mono, C["text"], W//2, H//2)
                draw_c(screen, f"Score: {total_score}", fn_big, (0,230,80), W//2, H//2+48)
                if cur_level+1 < len(LEVELS):
                    nxt = LEVELS[cur_level+1]["name"]
                    draw_c(screen, f"Loading: {nxt}...", fn_mono, (0,170,55), W//2, H//2+95)

        # ─ GAME COMPLETE ─────────────────────────────────────────
        elif state == "GAME_COMPLETE":
            ov = pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((0,0,0,200)); screen.blit(ov,(0,0))
            p = abs((glow%80)-40)/40.0
            gc2 = (int(40*p), int(190+65*p), int(45+55*p))
            draw_c(screen, "**  MAINFRAME SEIZED!  **",  fn_huge,  gc2,        W//2, H//2-120)
            draw_c(screen, "ALL 50 NODES SUCCESSFULLY HACKED",      fn_big,  (0,225,80), W//2, H//2-60)
            draw_c(screen, f"Hacker:  {nickname.upper()}",          fn_mono, (0,195,255),W//2, H//2)
            draw_c(screen, f"Final Score:  {total_score}  points",  fn_big,  (255,230,0),W//2, H//2+50)
            draw_c(screen, "-" * 50, fn_small, (0,75,28), W//2, H//2+95)
            bc = (0,230,80) if (glow//30)%2==0 else (0,90,35)
            draw_c(screen, "[ ESC ] -- Return to Menu", fn_mono, bc, W//2, H//2+125)
            if glow % 12 == 0:
                add_particles(random.randint(80,W-80), random.randint(80,H-80),
                              random.choice([(0,255,100),(255,230,0),(0,195,255),(255,55,55)]),18)
            for p2 in particles[:]:
                p2["x"]+=p2["vx"]; p2["y"]+=p2["vy"]; p2["life"]-=1
                if p2["life"]<=0: particles.remove(p2); continue
                s=pygame.Surface((5,5),pygame.SRCALPHA); s.fill((*p2["color"],min(255,p2["life"]*4)))
                screen.blit(s,(int(p2["x"]),int(p2["y"])))

        # ── Debug overlay (always drawn on top of everything) ─────
        if _dbg_active:
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 210))
            screen.blit(ov, (0, 0))
            bw, bh = 500, 360
            bx, by = (W-bw)//2, (H-bh)//2
            draw_panel(screen, bx, by, bw, bh, (0, 255, 100))

            if not _dbg_authed:
                # Password prompt — typed chars shown as asterisks
                draw_c(screen, "// DEBUG ACCESS //", fn_title, (0,255,100), W//2, by+36)
                draw_c(screen, "Enter password:", fn_mono, (0,200,70), W//2, by+100)
                stars = "*" * len(_dbg_input)
                cur_ch = "|" if (glow//20)%2==0 else " "
                draw_c(screen, f"> {stars}{cur_ch}", fn_big, (0,255,130), W//2, by+148)
                draw_c(screen, "ESC = cancel", fn_small, (0,120,40), W//2, by+220)
            elif _dbg_set_level_mode:
                draw_c(screen, "// SET LEVEL //", fn_title, (0,255,100), W//2, by+36)
                draw_c(screen, f"Enter level number (1-{len(LEVELS)}):", fn_mono, (0,200,70), W//2, by+110)
                cur_ch = "|" if (glow//20)%2==0 else " "
                draw_c(screen, f"> {_dbg_set_level_buf}{cur_ch}", fn_big, (0,255,130), W//2, by+160)
                draw_c(screen, "ENTER = confirm   ESC = back", fn_small, (0,120,40), W//2, by+220)
            else:
                draw_c(screen, "// DEBUG MENU //", fn_title, (0,255,100), W//2, by+36)
                draw_c(screen, f"Level {cur_level+1}/{len(LEVELS)}  |  Score {total_score}  |  Key: {'YES' if has_key else 'NO'}  |  Timer: {timer_frames//FPS}s", fn_small, (0,170,60), W//2, by+76)
                draw_c(screen, "-"*56, fn_small, (0,80,30), W//2, by+98)
                for ai, action in enumerate(_DBG_ACTIONS):
                    sel = (ai == _dbg_sel)
                    col = (0,255,120) if sel else (0,150,60)
                    prefix = ">> " if sel else "   "
                    draw_c(screen, f"{prefix}{action}", fn_big, col, W//2, by+128+ai*34)
                draw_c(screen, "UP/DOWN  ENTER=select  ESC=close", fn_small, (0,100,40), W//2, by+336)

        pygame.display.flip()

    pygame.mixer.stop()
    pygame.quit()


# ════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    result = terminal_phase()
    nick, start_lv, start_sc = result
    game_phase(nick, start_lv, start_sc)
