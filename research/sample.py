#!/usr/bin/env python3
"""Muestrea recursos reales: comprueba si el enlace vive y mide bytes reales."""
import json, glob, os, random, urllib.request, urllib.error, ssl, statistics as st
from concurrent.futures import ThreadPoolExecutor

random.seed(7)
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
UA = "Mozilla/5.0 (compatible; TFM-opendata-research/0.1)"
N = 30

def check(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Range": "bytes=0-0"})
        with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
            cr = r.headers.get("Content-Range")
            size = int(cr.split("/")[-1]) if cr and "/" in cr and cr.split("/")[-1].isdigit() \
                   else (int(r.headers.get("Content-Length") or 0))
            return (r.status, size)
    except urllib.error.HTTPError as e:
        return (e.code, -1)
    except Exception as e:
        return (type(e).__name__, -1)

rows = []
for f in sorted(glob.glob("cat/*.json")):
    p = os.path.basename(f)[:-5]
    pk = json.load(open(f))
    res = [(x.get("url"), x.get("size")) for d in pk for x in d.get("resources", []) if x.get("url", "").startswith("http")]
    if not res:
        continue
    smp = random.sample(res, min(N, len(res)))
    with ThreadPoolExecutor(max_workers=10) as ex:
        out = list(ex.map(lambda t: check(t[0]), smp))
    ok = [(o, s) for (o, s), (u, d) in zip(out, smp) if o == 200 or o == 206]
    codes = {}
    for o, _ in out:
        codes[str(o)] = codes.get(str(o), 0) + 1
    sizes = [s for o, s in ok if s > 0]
    # comparar declarado vs real
    pairs = [(int(d), s) for (o, s), (u, d) in zip(out, smp)
             if s > 0 and str(d or "").isdigit() and int(d) > 0]
    err = None
    if pairs:
        err = round(100 * st.median([abs(dd - ss) / max(ss, 1) for dd, ss in pairs]), 1)
    rows.append({"portal": p, "n": len(smp), "vivos_pct": round(100 * len(ok) / len(smp)),
                 "media_MB": round(st.mean(sizes) / 1e6, 2) if sizes else None,
                 "mediana_KB": round(st.median(sizes) / 1e3, 1) if sizes else None,
                 "err_mediano_tam_%": err, "codigos": codes})
    print(json.dumps(rows[-1], ensure_ascii=False))
json.dump(rows, open("sample.json", "w"), ensure_ascii=False, indent=1)
