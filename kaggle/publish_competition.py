"""
publish_competition.py — upload the competition's data, answer key and sample submission, then launch it.

THE ORDER MATTERS AND LAUNCHING IS LAST. `create_competition` makes an unlaunched competition that nobody can
see; the data, the solution and the sample submission go up while it is still invisible; `launch_competition`
is what makes it public. So a half-configured competition is never on show, and everything can be verified
first.

THE UPLOAD IS THREE STEPS PER FILE, not one. `start_blob_upload` returns a signed URL and a token, the bytes
go to the URL with a PUT, and the token is what the competition request refers to. The solution uses blob type
COMPETITION_SOLUTION rather than DATASET — the answer key is stored differently from the data participants
download, which is the whole point of it.

CREDENTIALS ARE PASSED EXPLICITLY, never left to ~/.kaggle/kaggle.json. ArtaSwitch rotates that file on a
timer to whichever account has GPU quota, and it silently moved the active account out from under an earlier
publishing sequence. A publish that authenticates as whoever happened to win a race is not a publish.

Usage: KAGGLE_USERNAME=... KAGGLE_KEY=... python publish_competition.py <dir-with-csvs> [--launch]
"""
import os
import sys
import time
import urllib.request

from kagglesdk import KaggleClient
from kagglesdk.blobs.types.blob_api_service import ApiBlobType, ApiStartBlobUploadRequest
from kagglesdk.competitions.types.competition_api_service import (
    ApiCompetitionDataFile, ApiCreateCompetitionDataRequest,
    ApiCreateCompetitionSampleSubmissionRequest, ApiCreateCompetitionSolutionRequest,
    ApiLaunchCompetitionRequest)
from kagglesdk.competitions.types.competition_enums import CompetitionDatabundleType

# The COMPETITION slug, which is not the dataset slug. They were the same word for long enough to cost a
# debugging session: uploading against the dataset name answers 403 "competitions.getPrivate was denied",
# which reads like a credential problem and is really a competition that this account does not host.
COMP = os.environ.get("AQ_COMP", "artamatch-astrology")
USER = os.environ["KAGGLE_USERNAME"]
KEY = os.environ["KAGGLE_KEY"]


def client():
    return KaggleClient(username=USER, password=KEY)


def upload(kc, path, blob_type, tries=6):
    """Three steps: ask for a slot, PUT the bytes, keep the token.

    RETRIED, because the link to api.kaggle.com drops roughly one request in three from here and the failure is
    an SSLEOFError rather than an HTTP status. Unretried, that took down a whole setup run mid-way and left the
    sample submission unattached — the competition looked complete while entrants had no format to copy. Only a
    repeated failure is an answer; a single one is the network.
    """
    data = open(path, "rb").read()
    last = None
    for attempt in range(tries):
        try:
            req = ApiStartBlobUploadRequest()
            req.type = blob_type
            req.name = os.path.basename(path)
            req.content_length = len(data)
            req.content_type = "text/csv"
            req.last_modified_epoch_seconds = int(os.path.getmtime(path))
            r = kc.blobs.blob_api_client.start_blob_upload(req)
            put = urllib.request.Request(r.create_url, data=data, method="PUT",
                                         headers={"Content-Type": "text/csv",
                                                  "Content-Length": str(len(data))})
            # 180s, not 900. A hung PUT on a flaky link is indistinguishable from a slow one, and a fifteen
            # minute hang burns the whole retry budget on a single attempt — failing fast and retrying moves
            # more bytes than waiting patiently does.
            with urllib.request.urlopen(put, timeout=180) as resp:
                if resp.status not in (200, 201):
                    raise RuntimeError(f"{path}: PUT returned {resp.status}")
            print(f"    uploaded {os.path.basename(path)} ({len(data)/1e6:.2f} MB)", flush=True)
            return r.token
        except Exception as e:
            last = e
            if attempt == tries - 1:
                break
            wait = 3 * (attempt + 1)
            print(f"    {os.path.basename(path)}: {type(e).__name__}, retrying in {wait}s "
                  f"({attempt+1}/{tries})", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"{path}: gave up after {tries} attempts — {type(last).__name__} {str(last)[:120]}")


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else "."
    launch = "--launch" in sys.argv
    for f in ("train.csv", "test.csv", "solution.csv", "sample_submission.csv"):
        p = os.path.join(d, f)
        if not os.path.exists(p):
            raise SystemExit(f"missing {p}")

    with client() as kc:
        api = kc.competitions.competition_api_client

        print("  1. public data (what participants download)")
        files = []
        # sample_submission.csv goes in the DATA BUNDLE, not through CreateCompetitionSampleSubmission.
        # That RPC answers 400 here and the blob enum has no sample-submission type at all — only
        # UNSPECIFIED, COMPETITION_SOLUTION, DATASET, INBOX and MODEL — so the dedicated path appears to need a
        # solution that cannot exist until the metric is set. As a data file it downloads with everything else,
        # which is where entrants look for it anyway, and it does not depend on the metric at all.
        for f in ("train.csv", "test.csv", "sample_submission.csv"):
            t = upload(kc, os.path.join(d, f), ApiBlobType.DATASET)
            cf = ApiCompetitionDataFile()
            cf.name = f
            cf.token = t
            files.append(cf)
        req = ApiCreateCompetitionDataRequest()
        req.competition_name = COMP
        req.version_notes = ("train, test and sample_submission: day-precision couples, one row each, "
                             "split by person group")
        req.files = files
        req.competition_databundle_type = CompetitionDatabundleType.COMPETITION_DATABUNDLE_TYPE_PUBLIC
        print("    ->", api.create_competition_data(req))

        print("  2. the answer key")
        st = ApiCreateCompetitionSolutionRequest()
        st.competition_name = COMP
        st.blob_token = upload(kc, os.path.join(d, "solution.csv"), ApiBlobType.COMPETITION_SOLUTION)
        # THE SOLUTION 500s UNTIL A METRIC EXISTS, and CompetitionSettings has no metric field — the server
        # itself says so: `Cannot find field "evaluation_metric" in message "kaggle.competitions.
        # CompetitionSettings"`. Letting that abort the run left the SAMPLE SUBMISSION unattached, so the
        # competition looked set up while entrants had no format to copy. Everything after this must still run.
        try:
            print("    ->", api.create_competition_solution(st))
        except Exception as e:
            code = getattr(getattr(e, "response", None), "status_code", None)
            print(f"    -> solution refused (HTTP {code}): set the metric to Area Under ROC Curve in the UI, "
                  f"then re-run. Continuing so the rest of the setup completes.")

        print("  3. sample submission — already in the data bundle above")
        try:
            ss = ApiCreateCompetitionSampleSubmissionRequest()
            ss.competition_name = COMP
            ss.blob_token = upload(kc, os.path.join(d, "sample_submission.csv"), ApiBlobType.DATASET)
            print("    ->", api.create_competition_sample_submission(ss))
        except Exception as e:
            code = getattr(getattr(e, "response", None), "status_code", None)
            print(f"    -> the dedicated RPC refused it (HTTP {code}); it ships as a data file instead, "
                  f"which is what participants download anyway")

        if launch:
            lr = ApiLaunchCompetitionRequest()
            lr.competition_name = COMP
            print("  4. launching")
            print("    ->", api.launch_competition(lr))
        else:
            print("  4. NOT launched — pass --launch when the configuration has been checked")


if __name__ == "__main__":
    main()
