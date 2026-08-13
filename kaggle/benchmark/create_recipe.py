#!/usr/bin/env ~/.artamatch-venv/bin/python
"""CREATE the benchmark task "ArtaMatch: two birth dates, one shared child".

Run with:  ~/.artamatch-venv/bin/python create_recipe.py            # dry run: builds + validates only
           AQ_DO_CREATE=1 ~/.artamatch-venv/bin/python create_recipe.py   # actually POSTs

Everything before the marked block is read-only.
"""
import json
import os
import time

# ---------------------------------------------------------------- credentials (explicit, per process)
CRED = json.load(open(os.path.expanduser("~/.kaggle/kaggle.artafather.json")))
KAGGLE_USERNAME, KAGGLE_KEY = CRED["username"], CRED["key"]
assert KAGGLE_USERNAME == "artafather", KAGGLE_USERNAME
# A Bearer token beats basic auth inside the SDK and 401s against these routes: make sure there is none.
os.environ.pop("KAGGLE_API_TOKEN", None)
assert not os.path.exists(os.path.expanduser("~/.kaggle/access_token")), "an access_token file would override basic auth"

from kagglesdk import KaggleClient
from kagglesdk.kaggle_env import KaggleEnv
from kagglesdk.benchmarks.types.benchmark_tasks_api_service import (
    ApiCreateBenchmarkTaskRequest,
    ApiGetBenchmarkTaskRequest,
    ApiBenchmarkTaskSlug,
)
from kagglesdk.benchmarks.types.benchmark_types import BenchmarkTaskOptions
from kaggle.api.kaggle_api_extended import KaggleApi          # only for its two pure static helpers
from slugify import slugify

TITLE = "ArtaMatch: two birth dates, one shared child"
SLUG = slugify(TITLE)                                          # 'artamatch-two-birth-dates-one-shared-child'
DATASET = "artaquest-foundation/artamatch-two-birth-dates"     # public, CC0, 1 file: train.csv
TASK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artamatch_task.py")

# ------------------------------------------------------------------------ build + validate the payload
SOURCE = open(TASK_FILE).read()
KaggleApi._validate_task_in_file(SLUG, TASK_FILE, SOURCE)      # slug must match the @kbench.task name
NOTEBOOK = KaggleApi._convert_py_to_notebook(SOURCE)           # py:percent -> .ipynb JSON string

request = ApiCreateBenchmarkTaskRequest()
request.slug = SLUG
request.text = NOTEBOOK
options = BenchmarkTaskOptions()
options.dataset_data_sources = [DATASET]
request.options = options
# request.definition is deliberately OMITTED: a notebook-backed task is the default, and the only
# proven-accepted shape (BenchmarkTaskNotebookDefinition is an empty message; docker_image / harbor_git /
# harbor_kaggle_datasets are the other three, mutually exclusive, branches of the oneof).

print("slug :", SLUG)
print("wire :", json.dumps({k: (v if k != "text" else f"<{len(NOTEBOOK)} chars of ipynb JSON>")
                            for k, v in ApiCreateBenchmarkTaskRequest.to_dict(request).items()}, indent=2))


def call(fn, tries=6, label="call"):
    """The link to api.kaggle.com drops roughly one request in three — retry before believing anything."""
    for i in range(1, tries + 1):
        try:
            with KaggleClient(env=KaggleEnv.PROD, username=KAGGLE_USERNAME, password=KAGGLE_KEY) as k:
                assert k.http_client()._session.auth == (KAGGLE_USERNAME, KAGGLE_KEY), "not basic auth!"
                return fn(k)
        except Exception as exc:
            resp = getattr(exc, "response", None)
            status = getattr(resp, "status_code", None)
            if status in (400, 401, 403, 404, 409):            # a real answer, not the flaky link
                raise
            print(f"[{label}] attempt {i}: {type(exc).__name__}: {exc}", flush=True)
            if i == tries:
                raise
            time.sleep(min(2 ** i, 20))


# 1. refuse to clobber: this slug must not exist yet (403 == absent OR not ours, both mean "do not push")
def _probe(k):
    req = ApiGetBenchmarkTaskRequest()
    s = ApiBenchmarkTaskSlug()
    s.owner_slug = KAGGLE_USERNAME
    s.task_slug = SLUG
    req.slug = s
    return k.benchmarks.benchmark_tasks_api_client.get_benchmark_task(req)

try:
    existing = call(_probe, tries=3, label="probe")
    print("!! a task with this slug already EXISTS — pushing would create version",
          existing.slug.version_number + 1, "of it, not a new task")
except Exception as exc:
    status = getattr(getattr(exc, "response", None), "status_code", None)
    print("probe:", "absent (403/404, as expected for a new slug)" if status in (403, 404) else f"unexpected: {exc}")

# =============================== THE ONLY WRITE IN THIS FILE ========================================
if os.environ.get("AQ_DO_CREATE") == "1":
    response = call(lambda k: k.benchmarks.benchmark_tasks_api_client.create_benchmark_task(request),
                    label="CreateBenchmarkTask")
    if response.error:
        raise SystemExit(f"refused: {response.error}")
    print("created  :", f"https://www.kaggle.com{response.url}")
    print("state    :", response.creation_state)               # QUEUED -> RUNNING -> COMPLETED
    print("attached :", (response.options.dataset_data_sources if response.options else None))
    print("version  :", response.slug.version_number, "owner:", response.slug.owner_slug)
    print("\npoll with: kaggle b t status", SLUG, " (or GetBenchmarkTask until COMPLETED)")
else:
    print("\nDRY RUN — set AQ_DO_CREATE=1 to POST CreateBenchmarkTask")
# ===================================================================================================
