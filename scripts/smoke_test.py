"""End-to-end smoke test for the ingestion pipeline.

Registers a document, uploads matching content (which enqueues a job), waits for
the worker to index it, then prints the resulting chunks and the job status.

Run with the API and the worker both running:
    python scripts/smoke_test.py
Optionally point at a different base URL:
    python scripts/smoke_test.py http://localhost:8000
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
import uuid

BASE_URL = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8000"

CONTENT = (
    "Databases organize information so it can be queried efficiently.\n"
    "Indexes trade write cost for read speed by maintaining sorted structures.\n\n"
    "Retrieval augmented generation grounds a model in retrieved passages.\n"
    "Chunking splits documents so relevant spans can be embedded and searched.\n"
)


def request(method: str, path: str, tenant: str, body: dict | None = None) -> tuple[int, dict | None]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "X-Tenant-ID": tenant},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()
        print(f"  ERROR {exc.code} on {method} {path}: {detail}")
        raise SystemExit(1) from exc
    except urllib.error.URLError as exc:
        print(f"  Could not reach {BASE_URL}. Is the API running? ({exc.reason})")
        raise SystemExit(1) from exc


def main() -> None:
    tenant = str(uuid.uuid4())
    collection = str(uuid.uuid4())
    content_hash = hashlib.sha256(CONTENT.encode()).hexdigest()
    print(f"tenant     = {tenant}")
    print(f"collection = {collection}")

    print("\n1. registering document...")
    _, doc = request(
        "POST", "/v1/documents", tenant,
        {
            "collection_id": collection,
            "title": "Smoke Test Document",
            "source_type": "upload",
            "source_uri": "s3://bucket/key",
            "content_hash": content_hash,
        },
    )
    document_id = doc["id"]
    print(f"   document_id = {document_id}  status = {doc['status']}")

    print("\n2. uploading content (enqueues ingestion job)...")
    status, _ = request("POST", f"/v1/documents/{document_id}/content", tenant, {"content": CONTENT})
    print(f"   accepted (HTTP {status})")

    print("\n3. waiting for the worker to index...")
    final_status = None
    for _ in range(20):
        _, current = request("GET", f"/v1/documents/{document_id}", tenant)
        final_status = current["status"]
        if final_status in ("indexed", "failed"):
            break
        time.sleep(0.5)
    print(f"   document status = {final_status}")

    print("\n4. chunks produced:")
    _, chunks = request("GET", f"/v1/documents/{document_id}/chunks", tenant)
    print(f"   count = {chunks['count']}")
    for item in chunks["items"]:
        preview = item["text"][:70].replace("\n", " ")
        print(f"   [{item['ordinal']}] dim={item['dimension']}  {preview}...")

    print("\n5. ingestion job:")
    _, jobs = request("GET", "/v1/ingestion/jobs", tenant)
    for job in jobs["items"]:
        print(f"   status={job['status']}  attempts={job['attempts']}/{job['max_attempts']}")

    print("\ndone." if final_status == "indexed" else "\nfinished, but the document did not reach 'indexed'.")


if __name__ == "__main__":
    main()