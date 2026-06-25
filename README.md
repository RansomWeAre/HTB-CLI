<div align="center">

```
 ██╗  ██╗████████╗██████╗      ██████╗██╗     ██╗
 ██║  ██║╚══██╔══╝██╔══██╗    ██╔════╝██║     ██║
 ███████║   ██║   ██████╔╝    ██║     ██║     ██║
 ██╔══██║   ██║   ██╔══██╗    ██║     ██║     ██║
 ██║  ██║   ██║   ██████╔╝    ╚██████╗███████╗██║
 ╚═╝  ╚═╝   ╚═╝   ╚═════╝      ╚═════╝╚══════╝╚═╝
```
<img width="528" height="389" alt="image" src="https://github.com/user-attachments/assets/ef57d30f-0a5f-4c4e-b132-4337be7ff83b" />

# HTB CLI

**A fast, feature-rich HackTheBox command-line tool built on the official API v4**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)](https://python.org)
[![HTB API](https://img.shields.io/badge/HTB-API%20v4-9FEF00?logo=hackthebox&logoColor=black)](https://labs.hackthebox.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Author](https://img.shields.io/badge/Author-alhamrizvi--cloud-red)](https://github.com/alhamrizvi-cloud)

*Spawn machines · Get target IP · Submit flags · Snipe new releases · Track countdowns*

</div>

## ✨ Features

| Feature | Description |
|---|---|
| 🔍 **Search** | Find any active or retired machine by name |
| 📋 **Machine Info** | Detailed stats, IP, owns, rating, creators |
| 🚀 **Fast Spawn** | Spawn and poll for IP with 2-second intervals |
| 🏁 **Flag Submit** | Submit user or root flags with instant feedback |
| ⚡ **Dual Submit** | Submit both flags simultaneously in parallel threads |
| ⏱ **Countdown** | Live countdown timers to upcoming machine releases |
| 🎯 **Snipe Mode** | Auto-spawn a machine the second it releases |
| 👤 **Profile** | View your rank, points, and own counts |
| 🎨 **Rich Output** | Color-coded difficulty, OS icons, spinners |

## 📋 Requirements

- Python **3.8+**
- `requests` library
- A HackTheBox account with an **App Token**
- HTB VPN connected (for spawning machines)

## ⚙️ Installation

```bash
# 1. Clone the repo
git clone https://github.com/alhamrizvi-cloud/htb-cli.git
cd htb-cli

# 2. Install dependency
pip install requests

# 3. Set your HTB API token
export HTB_API_KEY="eyJ0eXAiOiJKV1Qi..."

# (Optional) Make permanent — add to ~/.bashrc or ~/.zshrc
echo 'export HTB_API_KEY="your_token_here"' >> ~/.bashrc
source ~/.bashrc

# 4. Run it
python3 htb.py --help
```

### Getting Your API Token

1. Log in to [app.hackthebox.com](https://app.hackthebox.com)
2. Click your profile picture → **Account Settings**
3. Scroll to **App Tokens** → click **Create App Token**
4. Name it (e.g. `htb-cli`) and copy the token — **shown once only!**

> ⚠️ Never share or commit your API token. Add `.env` to `.gitignore`.

## 🚀 Usage

### Search Machines

```bash
python3 htb.py --search devhub
python3 htb.py --search lame
python3 htb.py --search win      # partial name match
```

```
Search Results  (1 found for 'devhub')
────────────────────────────────────────────────────────────────────
  ID      Name       OS         Diff      Pts   Status    Owns
────────────────────────────────────────────────────────────────────
  903     DevHub     🐧 Linux   Medium    30    Active    U R
────────────────────────────────────────────────────────────────────
```

### Machine Info

```bash
python3 htb.py --info DevHub
python3 htb.py --info 903        # by ID
```

```
🐧 DevHub  (ID: 903)
───────────────────────────────────────────────
  OS          : Linux
  Difficulty  : Medium  (50/100)
  Points      : 30
  Target IP   : 10.10.11.X
  User Flag   : ✔ Owned
  Root Flag   : ✔ Owned
  Global Owns : 1234 user  /  987 root
  Rating      : ⭐ 4.2/5.0
───────────────────────────────────────────────
```

### Spawn a Machine

```bash
python3 htb.py --spawn DevHub
```

Polls every **2 seconds** (fast mode) until the IP is live:

```
[*] Requesting spawn for 🐧 DevHub (ID: 903) ...
[+] Polling for IP ...
  ⠼ Waiting for IP ...
[+] Machine is UP!
────────────────────────────
  Name      : DevHub
  Target IP : 10.10.11.X
  Expires   : 2026-06-25 14:00 UTC
────────────────────────────
```

### Check Active Machine

```bash
python3 htb.py --active
```

### Stop / Reset

```bash
python3 htb.py --stop DevHub
python3 htb.py --reset DevHub
```

### Submit Flags

```bash
# Submit user flag
python3 htb.py --submit DevHub -f HTB{s0m3_us3r_fl4g} --type user

# Submit root flag
python3 htb.py --submit DevHub -f HTB{r00t_fl4g_h3re} --type root

# With custom difficulty rating (1-100, default 50)
python3 htb.py --submit DevHub -f HTB{flag} --type root --diff 65
```

---

### Submit Both Flags at Once (Fastest)

```bash
python3 htb.py --pwn DevHub \
  -u HTB{us3r_fl4g_h3re} \
  -r HTB{r00t_fl4g_h3re}
```

Submits both flags **simultaneously** using parallel threads:

```
[+] USER FLAG ACCEPTED — 'DevHub' user pwned! 🎉
[+] ROOT FLAG ACCEPTED — 'DevHub' root pwned! 🎉
[+] Machine fully pwned!  User ✔  Root ✔  🔥
```

### Upcoming Releases + Countdown

```bash
python3 htb.py --upcoming
```

```
Upcoming Machine Releases
──────────────────────────────────────────────────────────────────────────
  ID      Name        OS         Diff      Release (local)       Countdown
──────────────────────────────────────────────────────────────────────────
  910     NewBox      🐧 Linux   Hard      2026-06-28 19:00 UTC  3d 2h 14m 5s
         ↳ Retiring: OldBox (Linux, Easy)
──────────────────────────────────────────────────────────────────────────
```

### Snipe Mode — Auto-Spawn at Release

```bash
python3 htb.py --snipe NewBox
```

Counts down live and fires the spawn request the **instant** the machine releases:

```
[+] Sniping armed. Will auto-spawn at release.  Ctrl+C to cancel.
  ⠙ Releasing in 3d 2h 13m 44s
  ...
[+] Release time! Spawning 'NewBox' NOW ...
[+] Machine is UP!
  Target IP : 10.10.11.Y
```

### Your Profile

```bash
python3 htb.py --profile
```

```
Your HTB Profile
───────────────────────────────
  Name     : alham  (ID: 3132553)
  Rank     : Hacker  •  Points: 1540
  Owns     : 42 user  /  38 root
  Team     : -
───────────────────────────────
```

## 📖 Full Command Reference

```
Machine operations:
  --search  QUERY       Search machines by partial name
  --info    ID/NAME     Detailed machine info + IP
  --active              Show your currently active machine
  --spawn   ID/NAME     Spawn a machine (fast 2s polling)
  --stop    ID/NAME     Stop/terminate active machine
  --reset   ID/NAME     Reset active machine

Flag submission:
  --submit  ID/NAME     Submit a single flag
  --flag/-f FLAG        Flag value (HTB{...})
  --type    user|root   Flag type (default: user)
  --pwn     ID/NAME     Submit BOTH flags simultaneously
  -u        USER_FLAG   User flag (for --pwn)
  -r        ROOT_FLAG   Root flag (for --pwn)
  --diff    1-100       Difficulty rating (default: 50)

Release tracking:
  --upcoming            Show upcoming releases with countdowns
  --snipe   ID/NAME     Wait for release, then auto-spawn

Account:
  --profile             Your HTB profile (rank, points, owns)
```


## 🔌 API Endpoints Used

| Endpoint | Purpose |
|---|---|
| `GET /machine/paginated` | Active machines list |
| `GET /machine/list/retired/paginated` | Retired machines list |
| `GET /machine/profile/<id\|name>` | Single machine lookup |
| `GET /machine/active` | Your active machine |
| `GET /machine/unreleased` | Upcoming releases |
| `POST /machine/own` | Submit flag |
| `POST /vm/spawn` | Spawn machine |
| `POST /vm/terminate` | Stop machine |
| `POST /vm/reset` | Reset machine |
| `GET /user/info` | Authenticated user profile |

---

## 🎨 Output Legend

| Symbol | Meaning |
|---|---|
| `[+]` | Success |
| `[*]` | Info / in progress |
| `[!]` | Warning |
| `[-]` | Error |
| `U` | User flag owned |
| `R` | Root flag owned |
| `✔` | Owned |
| `✘` | Not owned |

**Difficulty colors:** `Easy` = green · `Medium` = yellow · `Hard` = red · `Insane` = cyan

## 🛡️ Security Notes

- Store your token in an environment variable, **never** hardcode it
- Don't paste your token in chat, forums, or commit it to git
- Rotate your token immediately if accidentally exposed
- Use `.env` file + `python-dotenv` for local dev (see below)

```bash
# Optional: use a .env file
pip install python-dotenv
echo 'HTB_API_KEY=your_token_here' > .env
echo '.env' >> .gitignore
```

Then add to the top of `htb.py`:
```python
from dotenv import load_dotenv
load_dotenv()
```

## 🤝 Contributing

Pull requests welcome! Please:
1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m 'Add my feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

## 📚 References

- [D3vil0p3r/HackTheBox-API](https://github.com/D3vil0p3r/HackTheBox-API)
- [Propolisa/htb-api-docs](https://github.com/Propolisa/htb-api-docs)
- [clubby789/htb-api](https://github.com/clubby789/htb-api)
- [7h3rAm/machinescli](https://github.com/7h3rAm/machinescli)
- [PyHackTheBox Docs](https://pyhackthebox.readthedocs.io)

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

<div align="center">
Made with ❤️ by <a href="https://github.com/RansomWeAre">RansomWeAre Group</a>
</div>
