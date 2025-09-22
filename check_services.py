#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smoke test de microserviços (sem libs externas).
Imprime linha PASS/FAIL + uma MENSAGEM DE STATUS para cada serviço testado.
Exit code 0 se todos ok; !=0 caso contrário.
"""

import concurrent.futures as cf
import json, time, ssl, urllib.request, urllib.error, sys

BASE = "https://web-production-3163.up.railway.app"
#BASE ="http://127.0.0.1:8000" 
TIMEOUT = 120

# ---------- Helpers de validação ----------
def is_list(x): return isinstance(x, list)
def has_keys_list(items, *keys):
    return isinstance(items, list) and all(isinstance(d, dict) and all(k in d for k in keys) for d in items)
def any_keys(d, *alts): return isinstance(d, dict) and any(k in d for k in alts)

def ok_health(p): return any_keys(p, "status") and str(p.get("status")).lower() == "ok"
def ok_courses(p): return has_keys_list(p, "id", "name") or has_keys_list(p, "id", "fullname")
def ok_matriculas(p): return has_keys_list(p, "ano", "total")
def ok_years(p): return has_keys_list(p, "ano")
def ok_studentbycities(p):
    return (has_keys_list(p, "municipio", "total") or
            has_keys_list(p, "estado", "total") or
            has_keys_list(p, "name", "value"))
def ok_enroll_by_year(p): return has_keys_list(p, "name", "value")
def ok_enroll_by_location(p):
    return (has_keys_list(p, "name", "value") or
            has_keys_list(p, "estado", "total") or
            has_keys_list(p, "municipio", "total"))
def ok_enroll_total_yearly(p): return has_keys_list(p, "name", "value")
def ok_enroll_polo_total(p): return has_keys_list(p, "name", "value")
def ok_analysis_list(p): return is_list(p)
def ok_analytics_health(p): return isinstance(p, dict) and p.get("ok") is True
def ok_analytics_std(p): return isinstance(p, dict) and any(k in p for k in ("data","global","weekly","params"))
def ok_polos_strings(p):
    # /polos -> lista de strings
    return isinstance(p, list) and all(isinstance(s, str) for s in p)

def ok_poles_comprehensive(p):
    # /api/poles/comprehensive -> lista de dicts com chaves essenciais
    return has_keys_list(p, "id", "polo", "year", "frequenciaAbsoluta", "frequenciaRelativa")

def ok_total_yearly_matriculas(p):
    # /api/matriculas/total_yearly -> [{ano, total}]
    return has_keys_list(p, "ano", "total")

# ---------- Endpoints a testar ----------
CHECKS = {
    "/health/": ("health", ok_health),
    "/courses": ("courses", ok_courses),
    "/matriculas?inicio=2010&fim=2025": ("matriculas", ok_matriculas),
    "/years_suap": ("years_suap", ok_years),
    "/studentbycities?inicio=2010&fim=2025&typelocal=estado": ("studentbycities", ok_studentbycities),
    # === Novos microserviços ===
    "/polos": ("polos", ok_polos_strings),  # :contentReference[oaicite:3]{index=3}
    "/poles/comprehensive": ("poles.comprehensive", ok_poles_comprehensive),  # :contentReference[oaicite:4]{index=4}
    "/matriculas/total_yearly": ("matriculas.total_yearly", ok_total_yearly_matriculas),  # :contentReference[oaicite:5]{index=5}

    # Opcionais (ok falhar se não existirem nesse deploy)
    "/enrollments/by_year": ("enrollments.by_year", ok_enroll_by_year),
    "/enrollments/by_location?inicio=2010&fim=2025&typelocal=estado": ("enrollments.by_location", ok_enroll_by_location),
    "/enrollments/total_yearly": ("enrollments.total_yearly", ok_enroll_total_yearly),
    "/enrollments/by_polo_total": ("enrollments.by_polo_total", ok_enroll_polo_total),
    "/analysis/gender": ("analysis.gender", ok_analysis_list),
    "/analysis/income": ("analysis.income", ok_analysis_list),
    "/analytics_behavour/health": ("analytics_behavour.health", ok_analytics_health),
    "/analytics_behavour/top-hours-days?start=2023-01-01&end=2024-01-05": ("analytics_behavour.top_hours_days", ok_analytics_std),
    "/analytics_behavour/resources-usage?start=2023-01-01&end=2024-01-05": ("analytics_behavour.resources_usage", ok_analytics_std),
    "/analytics_behavour/avg-session-time?start=2023-01-01&end=2024-01-31": ("analytics_behavour.avg_session_time", ok_analytics_std),
    "/analytics_behavour/activation": ("analytics_behavour.activation", ok_analytics_std),
}


CTX = ssl.create_default_context()

# ---------- HTTP ----------
def http_get_json(url: str):
    req = urllib.request.Request(url, headers={"Accept":"application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=CTX) as resp:
        status = resp.status
        body = resp.read()
    text = body.decode("utf-8", errors="replace").strip()
    try:
        data = json.loads(text if text else "null")
    except json.JSONDecodeError:
        # caso algum endpoint retorne texto simples
        data = {"_raw": text}
    return status, data

# ---------- Checagem de um endpoint ----------
def check_one(path, name, validator):
    url = BASE.rstrip("/") + path
    t0 = time.time()
    try:
        status, payload = http_get_json(url)
        ok = (status == 200) and bool(validator(payload))
        ms = int((time.time() - t0) * 1000)
        if ok:
            message = f"{name}: UP (HTTP {status}, {ms}ms)"
        else:
            if status != 200:
                message = f"{name}: DOWN (HTTP {status}, {ms}ms)"
            else:
                message = f"{name}: UNHEALTHY - shape inesperado (HTTP 200, {ms}ms)"
        return {"name": name, "path": path, "url": url, "ok": ok, "status": status, "ms": ms, "message": message}
    except urllib.error.HTTPError as e:
        ms = int((time.time() - t0) * 1000)
        return {"name": name, "path": path, "url": url, "ok": False, "status": e.code, "ms": ms,
                "message": f"{name}: DOWN (HTTP {e.code}, {ms}ms)"}
    except Exception as e:
        ms = int((time.time() - t0) * 1000)
        return {"name": name, "path": path, "url": url, "ok": False, "status": None, "ms": ms,
                "message": f"{name}: DOWN ({type(e).__name__}: {e}, {ms}ms)"}

# ---------- Main ----------
def main():
    print(f"=== Service Probe @ {BASE} ===")
    results = []
    with cf.ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(check_one, p, n, v) for p,(n,v) in CHECKS.items()]
        for f in cf.as_completed(futs):
            results.append(f.result())

    # Ordena: OK primeiro, depois por nome
    results.sort(key=lambda x: (x["ok"] is True, x["name"]), reverse=True)

    # Linha PASS/FAIL + mensagem explícita de status
    okc = 0
    for r in results:
        tag = "PASS" if r["ok"] else "FAIL"
        print(f"[{tag:4}] {r['message']}  -> {r['path']}")

        if r["ok"]:
            okc += 1

    # Sumário e JSON para CI
    total = len(results)
    print(f"\nResumo: {okc}/{total} endpoints OK")
    print("\nJSON:")
    print(json.dumps(results, ensure_ascii=False, indent=2))

    sys.exit(0 if okc == total else 1)

if __name__ == "__main__":
    main()
