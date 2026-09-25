"""
Sprint 1 — Seed diagram_requests with real Voyage embeddings.

Usage
-----
  python scripts/seed_diagrams.py

Requirements
------------
  - VOYAGE_API_KEY must be set in backend/.env (or as an env var)
  - The Postgres database must be reachable and migrated (alembic upgrade head)

What this script does
---------------------
1. Loads 8 hand-crafted example diagrams (prompt + structured_json + metadata)
2. Calls Voyage AI to generate a REAL 1024-dim embedding for each prompt
3. Inserts each row into diagram_requests (idempotent: skips if prompt already exists)

Run it as many times as you like — it won't duplicate rows.
"""

import sys
import os
import time
import uuid

# ── resolve backend/ as package root ──────────────────────────────────────────
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

from app.core.config import settings  # noqa: E402 — needs dotenv loaded first
from app.core.database import SessionLocal  # noqa: E402
from app.models.diagram_requests import DiagramRequest  # noqa: E402


# ── Seed data ──────────────────────────────────────────────────────────────────
# Each entry: (prompt, diagram_type, complexity, renderer, structured_json)
SEED_DIAGRAMS = [
    (
        "Design a microservices architecture for an e-commerce platform with user, product, order, payment, and notification services",
        "system",
        "high",
        "mermaid",
        {
            "nodes": [
                {"id": "api_gateway", "label": "API Gateway", "type": "gateway"},
                {"id": "user_svc", "label": "User Service", "type": "service"},
                {"id": "product_svc", "label": "Product Service", "type": "service"},
                {"id": "order_svc", "label": "Order Service", "type": "service"},
                {"id": "payment_svc", "label": "Payment Service", "type": "service"},
                {"id": "notification_svc", "label": "Notification Service", "type": "service"},
                {"id": "user_db", "label": "Users DB", "type": "database"},
                {"id": "product_db", "label": "Products DB", "type": "database"},
                {"id": "order_db", "label": "Orders DB", "type": "database"},
            ],
            "edges": [
                {"from": "api_gateway", "to": "user_svc"},
                {"from": "api_gateway", "to": "product_svc"},
                {"from": "api_gateway", "to": "order_svc"},
                {"from": "order_svc", "to": "payment_svc"},
                {"from": "order_svc", "to": "notification_svc"},
                {"from": "user_svc", "to": "user_db"},
                {"from": "product_svc", "to": "product_db"},
                {"from": "order_svc", "to": "order_db"},
            ],
        },
    ),
    (
        "Create a CI/CD pipeline diagram showing source control, build, test, staging, and production deployment stages",
        "pipeline",
        "moderate",
        "mermaid",
        {
            "stages": [
                {"id": "source", "label": "Source Control (Git)", "type": "trigger"},
                {"id": "build", "label": "Build & Compile", "type": "stage"},
                {"id": "unit_test", "label": "Unit Tests", "type": "stage"},
                {"id": "integration_test", "label": "Integration Tests", "type": "stage"},
                {"id": "staging", "label": "Deploy to Staging", "type": "stage"},
                {"id": "smoke_test", "label": "Smoke Tests", "type": "stage"},
                {"id": "prod", "label": "Deploy to Production", "type": "stage"},
            ],
            "edges": [
                {"from": "source", "to": "build"},
                {"from": "build", "to": "unit_test"},
                {"from": "unit_test", "to": "integration_test"},
                {"from": "integration_test", "to": "staging"},
                {"from": "staging", "to": "smoke_test"},
                {"from": "smoke_test", "to": "prod"},
            ],
        },
    ),
    (
        "Draw an entity-relationship diagram for a hospital management system with patients, doctors, appointments, wards, and billing",
        "erd",
        "high",
        "plantuml",
        {
            "entities": [
                {"name": "Patient", "attributes": ["patient_id PK", "name", "dob", "contact"]},
                {"name": "Doctor", "attributes": ["doctor_id PK", "name", "specialty", "department"]},
                {"name": "Appointment", "attributes": ["appt_id PK", "date", "time", "status"]},
                {"name": "Ward", "attributes": ["ward_id PK", "name", "capacity", "floor"]},
                {"name": "Bill", "attributes": ["bill_id PK", "amount", "date", "status"]},
            ],
            "relationships": [
                {"from": "Patient", "to": "Appointment", "type": "has", "cardinality": "1..N"},
                {"from": "Doctor", "to": "Appointment", "type": "manages", "cardinality": "1..N"},
                {"from": "Patient", "to": "Ward", "type": "admitted_to", "cardinality": "N..1"},
                {"from": "Patient", "to": "Bill", "type": "receives", "cardinality": "1..N"},
            ],
        },
    ),
    (
        "Show a sequence diagram for a user login flow with OAuth2, including token exchange and session creation",
        "sequence",
        "moderate",
        "mermaid",
        {
            "participants": ["User", "Browser", "AuthServer", "ResourceServer", "Database"],
            "messages": [
                {"from": "User", "to": "Browser", "label": "Click Login"},
                {"from": "Browser", "to": "AuthServer", "label": "GET /oauth/authorize"},
                {"from": "AuthServer", "to": "Browser", "label": "Redirect to consent screen"},
                {"from": "User", "to": "Browser", "label": "Grant permission"},
                {"from": "Browser", "to": "AuthServer", "label": "POST /oauth/token (code)"},
                {"from": "AuthServer", "to": "Browser", "label": "Return access_token + refresh_token"},
                {"from": "Browser", "to": "ResourceServer", "label": "GET /api/user (Bearer token)"},
                {"from": "ResourceServer", "to": "Database", "label": "Query user by token sub"},
                {"from": "Database", "to": "ResourceServer", "label": "Return user record"},
                {"from": "ResourceServer", "to": "Browser", "label": "200 OK + user data"},
            ],
        },
    ),
    (
        "Create a Kubernetes cluster architecture diagram with ingress controller, multiple pods, services, ConfigMaps, and persistent volumes",
        "infrastructure",
        "high",
        "graphviz",
        {
            "cluster": "production-k8s",
            "namespaces": [
                {
                    "name": "ingress-nginx",
                    "components": [{"type": "Deployment", "name": "nginx-ingress-controller", "replicas": 2}],
                },
                {
                    "name": "app",
                    "components": [
                        {"type": "Deployment", "name": "api-server", "replicas": 3},
                        {"type": "Deployment", "name": "worker", "replicas": 2},
                        {"type": "Service", "name": "api-service", "port": 8000},
                        {"type": "ConfigMap", "name": "app-config"},
                        {"type": "PersistentVolumeClaim", "name": "app-storage", "size": "50Gi"},
                    ],
                },
                {
                    "name": "monitoring",
                    "components": [
                        {"type": "Deployment", "name": "prometheus", "replicas": 1},
                        {"type": "Deployment", "name": "grafana", "replicas": 1},
                    ],
                },
            ],
        },
    ),
    (
        "Design a real-time chat application architecture with WebSocket connections, message queues, Redis pub/sub, and MongoDB storage",
        "system",
        "high",
        "mermaid",
        {
            "nodes": [
                {"id": "client", "label": "Chat Client (Web/Mobile)", "type": "client"},
                {"id": "lb", "label": "Load Balancer", "type": "infrastructure"},
                {"id": "ws_server", "label": "WebSocket Server", "type": "service"},
                {"id": "redis", "label": "Redis Pub/Sub", "type": "cache"},
                {"id": "mq", "label": "Message Queue (RabbitMQ)", "type": "queue"},
                {"id": "mongo", "label": "MongoDB", "type": "database"},
                {"id": "presence", "label": "Presence Service", "type": "service"},
                {"id": "push", "label": "Push Notification Service", "type": "service"},
            ],
            "edges": [
                {"from": "client", "to": "lb", "label": "WSS"},
                {"from": "lb", "to": "ws_server"},
                {"from": "ws_server", "to": "redis", "label": "publish/subscribe"},
                {"from": "ws_server", "to": "mq", "label": "enqueue message"},
                {"from": "mq", "to": "mongo", "label": "persist"},
                {"from": "ws_server", "to": "presence"},
                {"from": "mq", "to": "push"},
            ],
        },
    ),
    (
        "Flowchart for an order processing workflow: receive order, validate payment, check inventory, fulfil or backorder, ship, notify customer",
        "flowchart",
        "moderate",
        "mermaid",
        {
            "nodes": [
                {"id": "start", "label": "Order Received", "type": "start"},
                {"id": "validate", "label": "Validate Payment", "type": "process"},
                {"id": "payment_ok", "label": "Payment Valid?", "type": "decision"},
                {"id": "check_inv", "label": "Check Inventory", "type": "process"},
                {"id": "in_stock", "label": "In Stock?", "type": "decision"},
                {"id": "fulfil", "label": "Fulfil Order", "type": "process"},
                {"id": "backorder", "label": "Backorder Item", "type": "process"},
                {"id": "ship", "label": "Ship Order", "type": "process"},
                {"id": "notify", "label": "Notify Customer", "type": "process"},
                {"id": "reject", "label": "Reject & Refund", "type": "process"},
                {"id": "end", "label": "Done", "type": "end"},
            ],
            "edges": [
                {"from": "start", "to": "validate"},
                {"from": "validate", "to": "payment_ok"},
                {"from": "payment_ok", "to": "check_inv", "label": "Yes"},
                {"from": "payment_ok", "to": "reject", "label": "No"},
                {"from": "check_inv", "to": "in_stock"},
                {"from": "in_stock", "to": "fulfil", "label": "Yes"},
                {"from": "in_stock", "to": "backorder", "label": "No"},
                {"from": "fulfil", "to": "ship"},
                {"from": "ship", "to": "notify"},
                {"from": "notify", "to": "end"},
                {"from": "backorder", "to": "end"},
                {"from": "reject", "to": "end"},
            ],
        },
    ),
    (
        "Show the AWS three-tier architecture for a web application: Route53, CloudFront, ALB, EC2 auto-scaling group, RDS Multi-AZ, and ElastiCache",
        "infrastructure",
        "high",
        "graphviz",
        {
            "provider": "AWS",
            "tiers": [
                {
                    "name": "Edge",
                    "components": [
                        {"type": "Route53", "label": "DNS"},
                        {"type": "CloudFront", "label": "CDN"},
                    ],
                },
                {
                    "name": "Web",
                    "components": [
                        {"type": "ALB", "label": "Application Load Balancer"},
                        {"type": "AutoScalingGroup", "label": "EC2 Web Tier", "min": 2, "max": 10},
                    ],
                },
                {
                    "name": "Data",
                    "components": [
                        {"type": "RDS", "label": "PostgreSQL Multi-AZ"},
                        {"type": "ElastiCache", "label": "Redis Cluster", "nodes": 3},
                        {"type": "S3", "label": "Static Assets Bucket"},
                    ],
                },
            ],
            "vpc": {"cidr": "10.0.0.0/16", "azs": ["us-east-1a", "us-east-1b"]},
        },
    ),
]


# ── Voyage embedder (with rate-limit retry) ───────────────────────────────────

# Free tier without payment method: 3 RPM / 10K TPM.
# We retry up to 5 times with exponential back-off so the script never crashes
# on a 429 — it just waits and continues.
_RETRY_DELAYS = [21, 30, 60, 90, 120]  # seconds between retry attempts


def embed_texts(texts: list[str], api_key: str, model: str = "voyage-3-large") -> list[list[float]]:
    """
    Call Voyage AI to embed *texts* and return their embeddings.

    Automatically retries on RateLimitError with increasing wait times so the
    script works on the free tier (3 RPM) without crashing.
    """
    import voyageai

    client = voyageai.Client(api_key=api_key)

    for attempt, wait in enumerate([0] + _RETRY_DELAYS, start=1):
        if wait:
            print(f"  ⏳ Rate-limited — waiting {wait}s before retry #{attempt}...")
            time.sleep(wait)

        try:
            print(f"  Calling Voyage AI ({model}) for {len(texts)} text(s)...")
            result = client.embed(texts, model=model, input_type="document")
            embeddings = result.embeddings
            if not embeddings or len(embeddings) != len(texts):
                raise ValueError(
                    f"Expected {len(texts)} embeddings, got {len(embeddings) if embeddings else 0}"
                )
            return embeddings

        except voyageai.error.RateLimitError as exc:
            if attempt > len(_RETRY_DELAYS):
                print(f"  ✗ Gave up after {attempt} attempts: {exc}")
                raise
            # loop will sleep and retry
            continue

    # unreachable — loop always raises or returns
    raise RuntimeError("embed_texts: unexpected exit from retry loop")


# ── Main seeder ───────────────────────────────────────────────────────────────

def main() -> None:
    api_key = settings.VOYAGE_API_KEY
    if not api_key:
        print("ERROR: VOYAGE_API_KEY is not set.  Add it to backend/.env and retry.")
        sys.exit(1)

    print(f"\nSeeding {len(SEED_DIAGRAMS)} diagram(s) into 'diagram_requests'...\n")

    db = SessionLocal()
    inserted = 0
    skipped = 0

    try:
        for i, (prompt, dtype, complexity, renderer, sjson) in enumerate(SEED_DIAGRAMS, 1):
            # Idempotency check — skip if this exact prompt already exists
            existing = db.query(DiagramRequest).filter(DiagramRequest.prompt == prompt).first()
            if existing is not None:
                print(f"  [{i}/{len(SEED_DIAGRAMS)}] SKIP (already seeded): {prompt[:60]}...")
                skipped += 1
                continue

            print(f"  [{i}/{len(SEED_DIAGRAMS)}] Embedding: {prompt[:60]}...")
            embeddings = embed_texts([prompt], api_key=api_key)
            embedding_vector = embeddings[0]

            row = DiagramRequest(
                id=uuid.uuid4(),
                user_id=None,
                prompt=prompt,
                embedding=embedding_vector,
                structured_json=sjson,
                diagram_type=dtype,
                complexity=complexity,
                renderer=renderer,
                status="seeded",
            )
            db.add(row)
            db.commit()
            inserted += 1
            print(f"         ✓ inserted (dim={len(embedding_vector)})")

            # Free tier = 3 RPM max → wait 21 s between calls to stay safe.
            # If you have a payment method on file (standard rate limits),
            # you can reduce this to ~0.5 s.
            if i < len(SEED_DIAGRAMS):
                remaining = len(SEED_DIAGRAMS) - i
                print(f"  ⏳ Waiting 21 s (free-tier rate limit)... [{remaining} diagram(s) remaining]")
                time.sleep(21)

    finally:
        db.close()

    print(f"\nDone. Inserted: {inserted}  Skipped (already present): {skipped}")


if __name__ == "__main__":
    main()
