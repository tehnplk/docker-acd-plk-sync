#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
import time
from pathlib import Path
from urllib import error, request
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=False, encoding="utf-8")

DB_TYPE = os.getenv("DB_TYPE", "mysql").strip().lower()
SUPPORTED_DB_TYPES = {"mysql", "postgres"}

if DB_TYPE not in SUPPORTED_DB_TYPES:
    raise RuntimeError("DB_TYPE must be either 'mysql' or 'postgres'")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "112233")
DB_NAME = os.getenv("DB_NAME", "hos11253")

PATIENT_API_URL = os.getenv("API_URL", "http://127.0.0.1:3000/api/patient").rstrip("/")
PATIENT_API_JWT_SECRET = os.getenv("SECRET_KEY", "accident-patient-jwt-2026-plk").strip()


def configure_stdio() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def make_token(secret: str, ttl_seconds: int = 3600) -> str:
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode("utf-8"))
    payload = b64url(
        json.dumps({"scope": "patient-api", "exp": int(time.time()) + ttl_seconds}, separators=(",", ":")).encode(
            "utf-8"
        )
    )
    sig = b64url(hmac.new(secret.encode("utf-8"), f"{header}.{payload}".encode("ascii"), hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"


def load_query() -> str:
    if DB_TYPE == "mysql":
        query_path = BASE_DIR / "mysql_hosxp_acd_query.sql"
    else:
        query_path = BASE_DIR / "postgres_hosxp_acd_query.sql"
    return query_path.read_text(encoding="utf-8").strip().rstrip(";")


def run_query(sql: str) -> list[dict[str, object]]:
    if DB_TYPE == "postgres":
        import psycopg

        conn = psycopg.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            dbname=DB_NAME,
        )
        try:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(sql)
                return list(cur.fetchall())
        finally:
            conn.close()

    import pymysql
    from pymysql.cursors import DictCursor

    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=DictCursor,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return list(cur.fetchall())
    finally:
        conn.close()


def load_hospital_info() -> dict[str, str | None]:
    if DB_TYPE == "postgres":
        sql = "SELECT hospitalcode AS hoscode, hospitalname AS hosname FROM opdconfig LIMIT 1"
    else:
        sql = "SELECT hospitalcode AS hoscode, hospitalname AS hosname FROM opdconfig LIMIT 1"

    rows = run_query(sql)
    first = rows[0] if rows else {}
    return {
        "hoscode": clean_text(first.get("hoscode")),
        "hosname": clean_text(first.get("hosname")),
    }


def clean_text(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text == '""':
        return None
    return text


def clean_int(value: object | None) -> int | None:
    text = clean_text(value)
    if text is None:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def clean_dx_list(value: object | None) -> list[dict[str, str]] | None:
    text = clean_text(value)
    if text is None:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, list) else None


def map_row_to_payload(row: dict[str, object]) -> dict[str, object | None]:
    return {
        "hoscode": clean_text(row.get("hoscode")),
        "hosname": clean_text(row.get("hosname")),
        "hn": clean_text(row.get("hn")),
        "cid": clean_text(row.get("cid")),
        "patient_name": clean_text(row.get("patient_name")),
        "vn": clean_text(row.get("vn")),
        "visit_date": clean_text(row.get("visit_date")),
        "visit_time": clean_text(row.get("visit_time")),
        "sex": clean_text(row.get("sex")),
        "age": clean_int(row.get("age")),
        "house_no": clean_text(row.get("house_no")),
        "moo": clean_text(row.get("moo")),
        "road": clean_text(row.get("road")),
        "tumbon": clean_text(row.get("tumbon")),
        "amphoe": clean_text(row.get("amphoe")),
        "changwat": clean_text(row.get("changwat")),
        "cc": clean_text(row.get("cc")),
        "triage": clean_text(row.get("triage")),
        "status": clean_text(row.get("status")),
        "pdx": clean_text(row.get("pdx")),
        "ext_dx": clean_text(row.get("ext_dx")),
        "dx_list": clean_dx_list(row.get("dx_list")),
        "source": clean_text(row.get("source")) or "auto",
        "alcohol": clean_int(row.get("alcohol")),
    }


def build_api_url(path: str) -> str:
    normalized = PATIENT_API_URL.rstrip("/")
    if normalized.endswith("/api/patient"):
        base = normalized[: -len("/api/patient")]
    else:
        base = normalized
    return f"{base}{path}"


def make_json_request(url: str, payload: dict[str, object | None], include_token: bool) -> dict:
    if include_token:
        token = make_token(PATIENT_API_JWT_SECRET)
        url = f"{url}?token={token}"

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        url=url,
        data=body,
        method="POST",
        headers={"Accept": "application/json", "Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {details}") from exc


def post_sync_log(rows: list[dict[str, object]], hospital_info: dict[str, str | None]) -> dict:
    first = rows[0] if rows else {}
    payload = {
        "hoscode": clean_text(first.get("hoscode")) or hospital_info.get("hoscode"),
        "hosname": clean_text(first.get("hosname")) or hospital_info.get("hosname"),
        "num_pt_case": len(rows),
    }
    return make_json_request(build_api_url("/api/sync-log"), payload, include_token=False)


def post_patient(payload: dict[str, object | None]) -> dict:
    return make_json_request(build_api_url("/api/patient"), payload, include_token=True)


def main() -> int:
    configure_stdio()
    sql = load_query()
    rows = run_query(sql)
    hospital_info = load_hospital_info()
    payloads = [map_row_to_payload(row) for row in rows]
    sync_log_response = post_sync_log(rows, hospital_info)

    results = []
    if not payloads:
        print(
            json.dumps(
                [
                    {
                        "index": 0,
                        "cid": None,
                        "visit_date": None,
                        "sync_log": sync_log_response.get("row", sync_log_response),
                        "response": None,
                    }
                ],
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    for idx, payload in enumerate(payloads, start=1):
        response = post_patient(payload)
        results.append(
            {
                "index": idx,
                "cid": payload.get("cid"),
                "visit_date": payload.get("visit_date"),
                "sync_log": sync_log_response.get("row", sync_log_response) if idx == 1 else None,
                "response": response.get("row", response),
            }
        )
        time.sleep(0.1)

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
