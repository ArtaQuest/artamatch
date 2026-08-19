"""launch.py — push the edition-IV member-build kernels across the pool's accounts (GPU, internet), round-robin."""
import json, os, shutil, subprocess, sys, time
ACCOUNTS = ["artafather", "ashranet", "ashraasn", "arash0ash"]
MODULES = ["aboriginal_australian","african","astrocartography","babylonian_egyptian","chinese","east_asian_deep","harmonics","hellenistic","houses","indigenous_americas","lunar_calendrical","mesoamerican","modern_western","numerology","persian_arabic","polynesian","tibetan_seasia","uranian","vedic_ashtakavarga","vedic_core","vedic_match"]
# balance: harmonics alone; the rest three a kernel
shards = [["harmonics"], ["babylonian_egyptian", "east_asian_deep"], ["vedic_core", "vedic_ashtakavarga", "vedic_match"], ["hellenistic", "modern_western", "uranian"],
          ["chinese", "tibetan_seasia", "persian_arabic"], ["numerology", "lunar_calendrical", "mesoamerican", "polynesian"], ["aboriginal_australian", "african", "indigenous_americas", "astrocartography", "houses"]]
assert sorted(sum(shards, [])) == sorted(MODULES)
jobs = [("trad", k, {"AQ_JOB": "trad", "AQ_MODULES": ",".join(m), "AQ_TAG": f"_t{k}"}) for k, m in enumerate(shards)]
NS = 6
jobs += [("sid", k, {"AQ_JOB": "sid", "AQ_SHARD": f"{k}/{NS}"}) for k in range(NS)]
base = open("/tmp/aq4kg/code/kernel_job.py").read()
launched = []
for i, (kind, k, env) in enumerate(jobs):
    acct = ACCOUNTS[i % len(ACCOUNTS)]; slug = f"artamatch-iv-{kind}-{k}"; d = f"/tmp/aq4kg/kernels/{slug}"; os.makedirs(d, exist_ok=True)
    head = "import os\n" + "".join(f"os.environ[{json.dumps(a)}] = {json.dumps(b)}\n" for a, b in env.items())
    open(f"{d}/kernel.py", "w").write(head + base)
    json.dump({"id": f"{acct}/{slug}", "title": slug, "code_file": "kernel.py", "language": "python", "kernel_type": "script", "is_private": True,
               "enable_gpu": True, "enable_internet": True, "dataset_sources": ["artafather/artamatch-iv-code"], "competition_sources": [], "kernel_sources": [], "model_sources": []},
              open(f"{d}/kernel-metadata.json", "w"))
    cfg = f"/tmp/aqkg_{acct}"; os.makedirs(cfg, exist_ok=True); shutil.copy(os.path.expanduser(f"~/.kaggle/kaggle.{acct}.json"), f"{cfg}/kaggle.json"); os.chmod(f"{cfg}/kaggle.json", 0o600)
    code = f"from kaggle.api.kaggle_api_extended import KaggleApi\napi=KaggleApi(); api.authenticate()\nr=api.kernels_push({json.dumps(d)})\nprint(getattr(r,'ref',None) or r, '|', getattr(r,'url',None), '|', getattr(r,'error',None))"
    r = subprocess.run([sys.executable, "-c", code], env={**os.environ, "KAGGLE_CONFIG_DIR": cfg}, capture_output=True, text=True, timeout=300)
    out = (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else "?"
    print(f"  {acct:<10} {slug:<24} {env.get('AQ_MODULES') or env.get('AQ_SHARD'):<60} -> {out[:120]}")
    launched.append({"account": acct, "slug": slug, "env": env})
    time.sleep(2)
json.dump(launched, open("/tmp/aq4kg/launched.json", "w"), indent=1)
