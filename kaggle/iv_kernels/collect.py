"""collect.py — download outputs of COMPLETE kernels (once each) into /tmp/aq4kg/out/<slug>/."""
import json, os, shutil, subprocess, sys
L = json.load(open("/tmp/aq4kg/launched.json")); state = json.load(open("/tmp/aq4kg/state.json"))
def run(acct, code):
    cfg = f"/tmp/aqkg_{acct}"; r = subprocess.run([sys.executable, "-c", code], env={**os.environ, "KAGGLE_CONFIG_DIR": cfg}, capture_output=True, text=True, timeout=900)
    return (r.stdout + r.stderr).strip()
done = 0
for j in L:
    slug, acct = j["slug"], j["account"]; st = state.get(slug, {})
    if not st.get("pushed"):
        continue
    out = run(acct, f"from kaggle.api.kaggle_api_extended import KaggleApi\napi=KaggleApi(); api.authenticate()\nr=api.kernels_status({json.dumps(acct+'/'+slug)})\nprint(str(r.status), '|', getattr(r,'failure_message','') or '')")
    st["status"] = out.splitlines()[-1] if out else "?"; state[slug] = st
    if "COMPLETE" in st["status"] and not st.get("collected"):
        d = f"/tmp/aq4kg/out/{slug}"; os.makedirs(d, exist_ok=True)
        o = run(acct, f"from kaggle.api.kaggle_api_extended import KaggleApi\napi=KaggleApi(); api.authenticate()\nprint(api.kernels_output({json.dumps(acct+'/'+slug)}, path={json.dumps(d)}, force=True, quiet=True))")
        for junk in ("code", "dm", "couples_iv.json"):
            p_ = os.path.join(d, junk); shutil.rmtree(p_, ignore_errors=True) if os.path.isdir(p_) else (os.remove(p_) if os.path.exists(p_) else None)
        files = [f for f in os.listdir(d) if f.endswith(".npz")]; st["collected"] = bool(files); print(f"  {slug:<24} COMPLETE -> {files or o[-100:]}")
    elif "ERROR" in st["status"] or "CANCEL" in st["status"]:
        print(f"  {slug:<24} {st['status'][:140]}")
    else:
        print(f"  {slug:<24} {st['status'][:60]}")
    done += 1 if st.get("collected") else 0
json.dump(state, open("/tmp/aq4kg/state.json", "w"), indent=1)
print(f"collected {done}/{len(L)}")
