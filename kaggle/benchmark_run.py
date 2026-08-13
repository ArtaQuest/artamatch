"""
benchmark_run.py — wait for the benchmark task to build, publish it, and put the SOTA field on it.

WHAT THIS DOES, IN THE ORDER IT HAS TO HAPPEN
  1. Polls the task until its creation state is COMPLETED. Creating a benchmark task is asynchronous — the
     server builds a backing kernel and runs it once with a default model, so `creation_state` is really that
     kernel session's state. A task that is still RUNNING cannot be published or scheduled against.
  2. Publishes it, together with the backing notebook, so the grading script is readable by anyone who wants
     to argue with it.
  3. Lists every benchmark model with FULL PAGINATION and schedules a run for a chosen field of frontier
     models. Pagination matters: one page returns 20 and there are 38, so a single call quietly hides half
     the available competitors.

QUOTA IS REAL MONEY AND IT IS SMALL. `GetBenchmarkTaskQuota` reports a $10/day model-proxy allowance and the
monthly allowance is $100. Each scheduled run spends against it, and the task's own creation run has already
spent some. So the field is chosen deliberately rather than "all 38", the spend is printed before anything is
scheduled, and AQ_DO_SCHEDULE must be set for the scheduling call to fire.

CREDENTIALS ARE EXPLICIT. ~/.kaggle/kaggle.json is rewritten on a timer by ArtaSwitch and silently moved the
active account mid-sequence earlier today; a Bearer token would also beat basic auth inside the SDK and 401
these routes, so KAGGLE_API_TOKEN is cleared.

Usage:
    ~/.artamatch-venv/bin/python benchmark_run.py                    # poll, publish, list, DRY-RUN schedule
    AQ_DO_SCHEDULE=1 ~/.artamatch-venv/bin/python benchmark_run.py   # also schedule the runs
"""
import json
import os
import time

os.environ.pop("KAGGLE_API_TOKEN", None)
CR = json.load(open(os.path.expanduser("~/.kaggle/kaggle.artafather.json")))
U, K = CR["username"], CR["key"]
assert U == "artafather", U

from kagglesdk import KaggleClient
from kagglesdk.kaggle_env import KaggleEnv
from kagglesdk.benchmarks.types.benchmark_tasks_api_service import (
    ApiBatchScheduleBenchmarkTaskRunsRequest, ApiBenchmarkTaskSlug, ApiGetBenchmarkTaskQuotaRequest,
    ApiGetBenchmarkTaskRequest, ApiListBenchmarkTaskRunsRequest, ApiPublishBenchmarkTaskRequest)
from kagglesdk.benchmarks.types.benchmarks_api_service import ApiListBenchmarkModelsRequest

SLUG = "artamatch-two-birth-dates-one-shared-child"
T0 = time.time()

# The field. One flagship per lab plus a cheap one, so the comparison is across model families rather than
# across sizes of the same family — and small enough that the daily allowance is not the story.
WANT = [
    "claude-opus-5",
    "gemini-3-flash-preview",
    "deepseek-r1",
    "claude-sonnet-4-6",
    "gemini-2.5-pro",
]


def log(*a):
    print(f"[{time.time()-T0:6.1f}s]", *a, flush=True)


def kc():
    return KaggleClient(env=KaggleEnv.PROD, username=U, password=K, api_token=None)


def retry(fn, label, tries=7):
    """The link to api.kaggle.com drops about one request in three. Only a repeated HTTP verdict is an answer."""
    last = None
    for i in range(tries):
        try:
            with kc() as c:
                return fn(c)
        except Exception as e:
            last = e
            st = getattr(getattr(e, "response", None), "status_code", None)
            if st in (400, 401, 403, 404) and i >= 2:
                log(f"{label}: HTTP {st} (repeated) {str(e)[:120]}")
                return None
            time.sleep(2 * (i + 1))
    log(f"{label}: gave up after {tries} — {type(last).__name__} {str(last)[:110]}")
    return None


def task_slug(version=None):
    s = ApiBenchmarkTaskSlug()
    s.owner_slug = U
    s.task_slug = SLUG
    if version:
        s.version_number = version
    return s


def get_task():
    q = ApiGetBenchmarkTaskRequest()
    q.slug = task_slug()
    return retry(lambda c: c.benchmarks.benchmark_tasks_api_client.get_benchmark_task(q), "get_task")


def all_models():
    """Every benchmark model, paginated. One page is 20 of 38 — half the field would be invisible."""
    out, tok = [], ""
    while True:
        def f(c, tok=tok):
            r = ApiListBenchmarkModelsRequest()
            r.page_size = 50
            if tok:
                r.page_token = tok
            return c.benchmarks.benchmarks_api_client.list_benchmark_models(r)
        resp = retry(f, "list_models")
        if resp is None:
            return out
        out += list(resp.benchmark_models or [])
        tok = getattr(resp, "next_page_token", "") or ""
        if not tok:
            return out


def main():
    log("waiting for the task to finish building")
    state = ""
    for i in range(360):          # up to two hours: the creation run makes 40 model-proxy calls
        t = get_task()
        state = str(getattr(t, "creation_state", "") or "")
        if i % 3 == 0 or "COMPLETED" in state:
            log(f"  state={state.split('.')[-1]}")
        if "COMPLETED" in state:
            break
        if "FAIL" in state or "ERROR" in state or "NO_MODEL" in state:
            log(f"  creation did not succeed: {state}  error={getattr(t,'error','')}")
            return
        time.sleep(20)
    if "COMPLETED" not in state:
        log("  still not COMPLETED — stopping rather than publishing a half-built task")
        return

    q = ApiGetBenchmarkTaskQuotaRequest()
    quota = retry(lambda c: c.benchmarks.benchmark_tasks_api_client.get_benchmark_task_quota(q), "quota")
    if quota:
        log(f"  model-proxy quota: allowed {getattr(quota,'total_daily_quota_allowed','?')} / day, "
            f"used {getattr(quota,'daily_quota_used',0)}")

    pr = ApiPublishBenchmarkTaskRequest()
    pr.slug = task_slug()
    pr.publish_backing_notebook = True
    p = retry(lambda c: c.benchmarks.benchmark_tasks_api_client.publish_benchmark_task(pr), "publish")
    if p:
        log(f"  published: is_public={getattr(p,'is_public','?')} "
            f"backing_notebook={getattr(p,'is_backing_notebook_published','?')} url={getattr(p,'url','')}")

    models = all_models()
    log(f"  {len(models)} benchmark models available (paginated)")
    by = {}
    for m in models:
        for v in (getattr(m, "versions", None) or getattr(m, "model_versions", None) or []):
            vs = getattr(v, "slug", "") or ""
            if vs:
                by[vs] = getattr(m, "display_name", "") or getattr(m, "slug", "")
        ms = getattr(m, "slug", "")
        if ms and ms not in by:
            by[ms] = getattr(m, "display_name", "") or ms
    picked = []
    for w in WANT:
        exact = [s for s in by if s == w or s == f"{w}-default"]
        near = [s for s in by if s.startswith(w)]
        hit = (exact or near or [None])[0]
        if hit:
            picked.append(hit)
            log(f"    {by[hit]:<32} -> {hit}")
        else:
            log(f"    {w:<32} -> NOT AVAILABLE, skipped")
    if not picked:
        log("  no requested model resolved to a version slug — nothing to schedule")
        log(f"  available slugs: {sorted(by)[:12]} …")
        return

    if os.environ.get("AQ_DO_SCHEDULE") != "1":
        log(f"  DRY RUN — would schedule {len(picked)} runs. Set AQ_DO_SCHEDULE=1 to spend quota.")
        return
    req = ApiBatchScheduleBenchmarkTaskRunsRequest()
    req.task_slugs = [task_slug()]
    req.model_version_slugs = picked
    r = retry(lambda c: c.benchmarks.benchmark_tasks_api_client
              .batch_schedule_benchmark_task_runs(req), "schedule")
    log(f"  scheduled -> {r}")
    time.sleep(20)
    lr = ApiListBenchmarkTaskRunsRequest()
    lr.task_slug = task_slug()   # the FIELD is named task_slug but its TYPE is ApiBenchmarkTaskSlug; the
                                 # property list showing 'task_slug' is not evidence of a string
    runs = retry(lambda c: c.benchmarks.benchmark_tasks_api_client.list_benchmark_task_runs(lr), "list_runs")
    for run in (getattr(runs, "benchmark_task_runs", None) or getattr(runs, "runs", None) or []):
        log(f"    run {getattr(run,'model_version_slug','?'):<34} "
            f"{str(getattr(run,'state','?')).split('.')[-1]}")


if __name__ == "__main__":
    main()
