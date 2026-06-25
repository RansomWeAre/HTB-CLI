#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════╗
║          HTB CLI  •  HackTheBox API v4 Tool          ║
║  Spawn • IP • Flags • Countdown • Release Sniper     ║
╚══════════════════════════════════════════════════════╝
Developer: alhamrizvi-cloud

Setup:
  pip install requests
  export HTB_API_KEY="your_app_token"   # HTB → Settings → App Tokens

Commands:
  python3 htb.py --search  <name>              Search machines
  python3 htb.py --info    <id|name>           Machine details + IP
  python3 htb.py --active                      Your active machine
  python3 htb.py --spawn   <id|name>           Spawn machine (fast poll)
  python3 htb.py --stop    <id|name>           Stop machine
  python3 htb.py --reset   <id|name>           Reset machine
  python3 htb.py --submit  <id|name> -f <flag> Submit flag (user or root)
  python3 htb.py --pwn     <id|name> -u <user_flag> -r <root_flag>
  python3 htb.py --upcoming                    Upcoming releases + countdowns
  python3 htb.py --snipe   <id|name>           Wait for release, then auto-spawn
  python3 htb.py --profile                     Your HTB profile summary

Endpoint references:
  /machine/paginated                  → active machines (paginated)
  /machine/list/retired/paginated     → retired machines (paginated)
  /machine/profile/<id|name>          → single machine lookup
  /machine/active                     → your active machine
  /machine/unreleased                 → upcoming releases
  /machine/own                        → submit flag
  /vm/spawn  /vm/terminate  /vm/reset → machine control
  /user/profile/basic/<id>            → profile (self = use /user/info)
"""

import os
import sys
import time
import json
import argparse
import threading
from datetime import datetime, timezone, timedelta

try:
    import requests
except ImportError:
    print("[!] requests not installed. Run: pip install requests")
    sys.exit(1)

# ─── ANSI Colors ──────────────────────────────────────────────────────────────

class C:
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    BLUE   = "\033[94m"
    CYAN   = "\033[96m"
    WHITE  = "\033[97m"
    GRAY   = "\033[90m"
    BOLD   = "\033[1m"
    RESET  = "\033[0m"

def ok(msg):    print(f"{C.GREEN}[+]{C.RESET} {msg}")
def info(msg):  print(f"{C.CYAN}[*]{C.RESET} {msg}")
def warn(msg):  print(f"{C.YELLOW}[!]{C.RESET} {msg}")
def err(msg):   print(f"{C.RED}[-]{C.RESET} {msg}")
def hdr(msg):   print(f"\n{C.BOLD}{C.BLUE}{msg}{C.RESET}")
def sep(n=55):  print(f"{C.GRAY}{'─'*n}{C.RESET}")

# ─── Config ───────────────────────────────────────────────────────────────────

BASE_URL = "https://labs.hackthebox.com/api/v4"
API_KEY  = os.environ.get("HTB_API_KEY", "").strip()

DIFF_COLORS = {
    "Easy":      C.GREEN,
    "Medium":    C.YELLOW,
    "Hard":      C.RED,
    "Insane":    C.CYAN,
    "Very Easy": C.GREEN,
}
OS_ICONS = {"Linux": "🐧", "Windows": "🪟", "FreeBSD": "😈", "OpenBSD": "🐡", "Android": "🤖"}

# ─── HTTP helpers ──────────────────────────────────────────────────────────────

def _headers():
    if not API_KEY:
        err("HTB_API_KEY not set!")
        print(f"  {C.YELLOW}→ export HTB_API_KEY='your_token_here'{C.RESET}")
        print(f"  {C.GRAY}  (HTB → Profile → Settings → App Tokens → Create){C.RESET}")
        sys.exit(1)
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
        "User-Agent":    "htb-cli/2.1 alhamrizvi-cloud",
    }

def _request(method, path, data=None, params=None, silent=False):
    url = f"{BASE_URL}{path}"
    try:
        r = requests.request(method, url, headers=_headers(),
                             json=data, params=params, timeout=20)
    except requests.exceptions.ConnectionError:
        if not silent:
            err("Connection failed. Check your internet / VPN connection.")
        return {}
    except requests.exceptions.Timeout:
        if not silent:
            err("Request timed out (20s). HTB might be slow — try again.")
        return {}

    status_msgs = {
        401: "Unauthorized — your API key is invalid or expired.",
        403: "Forbidden — you don't have permission for this action.",
        404: "Not Found — endpoint or resource doesn't exist.",
        422: "Unprocessable — bad request data (wrong flag format / machine state).",
        429: "Rate Limited — too many requests. Wait a moment.",
        500: "HTB server error (500). Try again shortly.",
        503: "HTB service unavailable (503). Down for maintenance?",
    }

    if r.status_code in status_msgs:
        if not silent:
            err(f"HTTP {r.status_code}: {status_msgs[r.status_code]}")
            try:
                body   = r.json()
                detail = body.get("message") or body.get("error") or ""
                if detail and not isinstance(detail, list):
                    print(f"  {C.GRAY}Detail: {detail}{C.RESET}")
            except Exception:
                pass
        return {}

    try:
        return r.json()
    except Exception:
        if not silent:
            err(f"Non-JSON response ({r.status_code}): {r.text[:300]}")
        return {}

def get(path, params=None, silent=False):
    return _request("GET", path, params=params, silent=silent)

def post(path, data=None, silent=False):
    return _request("POST", path, data=data, silent=silent)

def _fetch_all_pages(endpoint):
    """
    Fetch all pages from a paginated HTB endpoint.
    Returns a flat list of machine dicts.
    HTB paginated endpoints return: { data: [...], meta: { last_page: N } }
    """
    all_items = []
    page = 1
    while True:
        resp = get(endpoint, params={"page": page, "per_page": 100}, silent=True)
        items = resp.get("data", [])
        if not items:
            break
        all_items.extend(items)
        meta      = resp.get("meta", {}) or {}
        last_page = meta.get("last_page", 1)
        if page >= last_page:
            break
        page += 1
    return all_items

# ─── Time helpers ──────────────────────────────────────────────────────────────

def parse_utc(s):
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None

def countdown_str(dt):
    now  = datetime.now(timezone.utc)
    diff = dt - now
    if diff.total_seconds() <= 0:
        return f"{C.GREEN}Released{C.RESET}"
    total_s = int(diff.total_seconds())
    d, rem  = divmod(total_s, 86400)
    h, rem  = divmod(rem, 3600)
    m, s    = divmod(rem, 60)
    parts   = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    parts.append(f"{s}s")
    return f"{C.YELLOW}" + " ".join(parts) + f"{C.RESET}"

def fmt_dt(dt):
    if not dt:
        return "N/A"
    return dt.astimezone().strftime("%Y-%m-%d %H:%M %Z")

# ─── Machine resolution ────────────────────────────────────────────────────────

_machine_cache = {}

def resolve_machine(id_or_name: str) -> dict:
    """Return machine info dict given a numeric ID or machine name."""
    key = id_or_name.lower().strip()
    if key in _machine_cache:
        return _machine_cache[key]

    # By numeric ID — fastest: direct profile lookup
    if id_or_name.strip().isdigit():
        data = get(f"/machine/profile/{id_or_name.strip()}")
        m = data.get("info", {})
        if m:
            _machine_cache[key] = m
            return m

    # By name — try direct profile endpoint first (HTB supports name lookup)
    data = get(f"/machine/profile/{id_or_name.strip()}", silent=True)
    m = data.get("info", {})
    if m:
        _machine_cache[key] = m
        return m

    # Fallback: scan paginated active list
    info(f"Scanning active machines for '{id_or_name}' ...")
    for m in _fetch_all_pages("/machine/paginated"):
        if m.get("name", "").lower() == key:
            _machine_cache[key] = m
            return m

    # Fallback: scan paginated retired list
    info(f"Scanning retired machines for '{id_or_name}' ...")
    for m in _fetch_all_pages("/machine/list/retired/paginated"):
        if m.get("name", "").lower() == key:
            _machine_cache[key] = m
            return m

    err(f"Machine '{id_or_name}' not found. Use --search to find machines.")
    sys.exit(1)

# ─── Display helpers ───────────────────────────────────────────────────────────

def diff_colored(text):
    c = DIFF_COLORS.get(str(text), C.WHITE)
    return f"{c}{text}{C.RESET}"

def os_icon(name):
    return OS_ICONS.get(name, "💻")

def own_badge(owned):
    return f"{C.GREEN}✔ Owned{C.RESET}" if owned else f"{C.GRAY}✘ Not owned{C.RESET}"

def spinner_frames():
    frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    i = 0
    while True:
        yield frames[i % len(frames)]
        i += 1

# ─── Commands ──────────────────────────────────────────────────────────────────

def banner():
    print(f"""
{C.BOLD}{C.GREEN} ██╗  ██╗████████╗██████╗      ██████╗██╗     ██╗{C.RESET}
{C.BOLD}{C.GREEN} ██║  ██║╚══██╔══╝██╔══██╗    ██╔════╝██║     ██║{C.RESET}
{C.BOLD}{C.GREEN} ███████║   ██║   ██████╔╝    ██║     ██║     ██║{C.RESET}
{C.BOLD}{C.GREEN} ██╔══██║   ██║   ██╔══██╗    ██║     ██║     ██║{C.RESET}
{C.BOLD}{C.GREEN} ██║  ██║   ██║   ██████╔╝    ╚██████╗███████╗██║{C.RESET}
{C.BOLD}{C.GREEN} ╚═╝  ╚═╝   ╚═╝   ╚═════╝      ╚═════╝╚══════╝╚═╝{C.RESET}
{C.GRAY}         API v4 CLI  •  Developer: alhamrizvi-cloud{C.RESET}
""")


# ── --profile ─────────────────────────────────────────────────────────────────
def cmd_profile():
    # /user/info is the correct endpoint for the authenticated user's own profile
    data = get("/user/info")
    u = data.get("info", {})
    if not u:
        err("Could not retrieve profile. Check your API key.")
        return
    hdr("Your HTB Profile")
    sep()
    print(f"  {C.BOLD}Name     :{C.RESET} {u.get('name')}  (ID: {u.get('id')})")
    print(f"  {C.BOLD}Rank     :{C.RESET} {C.YELLOW}{u.get('rank','?')}{C.RESET}  •  Points: {C.CYAN}{u.get('points','?')}{C.RESET}")
    print(f"  {C.BOLD}Respects :{C.RESET} {u.get('respects','?')}")
    print(f"  {C.BOLD}Owns     :{C.RESET} {C.GREEN}{u.get('user_owns',0)} user{C.RESET}  /  {C.RED}{u.get('system_owns',0)} root{C.RESET}")
    team = u.get("team")
    if team:
        print(f"  {C.BOLD}Team     :{C.RESET} {team.get('name','?')}")
    sep()


# ── --search ──────────────────────────────────────────────────────────────────
def cmd_search(query: str):
    info(f"Searching for '{query}' (fetching active machines) ...")
    active  = _fetch_all_pages("/machine/paginated")
    info(f"Fetching retired machines ...")
    retired = _fetch_all_pages("/machine/list/retired/paginated")
    all_machines = active + retired

    q = query.lower()
    results = [m for m in all_machines if q in m.get("name", "").lower()]

    if not results:
        warn(f"No machines found matching '{query}'")
        info("Tip: search is case-insensitive and matches partial names.")
        return

    hdr(f"Search Results  ({len(results)} found for '{query}')")
    sep(72)
    print(f"  {C.BOLD}{'ID':<7} {'Name':<20} {'OS':<10} {'Diff':<10} {'Pts':<5} {'Status':<10} Owns{C.RESET}")
    sep(72)
    for m in results:
        status = f"{C.GRAY}Retired{C.RESET}" if m.get("retired") else f"{C.GREEN}Active{C.RESET}"
        d_text = m.get("difficultyText", "?")
        u_own  = m.get("authUserInUserOwns")
        r_own  = m.get("authUserInRootOwns")
        owns   = (f"{C.GREEN}U{C.RESET}" if u_own else " ") + (f" {C.RED}R{C.RESET}" if r_own else "  ")
        print(f"  {str(m.get('id','?')):<7} {m.get('name','?'):<20} "
              f"{os_icon(m.get('os','?'))} {m.get('os','?'):<8} "
              f"{diff_colored(d_text):<20} {str(m.get('points','?')):<5} "
              f"{status:<20} {owns}")
    sep(72)


# ── --info ────────────────────────────────────────────────────────────────────
def cmd_info(id_or_name: str):
    info(f"Fetching machine info for '{id_or_name}' ...")
    m    = resolve_machine(id_or_name)
    play = m.get("playInfo", {}) or {}

    hdr(f"{os_icon(m.get('os','?'))} {m.get('name')}  (ID: {m.get('id')})")
    sep()
    print(f"  {C.BOLD}OS          :{C.RESET} {m.get('os','?')}")
    print(f"  {C.BOLD}Difficulty  :{C.RESET} {diff_colored(m.get('difficultyText','?'))}  ({m.get('difficulty','?')}/100)")
    print(f"  {C.BOLD}Points      :{C.RESET} {C.CYAN}{m.get('points','?')}{C.RESET}  (static: {m.get('static_points','?')})")
    print(f"  {C.BOLD}Free Tier   :{C.RESET} {'Yes' if m.get('free') else 'No'}")
    released = parse_utc(m.get("release", ""))
    if released:
        print(f"  {C.BOLD}Released    :{C.RESET} {fmt_dt(released)}")
    print(f"  {C.BOLD}Status      :{C.RESET} {'Retired' if m.get('retired') else C.GREEN+'Active'+C.RESET}")
    sep()

    ip = m.get("ip")
    print(f"  {C.BOLD}Target IP   :{C.RESET} {C.GREEN+str(ip)+C.RESET if ip else C.GRAY+'Not spawned'+C.RESET}")
    if play.get("isSpawned"):
        expires = parse_utc(play.get("expires_at", ""))
        print(f"  {C.BOLD}Expires     :{C.RESET} {fmt_dt(expires)}")
    print(f"  {C.BOLD}Spawned     :{C.RESET} {'Yes' if play.get('isSpawned') else 'No'}")
    sep()

    print(f"  {C.BOLD}User Flag   :{C.RESET} {own_badge(m.get('authUserInUserOwns'))}")
    print(f"  {C.BOLD}Root Flag   :{C.RESET} {own_badge(m.get('authUserInRootOwns'))}")
    print(f"  {C.BOLD}Global Owns :{C.RESET} {C.GREEN}{m.get('user_owns_count','?')} user{C.RESET}  /  {C.RED}{m.get('root_owns_count','?')} root{C.RESET}")
    sep()

    makers = []
    if m.get("maker"):  makers.append(m["maker"].get("name", "?"))
    if m.get("maker2"): makers.append(m["maker2"].get("name", "?"))
    if makers:
        print(f"  {C.BOLD}Creator(s)  :{C.RESET} {', '.join(makers)}")
    print(f"  {C.BOLD}Rating      :{C.RESET} ⭐ {m.get('stars','?')}/5.0")
    sep()


# ── --active ──────────────────────────────────────────────────────────────────
def cmd_active():
    # Correct endpoint: /machine/active
    data = get("/machine/active")
    m    = data.get("info")
    if not m:
        warn("No machine is currently active.")
        info("Use --spawn <name> to start one.")
        return

    hdr("Active Machine")
    sep()
    print(f"  {C.BOLD}Name    :{C.RESET} {os_icon(m.get('os',''))} {m.get('name')} (ID: {m.get('id')})")
    print(f"  {C.BOLD}IP      :{C.RESET} {C.GREEN}{m.get('ip','N/A')}{C.RESET}")
    print(f"  {C.BOLD}OS      :{C.RESET} {m.get('os','?')}")
    expires = parse_utc(m.get("expires_at", ""))
    if expires:
        now = datetime.now(timezone.utc)
        remaining = expires - now
        h, rem = divmod(int(max(remaining.total_seconds(), 0)), 3600)
        mi, s  = divmod(rem, 60)
        print(f"  {C.BOLD}Expires :{C.RESET} {fmt_dt(expires)}  ({h}h {mi}m remaining)")
    sep()


# ── --spawn ───────────────────────────────────────────────────────────────────
def cmd_spawn(id_or_name: str):
    m          = resolve_machine(id_or_name)
    machine_id = m["id"]
    name       = m["name"]

    # Check already spawned
    play = m.get("playInfo", {}) or {}
    if play.get("isSpawned") and m.get("ip"):
        ok(f"'{name}' is already spawned!")
        print(f"  {C.BOLD}Target IP : {C.GREEN}{m['ip']}{C.RESET}")
        return

    info(f"Requesting spawn for {os_icon(m.get('os',''))} {C.BOLD}{name}{C.RESET} (ID: {machine_id}) ...")

    # Use /vm/spawn with JSON body
    result = post("/vm/spawn", {"machine_id": machine_id})

    msg = result.get("message", "")
    if not result:
        warn("No response from spawn endpoint — the machine may still be starting.")
    elif isinstance(msg, str) and ("already" in msg.lower() or "active" in msg.lower()):
        warn(f"HTB: {msg}")
        info("Polling for existing active machine IP ...")
    elif msg:
        info(f"Spawn response: {msg}")

    # Fast polling: 2s for first 30s, then 5s for next 90s
    ok("Polling for IP ...")
    spin         = spinner_frames()
    poll_schedule = [2]*15 + [5]*18  # 30s fast + 90s slow = 2m total

    for delay in poll_schedule:
        time.sleep(delay)
        frame = next(spin)
        print(f"  {C.CYAN}{frame}{C.RESET} Waiting for IP ...", end="\r", flush=True)

        # Check via profile
        fresh = get(f"/machine/profile/{machine_id}", silent=True).get("info", {})
        ip    = fresh.get("ip")
        play2 = fresh.get("playInfo", {}) or {}
        if ip and play2.get("isSpawned"):
            print(" " * 45, end="\r")
            ok(f"{C.BOLD}Machine is UP!{C.RESET}")
            sep()
            print(f"  {C.BOLD}Name      : {fresh.get('name')}{C.RESET}")
            print(f"  {C.BOLD}Target IP : {C.GREEN}{C.BOLD}{ip}{C.RESET}")
            expires = parse_utc(play2.get("expires_at", ""))
            if expires:
                print(f"  {C.BOLD}Expires   :{C.RESET} {fmt_dt(expires)}")
            sep()
            return

        # Also check /machine/active as fallback
        active_data = get("/machine/active", silent=True).get("info") or {}
        if str(active_data.get("id")) == str(machine_id) and active_data.get("ip"):
            print(" " * 45, end="\r")
            ok(f"{C.BOLD}Machine is UP!{C.RESET}")
            sep()
            print(f"  {C.BOLD}Name      : {active_data.get('name')}{C.RESET}")
            print(f"  {C.BOLD}Target IP : {C.GREEN}{C.BOLD}{active_data.get('ip')}{C.RESET}")
            sep()
            return

    print(" " * 45, end="\r")
    warn("Timed out waiting for IP (~2 min). Machine may still be starting.")
    info("Run:  python3 htb.py --active")


# ── --stop ────────────────────────────────────────────────────────────────────
def cmd_stop(id_or_name: str):
    m = resolve_machine(id_or_name)
    info(f"Stopping '{m['name']}' (ID: {m['id']}) ...")
    result = post("/vm/terminate", {"machine_id": m["id"]})
    msg = result.get("message", "")
    if not result:
        warn("No response — machine may already be stopped.")
    elif "success" in str(msg).lower() or result.get("success"):
        ok(f"'{m['name']}' stopped successfully.")
    else:
        ok(f"Terminate sent. {msg or ''}")


# ── --reset ───────────────────────────────────────────────────────────────────
def cmd_reset(id_or_name: str):
    m = resolve_machine(id_or_name)
    info(f"Resetting '{m['name']}' (ID: {m['id']}) ...")
    result = post("/vm/reset", {"machine_id": m["id"]})
    msg = result.get("message", "")
    ok(f"Reset: {msg}" if msg else "Reset request sent.")


# ── --submit & --pwn ──────────────────────────────────────────────────────────
def _do_submit(machine_id, name, flag, flag_type, difficulty):
    """Submit one flag. Returns True on success."""
    payload = {"id": machine_id, "flag": flag.strip(), "difficulty": difficulty}
    result  = post("/machine/own", payload, silent=True)

    if not result:
        err(f"No response submitting {flag_type} flag. Is the machine spawned and active?")
        return False

    msg       = result.get("message", "")
    msg_lower = str(msg).lower()

    # Check NEGATIVES first — "Incorrect" contains "correct" so order is critical
    if "incorrect" in msg_lower or "wrong" in msg_lower or "invalid flag" in msg_lower:
        err(f"{flag_type.upper()} flag incorrect ✘  Double-check and try again.")
        if msg and not isinstance(msg, list):
            print(f"  {C.GRAY}Server: {msg}{C.RESET}")
        return False
    elif "already" in msg_lower:
        warn(f"You already own {flag_type} on '{name}'. (Counted as success)")
        return True
    elif "not found" in msg_lower or "no query" in msg_lower:
        err(f"Machine not found or not active. Is '{name}' spawned?")
        return False
    # Then check POSITIVES
    elif isinstance(msg, list) or "correct" in msg_lower or "owned" in msg_lower \
         or result.get("success") is True:
        ok(f"{C.BOLD}{C.GREEN}{flag_type.upper()} FLAG ACCEPTED{C.RESET} — '{name}' {flag_type} pwned! 🎉")
        return True
    else:
        warn(f"Unexpected server response for {flag_type}:")
        print(f"  {C.GRAY}{json.dumps(result, indent=2)}{C.RESET}")
        return False


def cmd_submit(id_or_name: str, flag: str, flag_type: str, difficulty: int):
    m = resolve_machine(id_or_name)
    info(f"Submitting {flag_type} flag for {os_icon(m.get('os',''))} {C.BOLD}{m['name']}{C.RESET} ...")
    _do_submit(m["id"], m["name"], flag, flag_type, difficulty)


def cmd_pwn(id_or_name: str, user_flag: str, root_flag: str, difficulty: int):
    m          = resolve_machine(id_or_name)
    machine_id = m["id"]
    name       = m["name"]

    hdr(f"Submitting both flags for {os_icon(m.get('os',''))} {name}")
    sep()

    results = {}

    def submit_user():
        results["user"] = _do_submit(machine_id, name, user_flag, "user", difficulty)

    def submit_root():
        results["root"] = _do_submit(machine_id, name, root_flag, "root", difficulty)

    # Submit both in parallel for speed
    t1 = threading.Thread(target=submit_user)
    t2 = threading.Thread(target=submit_root)
    t1.start(); t2.start()
    t1.join();  t2.join()

    sep()
    u_ok = results.get("user", False)
    r_ok = results.get("root", False)
    if u_ok and r_ok:
        ok(f"{C.BOLD}Machine fully pwned!{C.RESET}  User ✔  Root ✔  🔥")
    elif u_ok:
        warn("User owned ✔ — root flag failed ✘")
    elif r_ok:
        warn("Root owned ✔ — user flag failed ✘")
    else:
        err("Both submissions failed. Check your flags and machine state.")


# ── --upcoming ────────────────────────────────────────────────────────────────
def cmd_upcoming():
    info("Fetching upcoming machine releases ...")
    # Correct endpoint: /machine/unreleased
    data     = get("/machine/unreleased")
    machines = data.get("data", [])

    if not machines:
        warn("No upcoming machines scheduled right now.")
        return

    hdr("Upcoming Machine Releases")
    sep(74)
    print(f"  {C.BOLD}{'ID':<7} {'Name':<20} {'OS':<10} {'Diff':<10} {'Release (local)':<22} Countdown{C.RESET}")
    sep(74)
    for m in machines:
        release_dt = parse_utc(m.get("release", ""))
        cd_str     = countdown_str(release_dt) if release_dt else f"{C.GRAY}Unknown{C.RESET}"
        rel_str    = fmt_dt(release_dt) if release_dt else "?"
        d_text     = m.get("difficulty_text", "?")
        retiring   = m.get("retiring", {}) or {}
        print(f"  {str(m.get('id','?')):<7} {m.get('name','?'):<20} "
              f"{os_icon(m.get('os','?'))} {m.get('os','?'):<8} "
              f"{diff_colored(d_text):<20} {rel_str:<22} {cd_str}")
        if retiring:
            print(f"  {C.GRAY}         ↳ Retiring: {retiring.get('name','?')} "
                  f"({retiring.get('os','?')}, {retiring.get('difficulty_text','?')}){C.RESET}")
    sep(74)
    info("Use --snipe <name> to auto-spawn the moment it releases.")


# ── --snipe ───────────────────────────────────────────────────────────────────
def cmd_snipe(id_or_name: str):
    """Wait for a machine's release time then instantly spawn it."""
    info(f"Looking up upcoming releases for '{id_or_name}' ...")
    data     = get("/machine/unreleased")
    machines = data.get("data", [])

    target = None
    q = id_or_name.lower().strip()
    for m in machines:
        if m.get("name", "").lower() == q or str(m.get("id", "")) == q:
            target = m
            break

    if not target:
        err(f"'{id_or_name}' not found in upcoming releases.")
        if machines:
            info("Available upcoming machines:")
            for m in machines:
                release_dt = parse_utc(m.get("release", ""))
                cd = countdown_str(release_dt) if release_dt else "?"
                print(f"  • {C.BOLD}{m.get('name')}{C.RESET} (ID: {m.get('id')}) — releases in {cd}")
        sys.exit(1)

    release_dt = parse_utc(target.get("release", ""))
    machine_id = target["id"]
    name       = target["name"]

    if not release_dt:
        err("No release time found for this machine.")
        sys.exit(1)

    now = datetime.now(timezone.utc)
    if release_dt <= now:
        warn(f"'{name}' has already been released! Spawning now ...")
        cmd_spawn(str(machine_id))
        return

    hdr(f"SNIPE MODE — {os_icon(target.get('os',''))} {name} (ID: {machine_id})")
    sep()
    print(f"  {C.BOLD}OS          :{C.RESET} {target.get('os','?')}")
    print(f"  {C.BOLD}Difficulty  :{C.RESET} {diff_colored(target.get('difficulty_text','?'))}")
    print(f"  {C.BOLD}Release UTC :{C.RESET} {fmt_dt(release_dt)}")
    sep()
    ok("Sniping armed. Will auto-spawn at release.  Ctrl+C to cancel.")

    spin = spinner_frames()
    while True:
        now  = datetime.now(timezone.utc)
        diff = (release_dt - now).total_seconds()
        cd   = countdown_str(release_dt)
        print(f"  {C.CYAN}{next(spin)}{C.RESET} Releasing in {cd}        ", end="\r", flush=True)

        if diff <= 0:
            print(" " * 60, end="\r")
            ok(f"{C.BOLD}Release time! Spawning '{name}' NOW ...{C.RESET}")
            time.sleep(1.5)   # let HTB flip the machine to spawnable state
            cmd_spawn(str(machine_id))
            return
        elif diff <= 10:
            time.sleep(0.5)
        elif diff <= 60:
            time.sleep(1)
        else:
            time.sleep(5)


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    banner()

    p = argparse.ArgumentParser(
        prog="htb.py",
        description="HackTheBox CLI — spawn targets, submit flags, snipe releases",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    g = p.add_argument_group("Machine operations")
    g.add_argument("--search",  metavar="QUERY",   help="Search machines by name")
    g.add_argument("--info",    metavar="ID/NAME",  help="Detailed machine info + IP")
    g.add_argument("--active",  action="store_true",help="Show your active machine")
    g.add_argument("--spawn",   metavar="ID/NAME",  help="Spawn a machine (fast poll)")
    g.add_argument("--stop",    metavar="ID/NAME",  help="Stop/terminate active machine")
    g.add_argument("--reset",   metavar="ID/NAME",  help="Reset active machine")

    g2 = p.add_argument_group("Flag submission")
    g2.add_argument("--submit", metavar="ID/NAME",  help="Submit a single flag")
    g2.add_argument("--flag","-f", metavar="FLAG",  help="Flag value  (use with --submit)")
    g2.add_argument("--type",   metavar="user|root",help="Flag type   (default: user)")
    g2.add_argument("--pwn",    metavar="ID/NAME",  help="Submit BOTH flags at once")
    g2.add_argument("-u",       metavar="USER_FLAG",dest="user_flag", help="User flag (for --pwn)")
    g2.add_argument("-r",       metavar="ROOT_FLAG",dest="root_flag", help="Root flag (for --pwn)")
    g2.add_argument("--diff",   metavar="1-100",    help="Difficulty rating (default: 50)", type=int, default=50)

    g3 = p.add_argument_group("Release tracking")
    g3.add_argument("--upcoming",action="store_true",help="Show upcoming releases + countdowns")
    g3.add_argument("--snipe",  metavar="ID/NAME",  help="Wait for release, then auto-spawn")

    g4 = p.add_argument_group("Account")
    g4.add_argument("--profile",action="store_true",help="Your HTB profile summary")

    args = p.parse_args()

    try:
        if args.search:
            cmd_search(args.search)
        elif args.info:
            cmd_info(args.info)
        elif args.active:
            cmd_active()
        elif args.spawn:
            cmd_spawn(args.spawn)
        elif args.stop:
            cmd_stop(args.stop)
        elif args.reset:
            cmd_reset(args.reset)
        elif args.submit:
            if not args.flag:
                err("--flag / -f is required with --submit"); sys.exit(1)
            flag_type = (args.type or "user").lower()
            if flag_type not in ("user", "root"):
                err("--type must be 'user' or 'root'"); sys.exit(1)
            if not 1 <= args.diff <= 100:
                err(f"--diff must be between 1 and 100 (got {args.diff})"); sys.exit(1)
            cmd_submit(args.submit, args.flag, flag_type, args.diff)
        elif args.pwn:
            if not args.user_flag or not args.root_flag:
                err("--pwn requires both -u <user_flag> and -r <root_flag>"); sys.exit(1)
            if not 1 <= args.diff <= 100:
                err(f"--diff must be between 1 and 100 (got {args.diff})"); sys.exit(1)
            cmd_pwn(args.pwn, args.user_flag, args.root_flag, args.diff)
        elif args.upcoming:
            cmd_upcoming()
        elif args.snipe:
            cmd_snipe(args.snipe)
        elif args.profile:
            cmd_profile()
        else:
            p.print_help()

    except KeyboardInterrupt:
        print(f"\n\n{C.YELLOW}[!] Interrupted.{C.RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
