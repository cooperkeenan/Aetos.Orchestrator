# Aetos Orchestrator

Microservice orchestrator that manages the complete buy/resell lifecycle for cameras (and future products). It coordinates **ScraperV2**, **Chatterbot**, **eBayLister**, and **TelegramNotifier** through a strict state machine, persisting all events to PostgreSQL and publishing domain events via RabbitMQ.

---

## Architecture

```
aetos-orchestrator/
├── src/
│   ├── domain/              # Pure business logic — no framework dependencies
│   │   ├── entities/        # ProductListing aggregate
│   │   ├── enums/           # ListingState enum
│   │   ├── state_machine/   # LifecycleStateMachine (validates all transitions)
│   │   └── events/          # Domain events (ListingCreated, StateChanged, …)
│   ├── application/         # Use cases + port interfaces
│   │   ├── use_cases/       # CreateListingsFromScraper, TransitionListingState, …
│   │   ├── interfaces/      # ListingRepository, EventPublisher, ServiceCoordinator
│   │   └── coordinators/    # ScraperCoordinator (impl), Chatterbot/eBay (stubs)
│   ├── infrastructure/      # Adapters for external concerns
│   │   ├── database/        # SQLAlchemy models + repository implementations
│   │   ├── messaging/       # RabbitMQ publisher/consumer + no-op publisher
│   │   └── external_services/ # ScraperClient (httpx)
│   └── api/                 # FastAPI application
│       ├── routes/          # /health, /webhooks, /admin
│       ├── schemas/         # Pydantic request/response models
│       └── dependencies.py  # DI wiring
├── tests/
│   ├── unit/                # State machine, entity, use case tests
│   └── integration/         # API contract tests (all deps mocked)
├── alembic/                 # Database migrations
├── docker-compose.yml
└── Dockerfile
```

### Design Principles

- **Clean Architecture** — domain layer has zero infrastructure imports
- **SOLID** throughout — single-responsibility use cases, interface-segregated ports
- **Repository Pattern** — `SqlAlchemyListingRepository` implements `ListingRepository` port
- **Event-Driven** — every state change emits a domain event published to RabbitMQ
- **State Machine** — `LifecycleStateMachine` enforces all valid/invalid transitions centrally
- **Extensible** — adding VR headsets requires zero changes to the orchestration logic; just new product_ids

---

## Product Lifecycle

```
FOUND → MESSAGING → NEGOTIATING → PURCHASED → RECEIVED → LISTED → SOLD
  ↓         ↓            ↓            ↓
CANCELLED CANCELLED  CANCELLED   CANCELLED
```

**Phase 1 (implemented):** FOUND → MESSAGING → CANCELLED
**Phase 2 (stubs ready):** Chatterbot integration → NEGOTIATING → PURCHASED
**Phase 3 (stubs ready):** eBayLister integration → RECEIVED → LISTED → SOLD

---

## Quick Start

### Prerequisites
- Docker & Docker Compose

### Run with Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

The orchestrator will be available at `http://localhost:8000`.
RabbitMQ management UI: `http://localhost:15672` (aetos/aetos).

### Interactive API docs

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Local Development (without Docker)

```bash
# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env to point to your local Postgres and RabbitMQ

# Run migrations
alembic -c alembic/alembic.ini upgrade head

# Start the API
uvicorn src.api.main:app --reload
```

---

## Running Tests

```bash
# Unit tests (no external dependencies)
pytest tests/unit/ -v

# Integration tests (API contract — all deps mocked)
pytest tests/integration/ -v

# All tests
pytest -v
```

---

## API Reference

### Health

```
GET /health
→ { "status": "healthy", "database": "connected", "rabbitmq": "connected" }
```

### Webhooks (ScraperV2 → Orchestrator)

```
POST /webhooks/scraper/job-complete
Body: {
  "job_id": "uuid",
  "brand": "Sony",
  "matches": [
    {
      "listing": { "url": "...", "title": "Sony A6400", "price": 400.0 },
      "product": { "id": 230, "brand": "Sony", "model": "a6400" },
      "confidence": 95.0,
      "potential_profit": 100.0
    }
  ]
}
→ 202 { "accepted": true, "created_listings": 1, "skipped": 0 }
```

### Admin API

```
# List listings (filterable by state and brand)
GET /admin/listings?state=FOUND&brand=Sony&limit=50&offset=0

# Get a single listing
GET /admin/listings/{listing_id}

# Get full state transition history
GET /admin/listings/{listing_id}/history

# Manually transition state (admin override / testing)
POST /admin/listings/{listing_id}/transition
Body: { "to_state": "CANCELLED", "reason": "Seller not responding" }

# Trigger a scrape job
POST /admin/scrape/trigger
Body: { "brand": "Sony", "search": "Sony mirrorless cameras" }
```

---

## RabbitMQ Events

Exchange: `orchestrator.events` (topic)

| Routing Key | Published When |
|---|---|
| `scraper.job.created` | Scrape job triggered via admin API |
| `listing.created` | New listing created from scraper webhook |
| `listing.state.messaging` | Listing sent to Chatterbot |
| `listing.state.negotiating` | Active negotiation started |
| `listing.state.purchased` | Deal confirmed |
| `listing.state.received` | Photos uploaded |
| `listing.state.listed` | eBay listing created |
| `listing.state.sold` | eBay item sold |
| `listing.state.cancelled` | Listing cancelled |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://aetos:aetos@localhost:5432/aetos_orchestrator` | PostgreSQL connection string |
| `RABBITMQ_URL` | `amqp://aetos:aetos@localhost:5672/` | RabbitMQ connection string |
| `SCRAPER_API_URL` | `http://scraperv2:8000` | ScraperV2 service base URL |
| `CHATTERBOT_API_URL` | `http://chatterbot:8000` | Chatterbot service base URL (Phase 2) |
| `EBAY_API_URL` | `http://ebaylister:8000` | eBayLister service base URL (Phase 3) |
| `LOG_LEVEL` | `INFO` | structlog log level |

---

## Adding a New Product Type (e.g. VR Headsets)

The orchestrator is product-agnostic. To support VR headsets:

1. Register VR headset product IDs in ScraperV2
2. ScraperV2 posts to the same `/webhooks/scraper/job-complete` endpoint with `brand: "Meta"` (or similar)
3. The orchestrator creates listings with those product IDs — zero code changes needed

The `product_id` field references an external product catalogue. The orchestrator does not need to know what the product is, only that it has a lifecycle.

---

## Phase 2 / Phase 3 Checklist

### Phase 2 — Chatterbot Integration
- [ ] Implement `ChatterbotCoordinator.send_listing_for_messaging()`
- [ ] Add `POST /webhooks/chatterbot/message-sent` webhook
- [ ] Add `POST /webhooks/chatterbot/deal-confirmed` webhook
- [ ] Wire `FOUND → MESSAGING` transition to call ChatterbotCoordinator
- [ ] Add timeout worker (7-day MESSAGING, 14-day NEGOTIATING auto-cancel)
- [ ] Implement TelegramNotifier for error events

### Phase 3 — eBay Integration
- [ ] Implement `EbayCoordinator.create_listing()`
- [ ] Add photo upload endpoint (Google Drive or Telegram bot)
- [ ] Add `POST /webhooks/ebay/item-sold` endpoint
- [ ] Wire `RECEIVED → LISTED` to call EbayCoordinator
- [ ] Calculate and persist `final_profit` on SOLD
