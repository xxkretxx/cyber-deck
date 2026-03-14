"""
CYBER-DECK v3.0 - Multi-Level Hacker Game
Requirements: pip install colorama pygame numpy
"""

import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import sys, time, random, math, subprocess
import numpy as np
sys.setrecursionlimit(100000)

# ════════════════════════════════════════════════════════════════
#  VERSION & AUTO-UPDATER
#  To publish: bump VERSION, push new cyber_deck.py + version.txt
#  to your GitHub repo, then fill in the two URLs below.
# ════════════════════════════════════════════════════════════════

VERSION = "3.0"

# Replace with your actual GitHub raw URLs after creating the repo:
#   VERSION_URL = "https://raw.githubusercontent.com/YOU/REPO/main/version.txt"
#   SCRIPT_URL  = "https://raw.githubusercontent.com/YOU/REPO/main/cyber_deck.py"
VERSION_URL = ""
SCRIPT_URL  = ""


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
#  SOUND GENERATOR  (no external files, pure numpy math)
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

    # Box / block chars via chr() -- never treated as escape sequences
    BLK = chr(0x2588)  # full block
    TL  = chr(0x2554)  # top-left corner
    TR  = chr(0x2557)  # top-right corner
    BLC = chr(0x255A)  # bottom-left corner
    BRC = chr(0x255D)  # bottom-right corner
    HZ  = chr(0x2550)  # horizontal double
    VT  = chr(0x2551)  # vertical double
    HR  = chr(0x2500)  # horizontal single
    ARR = chr(0x25BA)  # right arrow
    ARL = chr(0x25C4)  # left arrow

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

    M  = Fore.MAGENTA
    R  = Fore.RED
    LB = Fore.LIGHTBLUE_EX
    LY = Fore.LIGHTYELLOW_EX
    LR = Fore.LIGHTRED_EX
    LM = Fore.LIGHTMAGENTA_EX

    # Apply any pending .exe update before anything else
    _apply_pending_exe_update()

    print("\033[2J\033[H", end="")

    # Quick update check (shows in terminal before the logo)
    print(G + "  Checking for updates..." + RS, flush=True)
    has_update, latest_ver = check_for_update(lambda s: print(G + s + RS, flush=True))
    if has_update:
        print(Y + BD + "  New version available! Updating now..." + RS, flush=True)
        updated = apply_update(lambda s: print(G + s + RS, flush=True))
        if not updated:
            # .exe case — update was downloaded but needs a restart
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
    slow_print("          [ v3.0  //  MULTI-NODE BREACH EDITION ]", 0.035, G + BD)

    # Animated divider — prints one char at a time in green
    sys.stdout.write(G)
    for i in range(54):
        sys.stdout.write(HR)
        sys.stdout.flush()
        time.sleep(0.03)
    print(RS)
    time.sleep(0.3)

    # Boot lines — all green
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
    # Auth box — yellow
    slow_print("  " + TL + HZ * 44 + TR, 0.006, Y + BD)
    slow_print("  " + VT + "       USER AUTHORIZATION REQUIRED          " + VT, 0.006, Y + BD)
    slow_print("  " + BLC + HZ * 44 + BRC, 0.006, Y + BD)
    print()

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
    slow_print("  [INFO] Session:    " + nick.upper() + "@CYBERDECK-v3.0",      0.012, DG)
    slow_print("  [INFO] Nodes:      50 available  //  Difficulty: ADAPTIVE",    0.012, BG)
    slow_print("  [INFO] Encryption: AES-256-GCM   //  Proxy: TOR",             0.012, BG)
    print()

    # Blinking access granted
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
    return nick


# ════════════════════════════════════════════════════════════════
#  LEVEL DATA
# ════════════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════════════
#  PROCEDURAL MAZE GENERATOR  (recursive backtracker)
# ════════════════════════════════════════════════════════════════

def generate_maze(cols, rows, rng):
    """
    Returns a 2-D list (rows x cols) of 0/1.
    Maze cells are on odd grid coords; walls on even coords.
    cols and rows should both be odd numbers >= 5.
    """
    # Force odd
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

    # Place target at bottom-right open cell
    for r in range(rows-2, 0, -1):
        for c in range(cols-2, 0, -1):
            if grid[r][c] == 0:
                grid[r][c] = 2
                return grid, cols, rows
    grid[rows-2][cols-2] = 2
    return grid, cols, rows


# ════════════════════════════════════════════════════════════════
#  LEVEL METADATA  (50 levels, progressively bigger)
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

# 10 colour themes that cycle through levels
_THEMES = [
    {"wall":(20,55,20),  "edge":(0,200,70),   "floor":(8,20,8),   "grid":(12,35,12),
     "player":(0,255,110),"target":(255,55,55), "text":(0,230,80)},   # green
    {"wall":(10,28,68),  "edge":(0,140,255),  "floor":(4,10,28),  "grid":(7,18,48),
     "player":(60,180,255),"target":(255,100,0),"text":(60,200,255)},  # blue
    {"wall":(58,18,8),   "edge":(255,120,0),  "floor":(22,8,4),   "grid":(38,14,6),
     "player":(255,180,0),"target":(255,0,80),  "text":(255,160,40)},  # orange
    {"wall":(38,0,58),   "edge":(180,0,255),  "floor":(14,0,24),  "grid":(26,0,40),
     "player":(220,100,255),"target":(0,255,200),"text":(200,80,255)}, # purple
    {"wall":(55,45,0),   "edge":(255,220,0),  "floor":(20,16,0),  "grid":(35,28,0),
     "player":(255,255,80),"target":(255,30,30),"text":(255,230,0)},   # gold
    {"wall":(0,45,55),   "edge":(0,220,255),  "floor":(0,16,20),  "grid":(0,28,35),
     "player":(80,255,255),"target":(255,0,150),"text":(0,220,255)},   # cyan
    {"wall":(55,0,20),   "edge":(255,0,80),   "floor":(20,0,8),   "grid":(35,0,14),
     "player":(255,80,120),"target":(0,255,150),"text":(255,60,100)},  # red
    {"wall":(30,45,10),  "edge":(120,255,0),  "floor":(12,18,4),  "grid":(20,30,8),
     "player":(180,255,60),"target":(255,60,200),"text":(140,255,40)}, # lime
    {"wall":(40,20,50),  "edge":(200,100,255),"floor":(15,8,20),  "grid":(28,14,35),
     "player":(255,150,255),"target":(0,230,130),"text":(220,130,255)},# pink
    {"wall":(50,35,10),  "edge":(200,160,0),  "floor":(18,12,4),  "grid":(30,20,6),
     "player":(255,200,80),"target":(80,200,255),"text":(210,170,40)}, # amber
]

# Full puzzle pool — 200+ questions, shuffled per level
_ALL_PUZZLES = [
    # Basics
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
    # Binary / Hex
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
    # Math / Sequences
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
    # ASCII
    {"q":"ASCII code for 'A': __",                           "a":"65",      "hint":"Uppercase starts at 65"},
    {"q":"ASCII code for 'a': __",                           "a":"97",      "hint":"Lowercase starts at 97"},
    {"q":"ASCII code for '0': __",                           "a":"48",      "hint":"Digits start at 48"},
    {"q":"ASCII code for space: __",                         "a":"32",      "hint":"Lowest printable"},
    {"q":"ASCII code for DEL: __",                           "a":"127",     "hint":"Last 7-bit ASCII"},
    {"q":"ASCII 90 in char = ?",                             "a":"Z",       "hint":"Last uppercase letter"},
    # Crypto
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
    # Networking
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
    # Security concepts
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
    # Systems
    {"q":"Linux root user UID = __",                         "a":"0",       "hint":"Lowest UID"},
    {"q":"chmod 777 gives __ permissions",                  "a":"all",     "hint":"rwxrwxrwx"},
    {"q":"chmod 644 owner can: read and __",                "a":"write",   "hint":"rw-r--r--"},
    {"q":"Linux command to find SUID files: find / -perm __","a":"-4000",  "hint":"Set user ID bit"},
    {"q":"/etc/shadow stores hashed __",                    "a":"passwords","hint":"Login credentials"},
    {"q":"Windows SAM database stores __",                  "a":"passwords","hint":"Security accounts"},
    {"q":"Registry hive for user data: HKEY_CURRENT___",   "a":"USER",    "hint":"Your profile"},
    {"q":"PowerShell execution policy to bypass: __",       "a":"Bypass",  "hint":"Set-ExecutionPolicy"},
    # Misc hacker culture
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

def _build_levels():
    rng = random.Random(42)  # fixed seed = consistent mazes every run
    levels = []
    total = 50
    # Maze sizes: start 11x9, grow by ~2 cols and ~2 rows every 3 levels
    # Level 50 → about 43x35
    for i in range(total):
        cols = 11 + (i // 3) * 2
        rows = 9  + (i // 3) * 2
        # Force odd
        if cols % 2 == 0: cols += 1
        if rows % 2 == 0: rows += 1
        cols = min(cols, 81)  # cap so it stays manageable
        rows = min(rows, 61)

        maze, c, r = generate_maze(cols, rows, rng)
        theme = _THEMES[i % len(_THEMES)]
        # Pick 4 unique puzzles for this level (seeded so same every run)
        pool  = _ALL_PUZZLES[:]
        rng.shuffle(pool)
        puzzles = pool[:5]

        levels.append({
            "name":     f"NODE-{i+1:02d} // {_NAMES[i]}",
            "subtitle": _SUBTITLES[i],
            "cols": c, "rows": r,
            "colors": theme,
            "maze":   maze,
            "puzzles": puzzles,
        })
    return levels

LEVELS = _build_levels()
# ════════════════════════════════════════════════════════════════
#  GAME PHASE
# ════════════════════════════════════════════════════════════════

def game_phase(nickname: str):
    try:
        import pygame
    except ImportError:
        print("pip install pygame"); sys.exit(1)

    pygame.mixer.pre_init(SR, -16, 2, 512)
    pygame.init()
    pygame.mixer.init(SR, -16, 2, 512)

    W, H = 960, 680
    TILE  = 48    # Bigger tiles = more zoomed in, can't see full maze
    FPS   = 60

    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption(f"CYBER-DECK v3.0  //  {nickname}@root")
    def resource_path(filename):
        if getattr(sys, "_MEIPASS", None):
            return os.path.join(sys._MEIPASS, filename)
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

    try:
        icon_img = pygame.image.load(resource_path("icon.png"))
        icon_img = pygame.transform.scale(icon_img, (32, 32))
        pygame.display.set_icon(icon_img)
        # Wymusza ikonę przez Windows API (pasek tytułu)
        if os.name == "nt" and os.path.exists(resource_path("icon.ico")):
            import ctypes
            hwnd = pygame.display.get_wm_info()["window"]
            ico  = ctypes.windll.user32.LoadImageW(
                0, resource_path("icon.ico"), 1, 0, 0, 0x10 | 0x2
            )
            ctypes.windll.user32.SendMessageW(hwnd, 0x80, 0, ico)
            ctypes.windll.user32.SendMessageW(hwnd, 0x80, 1, ico)
    except Exception as e:
        print(f"  [WARNING] Nie można wczytać ikony: {e}")
    clock  = pygame.time.Clock()

    # Fonts — try Consolas first (best for hacker aesthetic), fallback chain
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

    # ── Sounds ───────────────────────────────────────────────────
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
    snd_ambient.play(loops=-1)

    # ── Default key bindings ──────────────────────────────────────
    DEFAULT_BINDS = {
        "up":    [pygame.K_UP,    pygame.K_w],
        "down":  [pygame.K_DOWN,  pygame.K_s],
        "left":  [pygame.K_LEFT,  pygame.K_a],
        "right": [pygame.K_RIGHT, pygame.K_d],
    }
    binds = {k: list(v) for k, v in DEFAULT_BINDS.items()}

    # ── Settings ─────────────────────────────────────────────────
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
                  snd_gamend, snd_nav, snd_select]:
            s.set_volume(settings["vol_master"] * settings["vol_sfx"])
    apply_volume()

    # ── Game state ───────────────────────────────────────────────
    cur_level     = 0
    total_score   = 0
    state         = "MENU"   # MENU | SETTINGS | KEYBINDS | LEVEL_INTRO | PLAYING | PUZZLE | LEVEL_CLEAR | GAME_COMPLETE
    glow          = 0
    scan_y        = 0
    particles     = []
    float_texts   = []   # {x,y,vy,text,color,life,maxlife}
    matrix_drops  = [(random.randint(0,W), random.randint(0,H), random.randint(5,20)) for _ in range(80)]

    menu_sel      = 0    # selected menu item
    settings_sel  = 0
    keybind_sel   = 0
    waiting_key   = None # which action we are re-binding

    # Player
    px, py        = 1, 1
    mv_cd         = 0
    step_cd       = 0
    MVDELAY       = 7

    # Puzzle
    p_input       = ""
    p_result      = None  # None|"ok"|"fail"
    p_timer       = 0
    fail_flash    = 0
    active_puzzle = None
    hacked_jingle = False
    close_overlay = -1

    # Intro/clear timers
    intro_t  = 0
    clear_t  = 0
    done_t   = 0

    # Camera (for big mazes)
    cam_x, cam_y = 0.0, 0.0

    def load_level(idx):
        nonlocal px, py, mv_cd, step_cd, p_input, p_result, p_timer
        nonlocal fail_flash, active_puzzle, hacked_jingle, close_overlay
        nonlocal cam_x, cam_y
        px, py = 1, 1
        mv_cd = step_cd = 0
        p_input = ""; p_result = None; p_timer = 0
        fail_flash = 0; active_puzzle = None
        hacked_jingle = False; close_overlay = -1
        particles.clear(); float_texts.clear()
        cam_x = float(px * TILE)
        cam_y = float(py * TILE)

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
        gs = pygame.Surface((rect[2]+r*4, rect[3]+r*4), pygame.SRCALPHA)
        for i in range(r, 0, -1):
            pygame.draw.rect(gs, (*color, int(55*(i/r))),
                (r*2-i, r*2-i, rect[2]+i*2, rect[3]+i*2), border_radius=3)
        surf.blit(gs, (rect[0]-r*2, rect[1]-r*2))

    def draw_panel(surf, x, y, w, h, border_col, alpha=200):
        bg = pygame.Surface((w, h), pygame.SRCALPHA)
        bg.fill((0, 10, 0, alpha))
        surf.blit(bg, (x, y))
        pygame.draw.rect(surf, border_col, (x, y, w, h), 2, border_radius=6)

    def draw_bg_art(surf, tick):
        """Animated circuit-board background."""
        surf.fill((4, 8, 4))
        # Matrix rain
        for i, (mx, my, spd) in enumerate(matrix_drops):
            ch = chr(random.randint(0x21, 0x7E))  # ASCII printable only
            c = min(255, 30 + int(30 * abs(math.sin(tick * 0.02 + mx))))
            s = fn_small.render(ch, True, (0, c, 0))
            surf.blit(s, (mx, my))
            matrix_drops[i] = (mx, (my + spd) % H, spd)
        # Horizontal grid lines
        for gy in range(0, H, 60):
            alpha = int(20 + 10 * abs(math.sin(tick * 0.015 + gy)))
            ls = pygame.Surface((W, 1), pygame.SRCALPHA)
            ls.fill((0, alpha, 0, alpha))
            surf.blit(ls, (0, gy))

    # ── Menu items ───────────────────────────────────────────────
    MENU_ITEMS    = ["START GAME", "SETTINGS", "KEY BINDS", "QUIT"]
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
        if intro_t > 0: intro_t -= 1
        if clear_t > 0: clear_t -= 1
        if done_t  > 0: done_t  -= 1

        lv   = LEVELS[cur_level]
        C    = lv["colors"]
        maze = lv["maze"]
        ROWS = lv["rows"]
        COLS = lv["cols"]
        tgt  = find_target(maze)

        # Camera: always centred on player, smooth lerp, no clamping
        # The maze is always bigger than the screen so we never see the edges
        target_cam_x = float(px * TILE) - W / 2 + TILE / 2
        target_cam_y = float(py * TILE) - H / 2 + TILE / 2
        cam_x += (target_cam_x - cam_x) * 0.15
        cam_y += (target_cam_y - cam_y) * 0.15
        off_x = int(cam_x)
        off_y = int(cam_y)

        # Close overlay after success jingle
        if close_overlay > 0 and glow >= close_overlay:
            close_overlay = -1
            state = "LEVEL_CLEAR"
            clear_t = 220
            snd_lvclear.play()

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

            if event.type == pygame.KEYDOWN:

                # Waiting for keybind re-assignment
                if waiting_key is not None:
                    if event.key != pygame.K_ESCAPE:
                        binds[waiting_key][0] = event.key  # overwrite primary
                    waiting_key = None
                    continue

                # ─ MENU ─
                if state == "MENU":
                    if event.key in (pygame.K_UP,   pygame.K_w): menu_sel = (menu_sel-1)%len(MENU_ITEMS); snd_nav.play()
                    if event.key in (pygame.K_DOWN, pygame.K_s): menu_sel = (menu_sel+1)%len(MENU_ITEMS); snd_nav.play()
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        snd_select.play()
                        item = MENU_ITEMS[menu_sel]
                        if item == "START GAME":
                            cur_level = 0; total_score = 0
                            load_level(0); state = "LEVEL_INTRO"; intro_t = 180
                        elif item == "SETTINGS":
                            state = "SETTINGS"; settings_sel = 0
                        elif item == "KEY BINDS":
                            state = "KEYBINDS"; keybind_sel = 0
                        elif item == "QUIT":
                            running = False
                    if event.key == pygame.K_ESCAPE: running = False

                # ─ SETTINGS ─
                elif state == "SETTINGS":
                    if event.key in (pygame.K_UP,   pygame.K_w): settings_sel = (settings_sel-1)%len(SETTINGS_KEYS); snd_nav.play()
                    if event.key in (pygame.K_DOWN, pygame.K_s): settings_sel = (settings_sel+1)%len(SETTINGS_KEYS); snd_nav.play()
                    if event.key in (pygame.K_LEFT,  pygame.K_a): change_setting(SETTINGS_KEYS[settings_sel], -1); snd_nav.play()
                    if event.key in (pygame.K_RIGHT, pygame.K_d): change_setting(SETTINGS_KEYS[settings_sel],  1); snd_nav.play()
                    if event.key == pygame.K_ESCAPE: state = "MENU"

                # ─ KEYBINDS ─
                elif state == "KEYBINDS":
                    if event.key in (pygame.K_UP,   pygame.K_w): keybind_sel = (keybind_sel-1)%len(KEYBIND_KEYS); snd_nav.play()
                    if event.key in (pygame.K_DOWN, pygame.K_s): keybind_sel = (keybind_sel+1)%len(KEYBIND_KEYS); snd_nav.play()
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        waiting_key = KEYBIND_KEYS[keybind_sel]; snd_select.play()
                    if event.key == pygame.K_r:  # reset all
                        for k, v in DEFAULT_BINDS.items(): binds[k] = list(v)
                    if event.key == pygame.K_ESCAPE: state = "MENU"

                # ─ LEVEL INTRO ─
                elif state == "LEVEL_INTRO":
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE): intro_t = 1

                # ─ PLAYING ─
                elif state == "PLAYING":
                    if event.key == pygame.K_ESCAPE: state = "MENU"

                # ─ PUZZLE ─
                elif state == "PUZZLE":
                    if p_result is None:
                        if event.key == pygame.K_RETURN:
                            if p_input.strip() == active_puzzle["a"]:
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
                            if len(p_input) < 14 and event.unicode.isprintable() and event.unicode:
                                p_input += event.unicode; snd_type.play()

                # ─ LEVEL CLEAR / GAME COMPLETE ─
                elif state in ("LEVEL_CLEAR", "GAME_COMPLETE"):
                    if event.key == pygame.K_ESCAPE: state = "MENU"

        # ── Player movement ──────────────────────────────────────
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
                        if tgt and (py, px) == tgt:
                            active_puzzle = random.choice(lv["puzzles"])
                            p_input = ""; p_result = None
                            state = "PUZZLE"; snd_server.play()
                    else:
                        snd_wall.play(); mv_cd = MVDELAY // 2

        # Jingle once on success
        if p_result == "ok" and not hacked_jingle:
            hacked_jingle = True

        # ════════════════════════════════════════════════════════
        #  DRAW
        # ════════════════════════════════════════════════════════
        draw_bg_art(screen, glow)

        # ─ MENU ─────────────────────────────────────────────────
        if state == "MENU":
            ov = pygame.Surface((W, H), pygame.SRCALPHA); ov.fill((0,0,0,130)); screen.blit(ov,(0,0))

            # Title panel
            pw, ph = 600, 340
            ppx, ppy = (W-pw)//2, 60
            draw_panel(screen, ppx, ppy, pw, ph, (0, 200, 60))

            p = abs((glow%80)-40)/40.0
            tc = (0, int(160+95*p), int(50+50*p))
            draw_c(screen, "CYBER-DECK  v3.0", fn_huge, tc, W//2, ppy+55)
            draw_c(screen, "MULTI-NODE BREACH EDITION", fn_mono, (0,150,70), W//2, ppy+100)
            draw_c(screen, "-" * 52, fn_small, (0,70,28), W//2, ppy+122)

            for i, item in enumerate(MENU_ITEMS):
                sel  = (i == menu_sel)
                col  = (0,255,100) if sel else (0,160,60)
                prefix = ">> " if sel else "   "
                draw_c(screen, f"{prefix}{item}{prefix[::-1]}", fn_big, col, W//2, ppy+158+i*42)

            draw_c(screen, f"Logged in as:  {nickname.upper()}", fn_small, (0,140,50), W//2, ppy+310)
            draw_c(screen, f"Best score: {total_score}", fn_small, (0,110,40), W//2, ppy+328)

            # Node list panel
            npw, nph = 580, len(LEVELS)*28+40
            npx, npy = (W-npw)//2, ppy+ph+18
            draw_panel(screen, npx, npy, npw, nph, (0,120,40), 160)
            draw_c(screen, "TARGET NODES", fn_mono, (0,180,60), W//2, npy+18)
            for i, lv2 in enumerate(LEVELS):
                col = (0,220,80) if i < cur_level else (0,140,50)
                draw_c(screen, f"{i+1}. {lv2['name']}", fn_small, col, W//2, npy+36+i*26)

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
            draw_c(screen, f"LEVEL {cur_level+1} / {len(LEVELS)}", fn_huge, c2, W//2, H//2-80)
            draw_c(screen, lv["name"],     fn_big,  nc,         W//2, H//2-20)
            draw_c(screen, lv["subtitle"], fn_mono, (0,160,80), W//2, H//2+28)
            bc = nc if (glow//25)%2==0 else tuple(v//3 for v in nc)
            draw_c(screen, "[ ENTER / SPACE ] -- START", fn_mono, bc, W//2, H//2+85)

        # ─ PLAYING / PUZZLE / LEVEL_CLEAR ────────────────────────
        elif state in ("PLAYING", "PUZZLE", "LEVEL_CLEAR"):

            # Draw maze with camera offset
            for r in range(ROWS):
                for c in range(COLS):
                    rx = c*TILE - off_x
                    ry = r*TILE - off_y
                    if rx > W or ry > H or rx+TILE < 0 or ry+TILE < 0: continue
                    if maze[r][c] == 1:
                        pygame.draw.rect(screen, C["wall"],  (rx, ry, TILE, TILE))
                        pygame.draw.rect(screen, C["edge"],  (rx, ry, TILE, TILE), 1)
                    else:
                        pygame.draw.rect(screen, C["floor"], (rx, ry, TILE, TILE))
                        pygame.draw.rect(screen, C["grid"],  (rx, ry, TILE, TILE), 1)

            # Target server
            if tgt:
                tr, tc2 = tgt
                tx = tc2*TILE - off_x; ty = tr*TILE - off_y
                pl = abs((glow%60)-30)/30.0
                tcol = tuple(min(255, int(v+40*pl)) for v in C["target"])
                draw_glow(screen, C["target"], (tx+2,ty+2,TILE-4,TILE-4), r=10)
                pygame.draw.rect(screen, tcol, (tx+4,ty+4,TILE-8,TILE-8), border_radius=4)
                sl = fn_small.render("SRV", True, (255,225,225))
                screen.blit(sl, (tx+TILE//2-sl.get_width()//2, ty+TILE//2-sl.get_height()//2))

            # Player (always centered-ish via camera)
            ppx2 = px*TILE - off_x + 3
            ppy2 = py*TILE - off_y + 3
            ps   = TILE - 6
            draw_glow(screen, C["player"], (ppx2,ppy2,ps,ps), r=8)
            pygame.draw.rect(screen, C["player"], (ppx2,ppy2,ps,ps), border_radius=4)
            pygame.draw.rect(screen, (220,255,230), (ppx2+4,ppy2+4,ps-8,ps-8), border_radius=2)

            # Floating score texts
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

            # CRT scanline
            if settings["crt_effect"]:
                sl2 = pygame.Surface((W,2),pygame.SRCALPHA); sl2.fill((0,255,80,18))
                screen.blit(sl2,(0,scan_y))

            # HUD top
            hp = pygame.Surface((W,32),pygame.SRCALPHA); hp.fill((0,12,0,210))
            screen.blit(hp,(0,0))
            hud_txt = (f"[ CYBER-DECK v3.0 ]  {nickname.upper()}@root  |  "
                       f"Level {cur_level+1}/{len(LEVELS)}  |  Score: {total_score}  |  ESC=menu")
            screen.blit(fn_small.render(hud_txt, True, C["text"]), (8, 8))

            if settings["show_fps"]:
                fps_s = fn_small.render(f"FPS:{int(clock.get_fps())}", True, (100,100,100))
                screen.blit(fps_s, (W-60, 8))

            # HUD bottom
            bp2 = pygame.Surface((W,22),pygame.SRCALPHA); bp2.fill((0,12,0,200))
            screen.blit(bp2,(0,H-22))
            goal = "GOAL: Reach [SRV]  |  Arrow keys / WASD  |  Minimap: top-right"
            screen.blit(fn_small.render(goal, True, C["text"]), (8, H-18))

            # Minimap (top-right corner)
            MM_W, MM_H = 160, 120
            MM_X, MM_Y = W - MM_W - 8, 38
            mm_surf = pygame.Surface((MM_W, MM_H), pygame.SRCALPHA)
            mm_surf.fill((0, 0, 0, 180))
            pygame.draw.rect(mm_surf, C["edge"], (0, 0, MM_W, MM_H), 1)
            cell_w = MM_W / COLS
            cell_h = MM_H / ROWS
            for mr in range(ROWS):
                for mc in range(COLS):
                    v = maze[mr][mc]
                    if v == 1:
                        col_mm = (int(C["edge"][0]*0.5), int(C["edge"][1]*0.5), int(C["edge"][2]*0.5))
                        pygame.draw.rect(mm_surf, col_mm,
                            (int(mc*cell_w), int(mr*cell_h), max(1,int(cell_w)), max(1,int(cell_h))))
            # Target dot
            if tgt:
                tr2, tc3 = tgt
                pygame.draw.rect(mm_surf, C["target"],
                    (int(tc3*cell_w), int(tr2*cell_h), max(2,int(cell_w)+1), max(2,int(cell_h)+1)))
            # Player dot
            pygame.draw.rect(mm_surf, C["player"],
                (int(px*cell_w), int(py*cell_h), max(2,int(cell_w)+1), max(2,int(cell_h)+1)))
            screen.blit(mm_surf, (MM_X, MM_Y))

            # Fail flash
            if fail_flash > 0:
                fl = pygame.Surface((W,H),pygame.SRCALPHA)
                fl.fill((255,0,0,int(70*fail_flash/22))); screen.blit(fl,(0,0))

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
            gc = (int(40*p), int(190+65*p), int(45+55*p))
            draw_c(screen, "**  MAINFRAME SEIZED!  **",  fn_huge,  gc,         W//2, H//2-120)
            draw_c(screen, "ALL 5 NODES SUCCESSFULLY HACKED",       fn_big,  (0,225,80), W//2, H//2-60)
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

        pygame.display.flip()

    pygame.mixer.stop()
    pygame.quit()

# ════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    nick = terminal_phase()
    game_phase(nick)
