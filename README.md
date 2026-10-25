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

| # | Project | Category | Status | Automated Tests | Brief Description |
|---|---|---|:---:|:---:|---|
| **01** | [**Rate Limiter**](./Proj_01/) [![Video Walkthrough](https://img.shields.io/badge/Video-Google_Drive-4285F4?logo=googledrive&logoColor=white)](https://drive.google.com/file/d/1csICVtpLVmVxx17R0nxo7n9vIs0XbVHP/view?usp=sharing) | Concurrency / API Design | ✅ **Done** | `12 / 12 Passing` | In-memory multi-tenant rate limiter supporting **Sliding Window Log** and **Token Bucket** strategies with continuous token refills, recovery time calculation, and fine-grained thread-safe locking. |
| **02** | [**Comments & Replies**](./Proj_02/) [![Video Walkthrough](https://img.shields.io/badge/Video-Google_Drive-4285F4?logo=googledrive&logoColor=white)](https://drive.google.com/file/d/1alYAw-82A4aL1VaW2gQxndwNYka4aTOK/view?usp=sharing) | Data Modeling | ✅ **Done** | `30 / 30 Passing` | Two-level hierarchy (`Post -> Comment -> Reply`), independent auto-incrementing IDs, defensive copy snapshot isolation, and thread safety. |
| **03** | [**URL Shortener Service**](./Proj_03/) [![Video Walkthrough](https://img.shields.io/badge/Video-Google_Drive-4285F4?logo=googledrive&logoColor=white)](https://drive.google.com/file/d/18TOwuVrRbh_QpoLwfpNDav7uQnets9kN/view?usp=sharing) | Full Stack / SQLite API | ✅ **Done** | `21 / 21 Passing` | Flask REST API with SQLite persistence, custom and auto-generated short-codes, TTL expiration, hit counters, and concurrent read-modify-write safety. |
| **04** | [**Reservation Service Incident**](./Proj_04/) [![Video Walkthrough](https://img.shields.io/badge/Video-Google_Drive-4285F4?logo=googledrive&logoColor=white)](https://drive.google.com/file/d/1AB4pEInBqioXpBjXLIoCPz_N4sURLbst/view?usp=sharing) | Production Debugging | ✅ **Done** | `31 / 31 Passing` | Live booking incident diagnosis: resolving overbooking race conditions, fixing cancellation anomalies, and executing in-place historical DB repairs. |
| **05** | **File Deduplication** | Systems / File I/O | ⏳ Queued | — | Multi-stage deduplication pipeline with file size filtering, prefix sampling, streaming SHA-256 hashing, byte-by-byte comparison, and bounded memory limits. |
| **06** | [**Feature Flag & Experiments**](./Proj_06/) [![Video Walkthrough](https://img.shields.io/badge/Video-Google_Drive-4285F4?logo=googledrive&logoColor=white)](https://drive.google.com/file/d/1yt8-pTEtfUqeAtd9wg8mm5rX7aEXgH4Q/view?usp=sharing) | Systems / Backend | ✅ **Done** | `34 / 34 Passing` | In-memory feature flag service with ordered rule evaluation (first-match AND), deterministic percentage rollout hashing, and immutable returns. |
| **07** | [**Image Transform Pipeline**](./Proj_07/) [![Video Walkthrough](https://img.shields.io/badge/Video-Google_Drive-4285F4?logo=googledrive&logoColor=white)](https://drive.google.com/file/d/1YP1BlzgUOpqJDH5-FgT7lzwo6eWZ9GmY/view?usp=sharing) | Concurrency / Scheduling | ✅ **Done** | `17 / 17 Passing` | Batch processing pipeline enforcing ordered transforms, FIFO admission, memory budgeting based on in-flight payload sizes, and lazy stream consumption. |
| **08** | **Loan Lifecycle & Balances** | Fintech / State Machines | ⏳ Queued | — | Financial loan state machine (`pending -> active -> repaid`), balance conservation laws, atomic multi-step mutations, and snapshot isolation. |
| **09** | [**Return Risk Assessment**](./Proj_09/) [![Video Walkthrough](https://img.shields.io/badge/Video-Google_Drive-4285F4?logo=googledrive&logoColor=white)](https://drive.google.com/file/d/1oq97qDN4JaX8iFCrvrcmd2TisX3pd5Ds/view?usp=sharing) | Logic & Type Safety | ✅ **Done** | `21 / 21 Passing` | Risk evaluation pipeline enforcing strict type integrity (`bool` vs `int`), component scoring, threshold rules, and batch error isolation. |
| **10** | [**Comment Moderation**](./Proj_10/) [![Video Walkthrough](https://img.shields.io/badge/Video-Google_Drive-4285F4?logo=googledrive&logoColor=white)](https://drive.google.com/file/d/1XEIIKV9zv6iWv-eYu1K8vHfpT6bwCO8E/view?usp=sharing) | Backend / Fault Isolation | ✅ **Done** | `28 / 28 Passing` | In-memory comment service backed by an external checker, strike tracking, auto-blocking, and atomic rollback on checker failure. |
| **11** | [**Retry-Safe Issue Service**](./Proj_11/) | Distributed API Design | 🟡 **In Progress** | `28 / 28 Passing` | High-reliability issue tracker featuring idempotency keys for retry safety, optimistic locking (versioning) for concurrent edits, and cursor pagination. |
| **12** | **Movie Recommendation** | Algorithms / Data Processing | ⏳ Queued | — | Personalization engine with candidate filtering, genre preference weighting, cold-start fallback, and deterministic multi-level tie-breaking. |
| **13** | **Keyword & User Blocking** | Systems / Content Safety | ⏳ Queued | — | Content admission gateway with string normalization, substring matching, strike accumulation, auto-blocking, and atomic configuration updates. |
| **14** | [**Private Watchlists**](./Proj_14/) [![Video Walkthrough](https://img.shields.io/badge/Video-Google_Drive-4285F4?logo=googledrive&logoColor=white)](https://drive.google.com/file/d/1EzjQ8Nak1oAkPVF_XPLWWIhkascuK10I/view?usp=sharing) | SQLite / Persistence | ✅ **Done** | `23 / 23 Passing` | SQLite-backed watchlist service with user ownership boundaries, duplicate item handling, safe deletion, and multi-instance transaction commits. |
| **15** | [**Password Reset Workflow**](./Proj_15/) [![Video Walkthrough](https://img.shields.io/badge/Video-Google_Drive-4285F4?logo=googledrive&logoColor=white)](https://drive.google.com/file/d/1IVOQyueKy-K38i3KBWaiMjup2p2lA2vn/view?usp=sharing) | Security / Time Handling | ✅ **Done** | `21 / 21 Passing` | Recovery workflow handling timezone-aware vs naive datetimes, exact 30s validity windows, single-use token consumption, and storage boundaries. |

---

## 🧪 Testing & Verification

Currently **266 / 266 tests passing** across 11 projects.

Run the entire automated test suite:

```bash
python -m pytest -v
```
