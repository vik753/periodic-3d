#!/usr/bin/env python3
"""Probe the data sources from CI and measure coverage (stage 0, task S0.4).

The dev container has no internet access, so this script runs in GitHub Actions.
Standard library only. It never fails the job: every problem goes into the report.

Usage: python tools/probe/probe.py <out-dir>

Outputs in <out-dir>:
  report.md                  human-readable report (Russian headings, raw numbers)
  numbers.json               all measured numbers
  wikidata-compounds.json.gz compounds with a formula and a ru/uk/en Wikipedia article
"""

from __future__ import annotations

import gzip
import json
import math
import random
import re
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

UA = "periodic-3d/0.1 (https://github.com/vik753/periodic-3d; data probe)"
QLEVER = "https://qlever.cs.uni-freiburg.de/api/wikidata"
WDQS = "https://query.wikidata.org/sparql"
PUBCHEM = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
MP_OPTIMADE = "https://optimade.materialsproject.org/v1/structures"
COD_OPTIMADE = "https://www.crystallography.net/cod/optimade/v1/structures"

PREFIXES = """PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX schema: <http://schema.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""

WIKI_IRIS = {
    "en": "https://en.wikipedia.org/",
    "ru": "https://ru.wikipedia.org/",
    "uk": "https://uk.wikipedia.org/",
}
WIKI_VALUES = " ".join(f"<{iri}>" for iri in WIKI_IRIS.values())

ELEMENTS = (
    "H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn "
    "Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce "
    "Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn "
    "Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl "
    "Mc Lv Ts Og"
).split()
ELEMENT_SET = frozenset(ELEMENTS)

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def http_get(url: str, *, accept: str | None = None, timeout: float = 90.0) -> tuple[int, bytes, float]:
    """GET a URL. Returns (status, body, seconds). Status -1 means a network error."""
    headers = {"User-Agent": UA}
    if accept:
        headers["Accept"] = accept
    request = urllib.request.Request(url, headers=headers)
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read(), time.monotonic() - started
    except urllib.error.HTTPError as err:
        body = err.read() if err.fp else b""
        return err.code, body, time.monotonic() - started
    except Exception as err:  # noqa: BLE001 - any network failure goes into the report
        return -1, repr(err).encode(), time.monotonic() - started


def sparql(query: str, endpoint: str = QLEVER, timeout: float = 240.0) -> tuple[list[dict[str, Any]] | None, str, float]:
    params = {"query": PREFIXES + query}
    if endpoint == WDQS:
        params["format"] = "json"
    url = endpoint + "?" + urllib.parse.urlencode(params)
    status, body, seconds = http_get(url, accept="application/sparql-results+json", timeout=timeout)
    if status != 200:
        return None, f"HTTP {status}: {body[:300]!r}", seconds
    try:
        data = json.loads(body)
        return data["results"]["bindings"], "ok", seconds
    except (ValueError, KeyError) as err:
        return None, f"bad JSON: {err!r}", seconds


def sparql_count(where: str, endpoint: str = QLEVER) -> dict[str, Any]:
    rows, message, seconds = sparql(f"SELECT (COUNT(DISTINCT ?item) AS ?n) WHERE {{ {where} }}", endpoint)
    value = int(rows[0]["n"]["value"]) if rows else None
    return {"value": value, "message": message, "seconds": round(seconds, 2)}


# ---------------------------------------------------------------------------
# Formula parsing (same rules as the pipeline will use)
# ---------------------------------------------------------------------------

SUBSCRIPTS = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
SUPERSCRIPT_CHARGE = re.compile(r"[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+")
NUMBER = re.compile(r"\d+(?:\.\d+)?")
HYDRATE_SPLIT = re.compile(r"[·•∙⋅*]")


def _parse_group(text: str) -> Counter | None:
    stack: list[Counter] = [Counter()]
    i = 0
    while i < len(text):
        char = text[i]
        if char in "([{":
            stack.append(Counter())
            i += 1
        elif char in ")]}":
            if len(stack) == 1:
                return None
            group = stack.pop()
            i += 1
            match = NUMBER.match(text, i)
            factor = 1.0
            if match:
                factor = float(match.group())
                i = match.end()
            for symbol, amount in group.items():
                stack[-1][symbol] += amount * factor
        elif char.isupper():
            symbol = char
            i += 1
            if i < len(text) and text[i].islower():
                symbol += text[i]
                i += 1
            if symbol in ("D", "T"):  # deuterium, tritium
                symbol = "H"
            if symbol not in ELEMENT_SET:
                return None
            match = NUMBER.match(text, i)
            amount = 1.0
            if match:
                amount = float(match.group())
                i = match.end()
            stack[-1][symbol] += amount
        else:
            return None
    if len(stack) != 1 or not stack[0]:
        return None
    return stack[0]


def parse_formula(raw: str) -> dict[str, float] | None:
    """Parse a Wikidata-style formula (Unicode subscripts, hydrates) into element counts."""
    text = raw.translate(SUBSCRIPTS)
    text = SUPERSCRIPT_CHARGE.sub("", text)
    text = text.replace(" ", "").replace(" ", "")
    text = re.sub(r"[+\-−]+$", "", text)
    total: Counter = Counter()
    for part in HYDRATE_SPLIT.split(text):
        if not part:
            continue
        factor = 1.0
        match = re.match(r"^(\d+(?:\.\d+)?)(?=[A-Z(\[{])", part)
        if match:
            factor = float(match.group(1))
            part = part[match.end():]
        counts = _parse_group(part)
        if counts is None:
            return None
        for symbol, amount in counts.items():
            total[symbol] += amount * factor
    return dict(total) if total else None


def reduced_formula(counts: dict[str, float]) -> str | None:
    """OPTIMADE chemical_formula_reduced: alphabetical order, gcd-reduced integers."""
    if any(abs(v - round(v)) > 1e-6 for v in counts.values()):
        return None
    ints = {k: int(round(v)) for k, v in counts.items()}
    divisor = 0
    for value in ints.values():
        divisor = math.gcd(divisor, value)
    divisor = divisor or 1
    return "".join(f"{el}{'' if n // divisor == 1 else n // divisor}" for el, n in sorted(ints.items()))


# ---------------------------------------------------------------------------
# Probe steps
# ---------------------------------------------------------------------------


def probe_hosts() -> list[dict[str, Any]]:
    water_query = urllib.parse.urlencode({"query": PREFIXES + "SELECT ?f WHERE { wd:Q283 wdt:P274 ?f }"})
    targets = {
        "PubChem PUG REST": f"{PUBCHEM}/compound/cid/962/property/MolecularFormula/JSON",
        "PubChem 3D SDF": f"{PUBCHEM}/compound/cid/962/SDF?record_type=3d",
        "QLever (Wikidata)": f"{QLEVER}?{water_query}",
        "Wikidata Query Service": f"{WDQS}?{water_query}&format=json",
        "Wikidata EntityData": "https://www.wikidata.org/wiki/Special:EntityData/Q283.json",
        "Wikipedia RU REST": "https://ru.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote("Вода"),
        "Wikipedia UK REST": "https://uk.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote("Вода"),
        "Wikipedia EN REST": "https://en.wikipedia.org/api/rest_v1/page/summary/Water",
        "Wikimedia Commons API": "https://commons.wikimedia.org/w/api.php?action=query&meta=siteinfo&format=json",
        "COD OPTIMADE": f"{COD_OPTIMADE}?filter={urllib.parse.quote('chemical_formula_reduced=\"ClNa\"')}&page_limit=1",
        "MP OPTIMADE": f"{MP_OPTIMADE}?filter={urllib.parse.quote('chemical_formula_reduced=\"ClNa\"')}&page_limit=1",
        "MP API heartbeat": "https://api.materialsproject.org/heartbeat",
        "MP open data (S3)": "https://materialsproject-build.s3.amazonaws.com/",
    }
    results = []
    for name, url in targets.items():
        status, body, seconds = http_get(url, timeout=60)
        results.append({"name": name, "url": url, "status": status, "seconds": round(seconds, 2), "bytes": len(body)})
        time.sleep(0.3)
    return results


def find_properties() -> dict[str, Any]:
    query = (
        "SELECT ?p ?label WHERE { ?p a wikibase:Property ; rdfs:label ?label . "
        'FILTER(LANG(?label) = "en") '
        'FILTER(CONTAINS(LCASE(STR(?label)), "crystallography open database") '
        '|| CONTAINS(LCASE(STR(?label)), "materials project") '
        '|| CONTAINS(LCASE(STR(?label)), "pubchem cid") '
        '|| CONTAINS(LCASE(STR(?label)), "chemical formula")) }'
    )
    rows, message, seconds = sparql(query)
    found = [
        {"property": r["p"]["value"].rsplit("/", 1)[-1], "label": r["label"]["value"]}
        for r in (rows or [])
    ]
    return {"found": found, "message": message, "seconds": round(seconds, 2)}


def wikidata_counts(extra_properties: list[str]) -> dict[str, Any]:
    any_wiki = f"?a schema:about ?item ; schema:isPartOf ?wiki . VALUES ?wiki {{ {WIKI_VALUES} }}"
    counts: dict[str, Any] = {
        "formula_total": sparql_count("?item wdt:P274 ?f ."),
        "formula_any_wiki": sparql_count(f"?item wdt:P274 ?f . {any_wiki}"),
        "formula_any_wiki_with_pubchem": sparql_count(f"?item wdt:P274 ?f ; wdt:P662 ?cid . {any_wiki}"),
        "formula_any_wiki_without_pubchem": sparql_count(
            f"?item wdt:P274 ?f . {any_wiki} FILTER NOT EXISTS {{ ?item wdt:P662 ?cid }}"
        ),
        "minerals_any_wiki": sparql_count(f"?item wdt:P31 wd:Q12089225 ; wdt:P274 ?f . {any_wiki}"),
    }
    for code, iri in WIKI_IRIS.items():
        counts[f"formula_{code}wiki"] = sparql_count(f"?item wdt:P274 ?f . ?a schema:about ?item ; schema:isPartOf <{iri}> .")
    for prop in extra_properties:
        counts[f"formula_any_wiki_with_{prop}"] = sparql_count(f"?item wdt:P274 ?f ; wdt:{prop} ?x . {any_wiki}")
    return counts


def wikidata_list() -> tuple[list[dict[str, Any]], str]:
    query = (
        "SELECT ?item ?f ?cid ?wiki ?sl WHERE { "
        "?item wdt:P274 ?f . "
        f"?a schema:about ?item ; schema:isPartOf ?wiki . VALUES ?wiki {{ {WIKI_VALUES} }} "
        "OPTIONAL { ?item wdt:P662 ?cid } "
        "OPTIONAL { ?item wikibase:sitelinks ?sl } }"
    )
    rows, message, _ = sparql(query, timeout=300)
    if rows is None:
        return [], message
    items: dict[str, dict[str, Any]] = {}
    for row in rows:
        qid = row["item"]["value"].rsplit("/", 1)[-1]
        entry = items.setdefault(qid, {"qid": qid, "formulas": set(), "cids": set(), "wikis": set(), "sitelinks": 0})
        entry["formulas"].add(row["f"]["value"])
        if "cid" in row:
            entry["cids"].add(row["cid"]["value"])
        wiki = row["wiki"]["value"]
        for code, iri in WIKI_IRIS.items():
            if wiki == iri:
                entry["wikis"].add(code)
        if "sl" in row:
            entry["sitelinks"] = max(entry["sitelinks"], int(float(row["sl"]["value"])))
    result = []
    for entry in items.values():
        result.append(
            {
                "qid": entry["qid"],
                "formulas": sorted(entry["formulas"]),
                "cids": sorted(entry["cids"], key=lambda c: int(c) if c.isdigit() else 0),
                "wikis": sorted(entry["wikis"]),
                "sitelinks": entry["sitelinks"],
            }
        )
    return result, message


def coverage(items: list[dict[str, Any]]) -> dict[str, Any]:
    per_element: Counter = Counter()
    pair_counts: Counter = Counter()
    parsed = 0
    size_hist: Counter = Counter()
    for item in items:
        counts = None
        for formula in item["formulas"]:
            counts = parse_formula(formula)
            if counts:
                break
        if not counts:
            continue
        parsed += 1
        elements = sorted(counts)
        size_hist[min(len(elements), 6)] += 1
        for element in elements:
            per_element[element] += 1
        for i, a in enumerate(elements):
            for b in elements[i + 1:]:
                pair_counts[(a, b)] += 1
    element_counts = {el: per_element.get(el, 0) for el in ELEMENTS}
    values = list(element_counts.values())
    return {
        "items": len(items),
        "parsed": parsed,
        "unparsed": len(items) - parsed,
        "elements_with_0": [el for el, n in element_counts.items() if n == 0],
        "elements_under_10": [el for el, n in element_counts.items() if 0 < n < 10],
        "median_per_element": statistics.median(values),
        "per_element": element_counts,
        "pairs_total": len(pair_counts),
        "pairs_with_5_plus": sum(1 for n in pair_counts.values() if n >= 5),
        "top_pairs": [[f"{a}-{b}", n] for (a, b), n in pair_counts.most_common(15)],
        "element_count_histogram": {str(k): v for k, v in sorted(size_hist.items())},
        "sitelinks_quantiles": _quantiles([i["sitelinks"] for i in items]),
        "with_cid": sum(1 for i in items if i["cids"]),
    }


def _quantiles(values: list[int]) -> dict[str, float]:
    if not values:
        return {}
    ordered = sorted(values)
    pick = lambda q: ordered[min(len(ordered) - 1, int(q * len(ordered)))]  # noqa: E731
    return {"p10": pick(0.1), "p50": pick(0.5), "p90": pick(0.9), "p99": pick(0.99), "max": ordered[-1]}


def pubchem_3d_sample(items: list[dict[str, Any]], size: int = 150) -> dict[str, Any]:
    with_cid = [i for i in items if i["cids"]]
    rng = random.Random(42)
    sample = rng.sample(with_cid, min(size, len(with_cid)))
    has_3d = 0
    errors = 0
    sizes: list[int] = []
    for item in sample:
        cid = item["cids"][0]
        status, body, _ = http_get(f"{PUBCHEM}/compound/cid/{cid}/SDF?record_type=3d", timeout=45)
        if status == 200:
            has_3d += 1
            sizes.append(len(body))
        elif status not in (404, 400):
            errors += 1
        time.sleep(0.25)  # PubChem asks for at most 5 requests per second
    batch_status, batch_body, batch_seconds = http_get(
        f"{PUBCHEM}/compound/cid/2244,702,962,5793/SDF?record_type=3d", timeout=60
    )
    return {
        "sample_size": len(sample),
        "with_3d": has_3d,
        "share_3d": round(has_3d / len(sample), 3) if sample else None,
        "errors": errors,
        "median_sdf_bytes": statistics.median(sizes) if sizes else None,
        "batch_request": {
            "status": batch_status,
            "records": batch_body.count(b"$$$$"),
            "seconds": round(batch_seconds, 2),
        },
    }


def optimade_samples() -> dict[str, Any]:
    formulas = ["NaCl", "Fe2O3", "SiO2", "CaCO3", "Al2O3", "TiO2", "Fe3O4", "CuSO4", "KMnO4", "FeS2"]
    out: dict[str, Any] = {}
    for provider, base in (("mp", MP_OPTIMADE), ("cod", COD_OPTIMADE)):
        rows = []
        keys_seen: list[str] = []
        for formula in formulas:
            counts = parse_formula(formula)
            reduced = reduced_formula(counts) if counts else None
            flt = urllib.parse.quote(f'chemical_formula_reduced="{reduced}"')
            status, body, seconds = http_get(f"{base}?filter={flt}&page_limit=3", accept="application/json", timeout=90)
            available = None
            if status == 200:
                try:
                    data = json.loads(body)
                    meta = data.get("meta", {})
                    available = meta.get("data_available", meta.get("data_returned"))
                    if data.get("data") and not keys_seen:
                        keys_seen = sorted(data["data"][0].get("attributes", {}).keys())
                except ValueError:
                    pass
            rows.append({"formula": formula, "reduced": reduced, "status": status, "available": available, "seconds": round(seconds, 2)})
            time.sleep(0.5)
        out[provider] = {"rows": rows, "attribute_keys": keys_seen}
    return out


def mp_licensing() -> dict[str, Any]:
    """What MP's OPTIMADE says about licenses and data origins (GNoME check, ADR 0004)."""
    out: dict[str, Any] = {}
    for name, url in (
        ("info", "https://optimade.materialsproject.org/v1/info"),
        ("info_structures", "https://optimade.materialsproject.org/v1/info/structures"),
        ("links", "https://optimade.materialsproject.org/v1/links"),
    ):
        status, body, _ = http_get(url, accept="application/json", timeout=60)
        out[name] = {"status": status, "body": body.decode("utf-8", errors="replace")[:20000]}
        time.sleep(0.5)
    return out


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def write_report(out_dir: Path, numbers: dict[str, Any]) -> None:
    lines = ["# Замер источников данных (этап 0)", ""]
    lines += ["## Доступность источников из GitHub Actions", "", "| Источник | HTTP | Время, с | Байт |", "| --- | --- | --- | --- |"]
    for host in numbers["hosts"]:
        lines.append(f"| {host['name']} | {host['status']} | {host['seconds']} | {host['bytes']} |")
    lines += ["", "## Свойства Wikidata", ""]
    for prop in numbers["properties"]["found"]:
        lines.append(f"- {prop['property']} — {prop['label']}")
    lines += ["", "## Счётчики Wikidata (QLever)", "", "| Метрика | Значение | Время, с | Статус |", "| --- | --- | --- | --- |"]
    for name, value in numbers["wikidata_counts"].items():
        lines.append(f"| {name} | {value['value']} | {value['seconds']} | {value['message'][:60]} |")
    cov = numbers.get("coverage") or {}
    if cov:
        lines += [
            "",
            "## Покрытие элементов (соединения со статьёй RU/UK/EN)",
            "",
            f"- Записей: {cov['items']}; формула разобрана: {cov['parsed']}; не разобрана: {cov['unparsed']}.",
            f"- С PubChem CID: {cov['with_cid']}.",
            f"- Медиана соединений на элемент: {cov['median_per_element']}.",
            f"- Элементы без соединений: {', '.join(cov['elements_with_0']) or 'нет'}.",
            f"- Элементы с 1–9 соединениями: {', '.join(cov['elements_under_10']) or 'нет'}.",
            f"- Пар элементов: {cov['pairs_total']}; пар с 5+ соединениями: {cov['pairs_with_5_plus']}.",
            f"- Топ пар: {', '.join(f'{p} ({n})' for p, n in cov['top_pairs'])}.",
            f"- Число элементов в формуле (6 = 6+): {cov['element_count_histogram']}.",
            f"- Квантили числа статей (sitelinks): {cov['sitelinks_quantiles']}.",
            "",
            "| Элемент | Соединений |",
            "| --- | --- |",
        ]
        for element, n in cov["per_element"].items():
            lines.append(f"| {element} | {n} |")
    pc = numbers.get("pubchem_3d") or {}
    if pc:
        lines += [
            "",
            "## PubChem 3D (случайная выборка соединений с CID)",
            "",
            f"- Выборка: {pc['sample_size']}; с 3D: {pc['with_3d']} ({pc['share_3d']}); ошибок: {pc['errors']}.",
            f"- Медианный размер SDF: {pc['median_sdf_bytes']} байт.",
            f"- Пакетный запрос 4 CID: {pc['batch_request']}.",
        ]
    opt = numbers.get("optimade") or {}
    for provider, block in opt.items():
        lines += ["", f"## OPTIMADE: {provider}", "", "| Формула | Reduced | HTTP | Записей | Время, с |", "| --- | --- | --- | --- | --- |"]
        for row in block["rows"]:
            lines.append(f"| {row['formula']} | {row['reduced']} | {row['status']} | {row['available']} | {row['seconds']} |")
        lines.append("")
        lines.append(f"Поля атрибутов: {', '.join(block['attribute_keys'])}")
    lines += ["", f"Общее время замера: {numbers['total_seconds']} с.", ""]
    (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "out/probe")
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    numbers: dict[str, Any] = {}

    numbers["hosts"] = probe_hosts()
    numbers["properties"] = find_properties()
    extra = [
        p["property"]
        for p in numbers["properties"]["found"]
        if any(word in p["label"].lower() for word in ("crystallography open database", "materials project"))
    ]
    numbers["wikidata_counts"] = wikidata_counts(extra[:4])

    items, message = wikidata_list()
    numbers["wikidata_list_message"] = message
    if items:
        with gzip.open(out_dir / "wikidata-compounds.json.gz", "wt", encoding="utf-8") as handle:
            json.dump(items, handle, ensure_ascii=False)
        numbers["coverage"] = coverage(items)
        numbers["pubchem_3d"] = pubchem_3d_sample(items)
    numbers["optimade"] = optimade_samples()
    numbers["mp_licensing"] = mp_licensing()
    numbers["total_seconds"] = round(time.monotonic() - started, 1)

    (out_dir / "numbers.json").write_text(json.dumps(numbers, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    write_report(out_dir, numbers)
    print((out_dir / "report.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
