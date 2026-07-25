#!/usr/bin/env python3
"""Cosecha catálogos CKAN municipales: nº datasets, recursos, formatos y tamaños."""
import json, sys, random, gzip, os
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

UA = "Mozilla/5.0 (compatible; TFM-opendata-research/0.1)"
random.seed(42)

PORTALS = {
    "Malaga":      "https://datosabiertos.malaga.eu/api/3/action",
    "Madrid":      "https://datos.madrid.es/api/3/action",
    "Barcelona":   "https://opendata-ajuntament.barcelona.cat/data/api/3/action",
    "Arganda":     "https://datosabiertos.ayto-arganda.es/api/3/action",
    "Cordoba":     "https://datosabiertos.cordoba.es/api/3/action",
    "Reus":        "https://opendata.reus.cat/api/3/action",
    "Pamplona":    "https://datosabiertos.pamplona.es/api/3/action",
    "Alcobendas":  "https://datos.alcobendas.org/api/3/action",
    "Aviles":      "https://datos.aviles.es/api/3/action",
    "SCTenerife":  "https://www.santacruzdetenerife.es/opendata/api/3/action",
    "Alcoi":       "https://opendata.alcoi.org/data/api/3/action",
    "Ponferrada":  "https://opendata.ponferrada.org/api/3/action",
    "Torrent":     "http://datosabiertos.torrent.es/api/3/action",
    "Terrassa":    "https://opendata.terrassa.cat/api/3/action",
    "SanLorenzo":  "https://datosabiertos.aytosanlorenzo.es/api/3/action",
    "Tenerife_Cab":"https://datos.tenerife.es/ckan/api/3/action",
}

def get(url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return json.loads(raw)

def harvest(name, api):
    out = {"portal": name, "api": api, "packages": [], "error": None, "bytes_meta": 0}
    try:
        start, rows = 0, 200
        while True:
            d = get(f"{api}/package_search?rows={rows}&start={start}")
            res = d["result"]
            out["total"] = res["count"]
            got = res["results"]
            out["packages"].extend(got)
            start += rows
            if start >= res["count"] or not got or start > 3000:
                break
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
    out["bytes_meta"] = len(json.dumps(out["packages"], ensure_ascii=False).encode())
    return out

if __name__ == "__main__":
    os.makedirs("cat", exist_ok=True)
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(lambda kv: harvest(*kv), PORTALS.items()))
    summary = []
    for r in results:
        pkgs = r["packages"]
        nres = sum(len(p.get("resources", [])) for p in pkgs)
        sized = [int(x["size"]) for p in pkgs for x in p.get("resources", [])
                 if str(x.get("size") or "").isdigit() and int(x["size"]) > 0]
        fmts = {}
        for p in pkgs:
            for x in p.get("resources", []):
                f = (x.get("format") or "?").upper()[:12]
                fmts[f] = fmts.get(f, 0) + 1
        summary.append({
            "portal": r["portal"], "error": r["error"], "n_datasets": len(pkgs),
            "total_reported": r.get("total"), "n_resources": nres,
            "meta_MB": round(r["bytes_meta"] / 1e6, 2),
            "res_con_size": len(sized), "pct_size": round(100 * len(sized) / nres, 1) if nres else 0,
            "declared_GB": round(sum(sized) / 1e9, 3),
            "top_formats": sorted(fmts.items(), key=lambda t: -t[1])[:6],
        })
        if pkgs:
            with open(f"cat/{r['portal']}.json", "w") as fh:
                json.dump(pkgs, fh, ensure_ascii=False)
    json.dump(summary, open("summary.json", "w"), ensure_ascii=False, indent=1)
    for s in sorted(summary, key=lambda s: -(s["n_datasets"])):
        print(json.dumps(s, ensure_ascii=False))
