#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Elenca tutti i domini associati al tuo account InternetBS.
Richiede: ApiKey e Password API.
"""

import requests, json, sys

API_BASE = "https://api.internet.bs"

# Inserire  qui o passarle via terminale con --api-key e --api-pass
API_KEY = "XXXXXXXXXXXXXXXXXXXXXXXXXXXX"
API_PASS = "XXXXXXXXXXXXXXXXXXXXXXXXXXXX"

def api_call(endpoint, params):
    """Esegue una chiamata GET all'API InternetBS"""
    url = f"{API_BASE}{endpoint}"
    params.setdefault("ResponseFormat", "json")
    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Errore API: {e}")
        sys.exit(1)

def list_domains(api_key, api_pass):
    """Richiede la lista domini"""
    res = api_call("/Domain/List", {"ApiKey": api_key, "Password": api_pass})
    if res.get("status") != "SUCCESS":
        print("❌ Errore nel recupero domini:")
        print(json.dumps(res, indent=2))
        sys.exit(1)
    domains = res.get("domain", []) or res.get("domains", [])
    return domains

def main():
    domains = list_domains(API_KEY, API_PASS)
    if not domains:
        print("⚠️ Nessun dominio trovato per questo account.")
        sys.exit(0)

    print(f"🌐 Trovati {len(domains)} domini registrati:")
    for i, d in enumerate(domains, start=1):
        print(f"{i:02d}. {d}")

    # (opzionale) salva su file
    with open("domains_list.txt", "w") as f:
        for d in domains:
            f.write(d + "\n")
    print("\n💾 Lista salvata in domains_list.txt")

if __name__ == "__main__":
    main()
