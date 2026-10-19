# Illegal Prolly 🐾

<div align="center">

<img src="https://media.giphy.com/media/mlvseq9yvZhba/giphy.gif" alt="Evil Cat Plotting" width="360" />

### *Some good things populating soon...*

</div>

---

A curated collection of real-world software engineering interview projects—stepping away from standard DSA trivia and diving into modern practical systems: concurrency, thread safety, state isolation, production-grade error handling, and robust test suites.

> [!NOTE]
> **Source & Origin:**  
> These challenges originate from **LeetCode's new "Projects" feature**, which was introduced under an exclusive early-access preview available for a brief period to non-premium users (ending October 20th). 
> All 15 project specifications, problem statements, and requirements were captured to build clean, documented, and fully tested reference implementations that reflect what is expected in modern engineering interviews.

---

## 🚀 Projects & Progress

| # | Project | Category | Status | Brief Description |
|---|---|---|:---:|---|
| **01** | [**Rate Limiter**](./Proj_01/) [![Video Walkthrough](https://img.shields.io/badge/Video-Google_Drive-4285F4?logo=googledrive&logoColor=white)](https://drive.google.com/file/d/1csICVtpLVmVxx17R0nxo7n9vIs0XbVHP/view?usp=sharing) | Concurrency / API Design | ✅ **Done** | In-memory multi-tenant rate limiter supporting **Sliding Window Log** and **Token Bucket** strategies with continuous token refills, recovery time calculation, and fine-grained thread-safe locking. |
| **02** | **Comments & Replies** | Data Modeling | ⏳ Queued | Two-level hierarchy (`Post -> Comment -> Reply`), independent auto-incrementing IDs, defensive copy snapshot isolation, and thread safety. |
| **03** | **URL Shortener Service** | Full Stack / SQLite API | ⏳ Queued | Flask REST API with SQLite persistence, custom and auto-generated short-codes, TTL expiration, hit counters, and concurrent read-modify-write safety. |
| **04** | **Reservation Service Incident** | Production Debugging | ⏳ Queued | Live booking incident diagnosis: resolving overbooking race conditions, fixing cancellation anomalies, and executing in-place historical DB repairs. |
| **05** | **File Deduplication** | Systems / File I/O | ⏳ Queued | Multi-stage deduplication pipeline with file size filtering, prefix sampling, streaming SHA-256 hashing, byte-by-byte comparison, and bounded memory limits. |
| **06** | **Feature Flag & Experiments** | Systems / Backend | ⏳ Queued | In-memory feature flag service with ordered rule evaluation (first-match AND), deterministic percentage rollout hashing, and immutable returns. |
| **07** | **Image Transform Pipeline** | Concurrency / Scheduling | ⏳ Queued | Batch processing pipeline enforcing ordered transforms, FIFO admission, memory budgeting based on in-flight payload sizes, and lazy stream consumption. |
| **08** | **Loan Lifecycle & Balances** | Fintech / State Machines | ⏳ Queued | Financial loan state machine (`pending -> active -> repaid`), balance conservation laws, atomic multi-step mutations, and snapshot isolation. |
| **09** | **Return Risk Assessment** | Logic & Type Safety | ⏳ Queued | Risk evaluation pipeline enforcing strict type integrity (`bool` vs `int`), component scoring, threshold rules, and batch error isolation. |
| **10** | **Comment Moderation** | Backend / Fault Isolation | ⏳ Queued | In-memory comment service backed by an external checker, strike tracking, auto-blocking, and atomic rollback on checker failure. |
| **11** | **Retry-Safe Issue Service** | Distributed API Design | ⏳ Queued | High-reliability issue tracker featuring idempotency keys for retry safety, optimistic locking (versioning) for concurrent edits, and cursor pagination. |
| **12** | **Movie Recommendation** | Algorithms / Data Processing | ⏳ Queued | Personalization engine with candidate filtering, genre preference weighting, cold-start fallback, and deterministic multi-level tie-breaking. |
| **13** | **Keyword & User Blocking** | Systems / Content Safety | ⏳ Queued | Content admission gateway with string normalization, substring matching, strike accumulation, auto-blocking, and atomic configuration updates. |
| **14** | **Private Watchlists** | SQLite / Persistence | ⏳ Queued | SQLite-backed watchlist service with user ownership boundaries, duplicate item handling, safe deletion, and multi-instance transaction commits. |
| **15** | **Password Reset Workflow** | Security / Time Handling | ⏳ Queued | Recovery workflow handling timezone-aware vs naive datetimes, exact 30s validity windows, single-use token consumption, and storage boundaries. |

---

## 🧪 Testing & Verification

Run the entire automated test suite:

```bash
python -m pytest -v
```
