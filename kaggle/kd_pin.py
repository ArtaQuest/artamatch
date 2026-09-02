"""kd_pin.py — kaggle_dispatch.py pinned to ONE account for this session (env creds, never touching
~/.kaggle/kaggle.json), so the pool's auto-switch cannot move status/fetch to another user mid-run."""
import json, os, sys
ACCT = os.environ.get("KD_ACCOUNT", "ashraasn")
c = json.load(open(os.path.expanduser(f"~/.kaggle/kaggle.{ACCT}.json")))
assert c["username"] == ACCT, c["username"]
os.environ["KAGGLE_USERNAME"], os.environ["KAGGLE_KEY"] = c["username"], c["key"]
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import kaggle_dispatch as kd
kd.USER = ACCT; kd.CODE_DS, kd.CORPUS_DS = f"{ACCT}/artamatch-comp-code", f"{ACCT}/artamatch-comp-corpus"
cmd = sys.argv[1]
if cmd == "datasets": kd.datasets()
elif cmd == "push": kd.push(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "fit_nested.py", sys.argv[5:])
elif cmd == "status": kd.status(sys.argv[2])
elif cmd == "fetch": kd.fetch(sys.argv[2])
