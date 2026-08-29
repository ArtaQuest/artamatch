"""make_rule_cards.py — render the surviving statements into the page, grouped by tradition.

The model is only explainable if a reader can see every statement in it. This writes a static block —
26 rules is small enough that fetching would be slower than shipping it — grouped by the tradition each
statement comes from, ordered by how much weight that tradition carries.

Each card shows the statement in plain words and what the tradition reads into it. How it is COMPUTED is
one tap away rather than in the way, because most readers want the meaning and some want the mechanism.
"""
import collections, html, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from explain_rules import explain

MODEL = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1
                           else "~/.artamatch-dev/quality_v21_a35.json")
PAGE = os.path.expanduser(sys.argv[2] if len(sys.argv) > 2
                          else "~/.artaquest-dev/wt/am-pages/docs/index.html")
M0, M1 = "<!--RULE-CARDS-->", "<!--/RULE-CARDS-->"

CSS = """
<style id=rulecss>
#rulecards{margin-top:44px}
#rulecards>summary{cursor:pointer;list-style:none}
#rulecards>summary::-webkit-details-marker{display:none}
.trad{margin-top:26px}
.tradh{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;
  border-bottom:1px solid var(--line);padding-bottom:7px;margin-bottom:2px}
.tradn{font-family:var(--serif);font-size:16.5px;color:var(--gold)}
.tradw{margin-left:auto;font-size:11.5px;color:var(--mut);font-variant-numeric:tabular-nums}
.tbar{height:2px;background:var(--line);border-radius:2px;overflow:hidden;margin-bottom:12px}
.tbar>i{display:block;height:100%;background:linear-gradient(90deg,var(--gold),var(--blue-l))}
.rcard{padding:11px 0;border-bottom:1px solid rgba(18,40,62,.55)}
.rcard:last-child{border-bottom:0}
.rct{font-family:var(--serif);font-size:15px;line-height:1.4}
.rcr{color:var(--ink);opacity:.8;font-size:13.5px;line-height:1.55;margin-top:4px}
.rcm{margin-top:6px}
.rcm>summary{cursor:pointer;font-size:11.5px;letter-spacing:.05em;text-transform:uppercase;
  color:var(--mut);list-style:none}
.rcm>summary::-webkit-details-marker{display:none}
.rcm>summary:hover{color:var(--blue-l)}
.rcp{color:var(--mut);font-size:12.5px;line-height:1.55;margin-top:5px;
  border-left:2px solid var(--line);padding-left:11px}
@media(max-width:640px){.rct{font-size:14.5px}.rcr{font-size:13px}}
</style>"""


def main():
    m = json.load(open(MODEL))
    w = m["weights"]
    tot = sum(w.values())
    ex = []
    for k, v in w.items():
        e = explain(k); e["rule"] = k; e["w"] = v
        ex.append(e)
    by = collections.defaultdict(list)
    for e in ex:
        by[e["tradition"]].append(e)
    order = sorted(by, key=lambda t: -sum(e["w"] for e in by[t]))

    parts = [M0, CSS,
             '<details class="fam" id=rulecards><summary>What the model actually reads '
             f'<span class="tc">{len(ex)} statements</span></summary>',
             '<p class="fw" style="margin-top:14px">Every statement below is a named tradition, and '
             'every one of them uses <b>both</b> birth dates — nothing about one person alone can enter '
             'the model. Only the weighting was fitted; the statements themselves were written down long '
             'before us. This is the whole model, not a sample of it.</p>']
    for t in order:
        rules = sorted(by[t], key=lambda e: -e["w"])
        share = sum(e["w"] for e in rules) / tot
        parts.append('<div class=trad><div class=tradh>'
                     f'<span class=tradn>{html.escape(t)}</span>'
                     f'<span class=tradw>{len(rules)} statement{"s" if len(rules)!=1 else ""} · '
                     f'{share:.0%} of the model</span></div>'
                     f'<div class=tbar><i style="width:{max(2, round(share*100))}%"></i></div>')
        for e in rules:
            parts.append(
                '<div class=rcard>'
                f'<div class=rct>{html.escape(e["title"])}</div>'
                f'<div class=rcr>{html.escape(e["reading"])}</div>'
                '<details class=rcm><summary>how it is computed</summary>'
                f'<div class=rcp>{html.escape(e["plain"])}<br><span style="opacity:.6">'
                f'statement <code>{html.escape(e["rule"])}</code>, weight +{e["w"]:.4f}</span></div>'
                '</details></div>')
        parts.append('</div>')
    parts.append('</details>')
    parts.append(M1)
    block = "".join(parts)

    def markup_only(t):
        """strip script and style before counting tags — a <details> inside a JS comment is not
        markup, and counting it as such fails a balance check that is otherwise sound"""
        import re as _re
        return _re.sub(r"<(script|style)\b.*?</\1>", "", t, flags=_re.S | _re.I)

    s = open(PAGE).read()
    if M0 in s:
        s = s[:s.index(M0)] + block + s[s.index(M1) + len(M1):]
    else:
        j = s.index("<!--BROWSE-PANEL-->")
        s = s[:j] + block + "\n" + s[j:]
    open(PAGE, "w").write(s)
    ms = markup_only(s)
    o, c = ms.count("<details"), ms.count("</details>")
    assert o == c, f"details unbalanced {o}/{c}"
    print(f"  {len(ex)} rules across {len(order)} traditions written into the page "
          f"· details {o}/{c} balanced")
    for t in order:
        print(f"    {t:<44} {len(by[t]):>2}  {sum(e['w'] for e in by[t])/tot:>5.0%}")


if __name__ == "__main__":
    main()
