#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
InternetBS DNS Mass IP Migration (multi-domain, multi-record)
Aggiorna tutti i record A con un vecchio IP su tutti i domini dell'account.
uso : python3 internetbs.py   --api-key XXXXXXXXXX   --api-pass yyyyyyyyyy   --old-ip 123.456.789.000   --new-ip 000.987.654.321
"""

import requests, json, csv, time, argparse, concurrent.futures
from datetime import datetime
from pathlib import Path

API_BASE = "https://api.internet.bs"
DEFAULT_THREADS = 3
DEFAULT_TIMEOUT = 40


def api_call(endpoint, params):
    """Effettua chiamata GET all'API InternetBS"""
    url = f"{API_BASE}{endpoint}"
    params.setdefault("ResponseFormat", "json")
    try:
        r = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[ERRORE API] {e}")
        return {}


def list_domains(api_key, api_pass):
    """Ottiene la lista dei domini dell'account"""
    data = api_call("/Domain/List", {"ApiKey": api_key, "Password": api_pass})
    return data.get("domain", []) or data.get("domains", [])


def list_records(api_key, api_pass, domain):
    """Ottiene tutti i record DNS per un dominio"""
    data = api_call("/Domain/DnsRecordList", {
        "ApiKey": api_key,
        "Password": api_pass,
        "Domain": domain
    })
    return data.get("records", [])


def remove_record(api_key, api_pass, full_name, rtype):
    """Rimuove un record specifico"""
    params = {
        "ApiKey": api_key,
        "Password": api_pass,
        "FullRecordName": full_name,
        "Type": rtype
    }
    return api_call("/Domain/DnsRecordRemove", params)


def add_record(api_key, api_pass, full_name, rtype, value, ttl):
    """Aggiunge un record DNS"""
    params = {
        "ApiKey": api_key,
        "Password": api_pass,
        "FullRecordName": full_name,
        "Type": rtype,
        "Value": value,
        "TTL": ttl
    }
    return api_call("/Domain/DnsRecordAdd", params)


def process_domain(domain, api_key, api_pass, old_ip, new_ip, dry_run, writer, backup_data):
    print(f"\n🌐 Scansione dominio: {domain}")
    records = list_records(api_key, api_pass, domain)
    if not records:
        print(f"⚠️ Nessun record trovato per {domain}")
        return

    backup_data[domain] = records

    for rec in records:
        name = rec.get("name")
        value = rec.get("value")
        ttl = rec.get("ttl", 3600)
        rtype = rec.get("type")

        if rtype == "A" and value == old_ip:
            full_name = name
            print(f"🔄 {full_name} → {old_ip} → {new_ip}")

            start = time.time()
            if dry_run:
                status, msg = "DRY-RUN", "Simulazione"
            else:
                rem = remove_record(api_key, api_pass, full_name, "A")
                add = add_record(api_key, api_pass, full_name, "A", new_ip, ttl)
                status = add.get("status", "UNKNOWN")
                msg = add.get("message", "")

            end = time.time()
            writer.writerow({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "domain": domain,
                "record": full_name,
                "old_value": old_ip,
                "new_value": new_ip,
                "status": status,
                "message": msg,
                "duration_ms": int((end - start) * 1000),
                "action": "UPDATE" if not dry_run else "DRY-RUN"
            })


def main():
    parser = argparse.ArgumentParser(description="InternetBS mass DNS IP migration tool")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--api-pass", required=True)
    parser.add_argument("--old-ip", required=True)
    parser.add_argument("--new-ip", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--threads", type=int, default=DEFAULT_THREADS)
    args = parser.parse_args()

    log_dir = Path("logs") / datetime.now().strftime("%Y%m%d_%H%M%S_massupdate")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_csv = log_dir / "migration_audit.csv"
    backup_file = log_dir / "backup_records.json"

    print(f"📁 Logs salvati in: {log_dir}")

    backup_data = {}

    with open(log_csv, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["timestamp", "domain", "record", "old_value", "new_value",
                      "status", "message", "duration_ms", "action"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        domains = list_domains(args.api_key, args.api_pass)
        if not domains:
            print("❌ Nessun dominio trovato nell account.")
            return

        with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
            futures = [
                executor.submit(process_domain, d, args.api_key, args.api_pass,
                                args.old_ip, args.new_ip, args.dry_run, writer, backup_data)
                for d in domains
            ]
            for f in concurrent.futures.as_completed(futures):
                f.result()

    with open(backup_file, "w", encoding="utf-8") as bf:
        json.dump(backup_data, bf, indent=2, ensure_ascii=False)

    print(f"\n🧾 Report CSV: {log_csv}")
    print(f"💾 Backup JSON: {backup_file}")
    print("✅ Operazione completata.")


if __name__ == "__main__":
    main()
