"""sched.py — (re)push pending kernels as capacity frees; CPU for the sidereal feature shards. Run repeatedly."""
import json, os, shutil, subprocess, sys, time
L = json.load(open("/tmp/aq4kg/launched.json")); state_p = "/tmp/aq4kg/state.json"
state = json.load(open(state_p)) if os.path.exists(state_p) else {}
def run(acct, code):
    cfg = f"/tmp/aqkg_{acct}"; os.makedirs(cfg, exist_ok=True); shutil.copy(os.path.expanduser(f"~/.kaggle/kaggle.{acct}.json"), f"{cfg}/kaggle.json"); os.chmod(f"{cfg}/kaggle.json", 0o600)
    r = subprocess.run([sys.executable, "-c", code], env={**os.environ, "KAGGLE_CONFIG_DIR": cfg}, capture_output=True, text=True, timeout=300)
    return (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else "?"
for j in L:
    slug, acct = j["slug"], j["account"]; d = f"/tmp/aq4kg/kernels/{slug}"; meta = json.load(open(f"{d}/kernel-metadata.json"))
    if j["env"]["AQ_JOB"] == "sid" and meta["enable_gpu"]:
        meta["enable_gpu"] = False; json.dump(meta, open(f"{d}/kernel-metadata.json", "w"))
    st = state.get(slug, {"pushed": False, "status": None})
    # status of a pushed kernel
    if st["pushed"]:
        out = run(acct, f"from kaggle.api.kaggle_api_extended import KaggleApi\napi=KaggleApi(); api.authenticate()\nr=api.kernels_status({json.dumps(acct+'/'+slug)})\nprint(getattr(r,'status',r), '|', getattr(r,'failure_message',''))")
        st["status"] = out; state[slug] = st; print(f"  {acct:<10} {slug:<24} {out[:100]}"); continue
    out = run(acct, f"from kaggle.api.kaggle_api_extended import KaggleApi\napi=KaggleApi(); api.authenticate()\nr=api.kernels_push({json.dumps(d)})\nprint(getattr(r,'ref',None) or r, '|', getattr(r,'error',None))")
    ok = "Maximum" not in out and "error" not in out.lower().split("|")[-1] if "|" in out else "Maximum" not in out
    st["pushed"] = bool(ok); state[slug] = st; print(f"  {acct:<10} {slug:<24} push -> {out[:110]}")
json.dump(state, open(state_p, "w"), indent=1)
