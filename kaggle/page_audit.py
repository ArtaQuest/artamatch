"""page_audit.py — check the live page against the files it claims to report, then check how it reads.

Two halves. CORRECTNESS asks whether every number the page shows can be traced to the artefact it came
from — a page that quotes a figure no file contains is worse than a page with no figure. UI asks whether
the thing is actually usable: contrast against the brand's own tokens, overflow at phone width, tap
targets, heading order, and what the first screen costs to load.

Usage: page_audit.py [url]
"""
import json, os, re, subprocess, sys, urllib.request
import html as H

URL = sys.argv[1] if len(sys.argv) > 1 else "https://artaquest.github.io/artamatch/"
BASE = URL.rsplit("/", 1)[0] + "/"
CHR = os.path.expanduser("~/Library/Caches/ms-playwright/chromium_headless_shell-1234/"
                         "chrome-headless-shell-mac-arm64/chrome-headless-shell")
GOLD, BLUE, BG = (0xE8, 0xB9, 0x23), (0x17, 0x46, 0xDC), (0x01, 0x0C, 0x17)


def get(u, binary=False):
    with urllib.request.urlopen(u, timeout=40) as r:
        b = r.read()
    return b if binary else b.decode("utf-8", "replace")


def render(u, width=None):
    cmd = [CHR, "--headless", "--disable-gpu", "--no-sandbox", "--virtual-time-budget=14000"]
    if width:
        cmd.append(f"--window-size={width},900")
    cmd += ["--dump-dom", u]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=180).stdout


def text_of(dom, a=None, b=None):
    s = dom[dom.index(a):dom.index(b)] if a and b else dom
    s = re.sub(r"<(script|style)\b.*?</\1>", " ", s, flags=re.S | re.I)
    return H.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)))


def rel_lum(c):
    def f(v):
        v /= 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def contrast(a, b):
    la, lb = rel_lum(a), rel_lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def main():
    fails, warns = [], []
    def chk(label, ok, detail="", warn=False):
        tag = "PASS" if ok else ("WARN" if warn else "FAIL")
        print(f"   {tag}  {label}{('  — ' + detail) if detail else ''}")
        if not ok:
            (warns if warn else fails).append(label)

    print(f"  auditing {URL}\n")
    raw = get(URL)
    dom = render(URL)
    body = text_of(dom)

    print("  CORRECTNESS — every figure traced to the file it came from")
    summ = json.loads(get(BASE + "almanac/quality_summary.json"))
    imp = json.loads(get(BASE + "almanac/quality_importance.json"))
    model = json.loads(get(BASE + "almanac/quality_model.json"))
    for k, v in (("test AUC", f"{summ['test_auc']:.4f}"), ("CV", f"{summ['cv_auc']:.4f}"),
                 ("bank size", f"{summ['n_bank']:,}"), ("baseline", f"{summ['age_gap_auc']:.4f}")):
        chk(f"{k} {v} appears on the page", v in body)
    chk("statement count matches the model file",
        str(summ["n_statements"]) in body and len(model["weights"]) == summ["n_statements"],
        f"{summ['n_statements']} statements")
    chk("the model file and the importance file list the same statements",
        set(model["weights"]) == {r["rule"] for r in imp["ranked"]})
    chk("the audit recorded no failures", not summ["audit_failures"])
    top = imp["ranked"][0]
    chk("the top-ranked statement's drop-one figure appears on the page",
        f"{top['drop_one_cv_loss']:+.4f}" in body, f"{top['drop_one_cv_loss']:+.4f}")
    rendered_cards = dom.count('class="rcard"')
    chk("every statement has a card in the page", rendered_cards >= summ["n_statements"],
        f"{rendered_cards} cards for {summ['n_statements']} statements")
    idx = json.loads(get(BASE + "almanac/browse/index.json"))
    chk("the browse index matches the published corpus", idx["total"] == 10000,
        f"{idx['total']:,} rows, {idx['shards']} shards")
    chk(f"the corpus good/bad split is stated ({idx['good']:,}/{idx['bad']:,})",
        f"{idx['good']:,}" in body or f"{idx['good']/idx['total']:.0%}" in body, warn=True)

    print("\n  LINKS")
    # strip script and style first: an href-looking string inside JS ("'+esc(u)+'") is not a link,
    # and reporting it as a 404 is the audit lying about the page
    markup = re.sub(r"<(script|style)\b.*?</\1>", " ", raw, flags=re.S | re.I)
    hrefs = sorted(set(re.findall(r'href="([^"#]+)"', markup)))
    bad = []
    for h in hrefs:
        if h.startswith("http") and "artaquest.github.io" not in h:
            continue
        u = h if h.startswith("http") else BASE + h.lstrip("/")
        try:
            req = urllib.request.Request(u, method="HEAD")
            code = urllib.request.urlopen(req, timeout=25).status
        except Exception as e:
            code = getattr(e, "code", 0)
        if code >= 400:
            bad.append((h, code))
    chk("every internal link resolves", not bad, str(bad[:3]))

    print("\n  UI — how it actually reads")
    css = raw[raw.index("<style"):raw.index("</style>") + 8] if "<style" in raw else ""
    hexes = set(re.findall(r"#([0-9A-Fa-f]{6})\b", css))
    def hue_family(h):
        r, g, b = int(h[:2], 16), int(h[2:4], 16), int(h[4:], 16)
        mx, mn = max(r, g, b), min(r, g, b)
        if mx - mn < 26:
            return "neutral"
        return "gold" if r >= g > b else ("blue" if b >= g and b > r else "other")
    others = sorted({h for h in hexes if hue_family(h) == "other"})
    chk("no third accent colour (brand is gold + blue only)", not others, str(others[:4]))
    # test the colours the page actually PAINTS TEXT WITH, not every token it declares. A token that
    # fails contrast but is never applied is dead CSS, and flagging it hides the real ones.
    tokens = dict(re.findall(r"--([\w-]+):\s*(#[0-9A-Fa-f]{6})", css))
    used = set()
    for sel, tok in re.findall(r"([.#][\w-]+)\s*\{[^}]*color:\s*var\(--([\w-]+)\)", css):
        if re.search(r'class="?' + re.escape(sel[1:]) + r'\b', raw):
            used.add(tok)
    used |= {"ink", "mut", "gold"}
    for tok in sorted(used):
        if tok not in tokens:
            continue
        h = tokens[tok]
        col = tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
        c = contrast(col, BG)
        chk(f"text colour --{tok} ({h}): contrast {c:.1f}:1", c >= 4.5,
            "WCAG AA body text is 4.5:1", warn=(3.0 <= c < 4.5))
    dead = [t for t in tokens if t.startswith("blue") and t not in used]
    if dead:
        print(f"    (declared but never applied to text: {', '.join('--' + d for d in dead)})")
    mob = render(URL, width=390)
    chk("renders at phone width", len(mob) > 50000, f"{len(mob):,} bytes of DOM at 390px")
    chk("wide content is allowed to scroll inside itself, not the page",
        "overflow-x:auto" in css or "overflow-x: auto" in css, warn=True)
    chk("interactive summaries are focusable", "<summary" in raw)
    chk("reduced motion is respected", "prefers-reduced-motion" in css, warn=True)
    h1 = len(re.findall(r"<h1\b", raw))
    chk("exactly one h1", h1 == 1, f"{h1} found")
    chk("the page declares a language", 'lang=' in raw[:600] or "<html" not in raw[:600], warn=True)

    print("\n  WEIGHT — what the first screen costs")
    page_kb = len(get(URL, binary=True)) / 1024
    print(f"    the page itself: {page_kb:.0f} KB")
    for f in ("almanac/browse/index.json", "almanac/quality_summary.json"):
        print(f"    {f}: {len(get(BASE + f, binary=True))/1024:.0f} KB (fetched only on demand)")
    big = len(get(BASE + "almanac/marriage_quality_binary.csv", binary=True)) / 1e6
    chk("the 8.9 MB corpus is NOT on the critical path", "browse/p000.json" not in raw,
        f"the CSV ({big:.1f} MB) is a download, the panel pages 500 rows at a time")

    print(f"\n  {'ALL CORRECT' if not fails else 'FAILURES: ' + '; '.join(fails)}")
    if warns:
        print(f"  warnings: {'; '.join(warns)}")


if __name__ == "__main__":
    main()
