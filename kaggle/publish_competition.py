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


def upload(kc, path, blob_type):
    """Three steps: ask for a slot, PUT the bytes, keep the token."""
    data = open(path, "rb").read()
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
    with urllib.request.urlopen(put, timeout=900) as resp:
        if resp.status not in (200, 201):
            raise RuntimeError(f"{path}: PUT returned {resp.status}")
    print(f"    uploaded {os.path.basename(path)} ({len(data)/1e6:.2f} MB)", flush=True)
    return r.token


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
        for f in ("train.csv", "test.csv"):
            t = upload(kc, os.path.join(d, f), ApiBlobType.DATASET)
            cf = ApiCompetitionDataFile()
            cf.name = f
            cf.token = t
            files.append(cf)
        req = ApiCreateCompetitionDataRequest()
        req.competition_name = COMP
        req.version_notes = "train (80%) and test (20%), split by person group"
        req.files = files
        req.competition_databundle_type = CompetitionDatabundleType.COMPETITION_DATABUNDLE_TYPE_PUBLIC
        print("    ->", api.create_competition_data(req))

        print("  2. the answer key")
        st = ApiCreateCompetitionSolutionRequest()
        st.competition_name = COMP
        st.blob_token = upload(kc, os.path.join(d, "solution.csv"), ApiBlobType.COMPETITION_SOLUTION)
        print("    ->", api.create_competition_solution(st))

        print("  3. sample submission")
        ss = ApiCreateCompetitionSampleSubmissionRequest()
        ss.competition_name = COMP
        ss.blob_token = upload(kc, os.path.join(d, "sample_submission.csv"), ApiBlobType.DATASET)
        print("    ->", api.create_competition_sample_submission(ss))

        if launch:
            lr = ApiLaunchCompetitionRequest()
            lr.competition_name = COMP
            print("  4. launching")
            print("    ->", api.launch_competition(lr))
        else:
            print("  4. NOT launched — pass --launch when the configuration has been checked")


if __name__ == "__main__":
    main()
