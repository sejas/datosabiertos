#!/usr/bin/env python3
"""Score 0-100 = Impacto (50) + Calidad (50). Rúbrica explícita y reproducible."""
import json, math, glob, os, datetime as dt

NOW = dt.datetime(2026, 7, 25)
MACH = {'CSV','JSON','GEOJSON','XML','XLSX','XLS','ODS','GPKG','SHP','KML','KMZ','API','RDF',
        'GML','TSV','JSON-LD','WFS','WMS','GTFS','PARQUET','SHAPE','GEOPACKAGE','TXT'}

# población (padrón INE ~2024, aprox) y tipo de API observado empíricamente
CIUDADES = {
 # nombre            pobl     api          ds     medido
 "Madrid":          (3400000, "CKAN+DCAT"),
 "Barcelona":       (1700000, "CKAN+DCAT"),
 "Valencia":        ( 830000, "ArcGIS/ad-hoc"),
 "Zaragoza":        ( 690000, "ad-hoc REST"),
 "Malaga":          ( 596000, "CKAN+DCAT"),
 "Palmas_GC":       ( 381000, "ArcGIS"),
 "Bilbao":          ( 350000, "ad-hoc/web"),
 "Cordoba":         ( 322000, "CKAN+DCAT"),
 "Vigo":            ( 293000, "ad-hoc/web"),
 "Gijon":           ( 270000, "ad-hoc REST"),
 "Vitoria":         ( 255000, "ad-hoc REST"),
 "Terrassa":        ( 227000, "CKAN+DCAT"),
 "SCTenerife":      ( 209000, "CKAN+DCAT"),
 "Pamplona":        ( 204000, "CKAN+DCAT"),
 "Donostia":        ( 190000, "ArcGIS"),
 "Santander":       ( 172000, "ad-hoc REST"),
 "Alcobendas":      ( 120000, "CKAN+DCAT"),
 "Reus":            ( 108000, "CKAN+DCAT"),
 "Lorca":           (  97000, "ad-hoc"),
 "Caceres":         (  96000, "SPARQL/ad-hoc"),
 "Torrent":         (  84000, "CKAN+DCAT"),
 "SantBoi":         (  82000, "ArcGIS Hub"),
 "Aviles":          (  76000, "CKAN+DCAT"),
 "Ponferrada":      (  63000, "CKAN+DCAT"),
 "Arganda":         (  60000, "CKAN+DCAT"),
 "Alcoi":           (  59000, "CKAN+DCAT"),
 "SanLorenzo":      (  19000, "CKAN+DCAT"),
}
API_PTS = {"CKAN+DCAT": 15, "ODS": 13, "Socrata": 12, "ArcGIS Hub": 9, "ArcGIS": 8,
           "SPARQL/ad-hoc": 10, "ad-hoc REST": 6, "ad-hoc": 4, "ad-hoc/web": 2}
# nº datasets desde datos.gob.es (federado, autoritativo)
DS = {"Malaga":1369,"Arganda":968,"Gijon":783,"Madrid":672,"Barcelona":555,"Torrent":342,
      "Bilbao":341,"Valencia":296,"Zaragoza":228,"Lorca":204,"Vitoria":197,"Alcobendas":177,
      "Vigo":148,"Terrassa":125,"Caceres":116,"Donostia":108,"Aviles":107,"SCTenerife":86,
      "Santander":58,"SanLorenzo":49,"SantBoi":45,"Cordoba":145,"Reus":119,"Pamplona":35,
      "Alcoi":32,"Ponferrada":29,"Palmas_GC":24}
GB = {"Madrid":262.4,"Barcelona":61.7,"Alcoi":5.13,"Malaga":10.2,"Cordoba":0.71,"Arganda":1.03,
      "SCTenerife":0.72,"Reus":0.56,"Alcobendas":0.49,"Aviles":0.14,"Terrassa":0.12,
      "Torrent":0.17,"SanLorenzo":0.01,"Ponferrada":0.01}
VIVOS = {"Alcobendas":100,"Alcoi":100,"Arganda":100,"Aviles":100,"Barcelona":100,"Cordoba":100,
         "Madrid":25,"Malaga":100,"Pamplona":70,"Ponferrada":100,"Reus":100,"SCTenerife":100,
         "SanLorenzo":100,"Terrassa":75,"Torrent":90}

Q = {r["portal"]: r for r in json.load(open("quality.json"))}
SUM = {r["portal"]: r for r in json.load(open("summary.json"))}

def clamp(x, lo, hi): return max(lo, min(hi, x))

rows = []
for c, (pob, api) in CIUDADES.items():
    q = Q.get(c); s = SUM.get(c)
    medido = q is not None
    nds = DS.get(c, 0)
    gb = GB.get(c)
    # --- IMPACTO (50) ---
    i_pob = clamp(20 * (math.log10(pob) - 4.2) / (math.log10(3.4e6) - 4.2), 0, 20)
    i_ds  = clamp(15 * math.log10(max(nds, 1)) / math.log10(1400), 0, 15)
    i_vol = clamp(8 * (math.log10(gb + 0.05) + 1.3) / (math.log10(262) + 1.3), 0, 8) if gb is not None else 3.0
    i_rec = clamp(7 * math.log10(max(s["n_resources"], 1)) / math.log10(11000), 0, 7) if s else 2.5
    imp = i_pob + i_ds + i_vol + i_rec
    # --- CALIDAD (50) ---
    c_api = API_PTS.get(api, 4)
    c_fmt = (q["maq"] / 100 * 12) if medido else 6.0
    c_fresh = (q["a12"] / 100 * 12) if medido else 5.0
    c_lic = 5 if c in SUM and SUM[c] else 3
    if c in ("Cordoba",): c_lic = 1.5          # 43% sin licencia / notspecified
    c_meta = ((s["pct_size"] / 100 * 3) + (q["desc"] / 100 * 3)) if medido else 2.0
    c_fiab = (VIVOS.get(c, 70) / 100 * 6)
    cal = c_api + c_fmt + c_fresh + c_lic + c_meta + c_fiab
    rows.append(dict(ciudad=c, pob=pob, api=api, ds=nds, gb=gb, medido=medido,
                     impacto=round(imp, 1), calidad=round(cal, 1), total=round(imp + cal)))

rows.sort(key=lambda r: -r["total"])
print(f"{'#':<3}{'ciudad':<12}{'pobl':>9}{'ds':>6}{'GB':>8}{'API':<15}{'IMP/50':>7}{'CAL/50':>7}{'TOTAL':>7}  base")
for i, r in enumerate(rows, 1):
    g = f"{r['gb']:.1f}" if r['gb'] is not None else "n/d"
    print(f"{i:<3}{r['ciudad']:<12}{r['pob']:>9,}{r['ds']:>6}{g:>8}  {r['api']:<15}{r['impacto']:>5}{r['calidad']:>7}{r['total']:>7}  "
          f"{'medido' if r['medido'] else 'inferido'}")
json.dump(rows, open("scores.json", "w"), indent=1, ensure_ascii=False)
