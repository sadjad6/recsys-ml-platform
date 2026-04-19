# Architectural Decisions — Real-Time Recommendation System

## ADR-001: Apache Kafka for Event Streaming

**Decision:** Use Apache Kafka as the event streaming platform.

**Rationale:**
- Industry standard with proven scalability and durable message storage
- Native Spark Structured Streaming integration
- Supports multiple consumer groups (streaming, online learning, monitoring)
- Partitioning enables horizontal throughput scaling

**Alternatives Considered:**
- **RabbitMQ**: Lacks log-based durability and replay needed for ML pipelines
- **Apache Pulsar**: Smaller ecosystem, less mature Spark integration
- **AWS Kinesis**: Vendor lock-in; requires local Docker deployment

---

## ADR-002: ALS for Candidate Generation

**Decision:** Use ALS via PySpark MLlib for Stage 1 candidate generation.

**Rationale:**
- Native PySpark — scales without additional dependencies
- Handles implicit feedback natively
- Generates embeddings that support incremental updates for online learning

**Alternatives Considered:**
- **Neural Collaborative Filtering**: Requires GPU infra and deep learning stack
- **Two-Tower Models**: Requires TF Serving / Triton — out of scope

---

## ADR-003: Multi-Stage Pipeline (Candidate → Ranking → Re-Ranking)

**Decision:** 3-stage pipeline following industry patterns (YouTube, Netflix).

**Rationale:**
- Separates fast/broad candidate gen from precise/expensive ranking
- Re-ranking enables business logic injection without retraining
- Each stage independently improvable and testable

**Alternatives Considered:**
- **Single-model**: Cannot scale to large item catalogs
- **Two-stage (no re-ranking)**: Loses business rule injection capability

---

## ADR-004: Redis for Recommendation Caching

**Decision:** Cache recommendations in Redis with TTL-based expiration.

**Rationale:**
- Sub-millisecond reads; reduces Model Service load
- Simple `user_id → recommendations` key-value model
- Shared across service replicas

**Alternatives Considered:**
- **Memcached**: Lacks persistence and data structures
- **Application LRU cache**: Not shared across replicas

---

## ADR-005: Hash-Based A/B Testing Assignment

**Decision:** Deterministic `hash(user_id + experiment_id) % 100` for bucketing.

**Rationale:**
- Reproducible, sticky assignments — same user always sees same variant
- No external dependency; easily auditable
- Supports concurrent experiments with orthogonal bucketing

**Alternatives Considered:**
- **Random + DB persistence**: Adds latency per request
- **Feature flag service**: Adds operational complexity

---

## ADR-006: Online Learning via Incremental Updates

**Decision:** Incremental user embedding updates + warm-start retraining.

**Rationale:**
- ALS embeddings can be efficiently updated per-user
- Feature store updates provide immediate personalization
- Warm-start converges faster than cold-start
- < 5 min adaptation latency is sufficient for e-commerce

**Alternatives Considered:**
- **Full online SGD**: Unstable on sparse implicit feedback
- **Real-time full retraining**: Too expensive

---

## ADR-007: FastAPI for Microservices

**Decision:** FastAPI for all services.

**Rationale:**
- Async-first with native `asyncio` support
- Auto-generates OpenAPI docs from type hints
- Pydantic validation; Prometheus client integration

**Alternatives Considered:**
- **Flask**: Lacks native async and auto-documentation
- **gRPC**: Adds complexity for frontend integration

---

## ADR-008: MLflow for ML Lifecycle

**Decision:** MLflow for experiment tracking, model versioning, and registry.

**Rationale:**
- Single tool covers tracking, artifacts, and registry
- Model staging supports A/B testing workflows
- Python-native with PySpark integration

**Alternatives Considered:**
- **Weights & Biases**: SaaS-first; self-hosting less mature
- **Kubeflow**: Too heavyweight for tracking-only needs

---

## ADR-009: Prometheus + Grafana for Monitoring

**Decision:** Prometheus scrapes metrics; Grafana visualizes.

**Rationale:**
- Pull-based model is trivial to implement in FastAPI
- PromQL enables powerful alerting
- Industry standard, open-source, extensive community

**Alternatives Considered:**
- **Datadog**: SaaS-only with cost implications
- **ELK Stack**: Better for logs, not metrics

---

## ADR-010: Evidently for Drift Detection

**Decision:** Evidently for data and model drift detection.

**Rationale:**
- Purpose-built for ML monitoring
- Generates HTML reports storable as MLflow artifacts
- Lightweight; integrates into Airflow DAGs

**Alternatives Considered:**
- **Great Expectations**: Lacks ML-specific drift detection
- **Custom drift logic**: Maintenance burden

---

## ADR-011: Parquet/Delta for Feature Store

**Decision:** Parquet files (optional Delta Lake) as feature store.

**Rationale:**
- Columnar format optimized for Spark reads
- Schema evolution support; partitioned by date
- No additional infrastructure needed

**Alternatives Considered:**
- **Feast**: Adds significant operational complexity
- **PostgreSQL**: Not optimized for Spark analytical reads

---

## ADR-012: Docker Compose + Kubernetes

**Decision:** Docker Compose for local dev, Kubernetes for production.

**Rationale:**
- Single-command local startup; production-grade K8s orchestration
- Same Docker images in both environments
- ConfigMaps/Secrets for environment-specific config

**Alternatives Considered:**
- **Docker Swarm**: Lacks K8s ecosystem and scaling
- **K8s-only (minikube)**: Higher local resource requirements
