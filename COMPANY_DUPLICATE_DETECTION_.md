# Hybrid Intelligent Company Duplicate Detection System
## Final consolidated implementation specification — Groups 1–8

> **Status:** All eight engineering groups are consolidated for agent implementation. **This is a build contract, not evidence that code exists, tests have passed, or the client has approved unresolved decisions.** Decisions DEC-01–DEC-03 and the Status-percentage presentation require business-owner sign-off before production acceptance. Real company data is unavailable; synthetic results cannot establish production accuracy.

## Agent execution contract — READ FIRST

- **Implement the app now**; do not stop at planning, an attractive static UI, placeholder buttons or an untested code scaffold. Reuse current workspace where present; inspect before editing.
- **Single source of truth:** Groups 1–4 are defined in sections 2–7 and Appendices A–C; **Group 5 is Appendix D; Group 6 is Appendix E; Group 7 is Appendix F; Group 8 is Appendix G**. Older summary sections point to the appendices and **do not create additional implementations**.
- **Source priority:** direct manager/business rules and client complaints > explicitly approved engineering decisions > colleague reference. Use provisional DEC-01–DEC-03 demo defaults only until the owner confirms them; never claim those defaults are business-approved.
- **Dataset invariant:** **exactly 10,000 synthetic master rows and exactly 200 intentional duplicate groups**; each group has >=2 records, with underlying truth identities assigned by generator independently of fuzzy scoring. All seed runs are deterministic and never silently overwrite existing data.
- **UI invariant:** **three main pages only**; design of Matching Results based on the approved screenshot. The screenshot is a visual reference, not permission to hardcode screenshot metrics or fake backend responses.
- **AI invariant:** `AI_VERIFICATION_ENABLED=false` by default. Core upload, compare, results, review, export, tests and deployment work with optional AI code/packages/providers absent. No paid API requests during synthetic demo; mock evidence when testing optional features.
- **No duplicate logic:** one normalization service, one candidate-retrieval pipeline, one match/classify pipeline, one result upsert path, one review-event writer, one export service, one optional verification pipeline.
- **Quality gate:** run automated tests and a real end-to-end smoke test. Never assert accuracy, performance, security or completion without measured proof. Do not weaken tests or silently alter rules to obtain green results. If unavailable resources block a feature, state exactly what was tested, what remains blocked and why.

## 1. Objective and scope

Build an independently demonstrable web application that accepts a CSV of companies, checks each incoming record against a synthetic company master, identifies potential duplicate legal entities, exposes evidence, preserves entity IDs, supports human review, and exports accurate results. Initial demo workload: 10 uploaded rows against 10,000 synthetic master rows. Scale tests: 100,000 and 1,000,000 master records.

Success means: low latency; high candidate recall; no fake IDs, fabricated scores or duplicate summary rows; transparent matching evidence; repeatable benchmarks. No automatic merge, update or delete of master company records.

## 2. Group 1 — business requirements and decision authority

**Design status: FINAL ENGINEERING BASELINE; three business-owner approvals remain open.** This means the behavior below is implementable and testable for the local demo, but must not be described as client-approved or production-accepted until the open decisions are signed off.

### 2.1 Sources and priority

1. **Manager/team message (primary requirements):** domain and LinkedIn matching; fuzzy comparison of *Legal Names* with an 80% minimum when both identifiers are blank; required displayed columns `Company Name`, `Website Domain`, `LinkedIn`, `Status` (percentage). The message does **not** fully specify pair-side missing-value semantics or how the percentage is derived.
2. **Client complaints (primary acceptance outcomes):** responsive tool; discover Trimark-like look-alikes; preserve real `Entity ID` (not `IMPORT_BATCH`); show matched `Legal Name` next to ID in every export; no repeated companies in the Potential Duplicate download; compare website **domains**, not raw URL strings; measure and report actual matching accuracy.
3. **Teammate Antigravity specification (reference implementation, not higher authority):** 10 incoming CSV rows against 10,000 SQLite entities; normalized identifier matching; SQL/master-side both-identifiers-blank fuzzy fallback using the best of four name-field combinations; conflict handling; separate reviews; all matching candidate pairs; Flask/SQLite prototype.
4. **Our independent hybrid proposal (optional enhancements):** multi-pass candidate retrieval, separate related-name discovery, selective web enrichment, LLM evidence review, alternative stack. Enhancements must **not silently change** rules 1–2.

### 2.2 Three unresolved business-owner decisions (explicit sign-off)

| Decision ID | Unresolved point | Demo behavior selected provisionally | Release gate |
|---|---|---|---|
| DEC-01 | Does “both identifiers blank” refer to master record alone or **both** records? | Use teammate's SQL/master-side rule: master website AND LinkedIn are missing/unusable; upload may have identifiers. | Obtain written owner confirmation before production. |
| DEC-02 | Should 80% compare Legal Name only or the maximum of four company/legal-name combinations? | **Legal Name-to-Legal Name** controls mandatory 80% classification. Other combinations may appear as supplementary discovery evidence, never silently override the legal-name rule. | Obtain written owner confirmation before changing mandatory classification. |
| DEC-03 | Does “one row per company” mean unique incoming company or unique matched master Entity ID? | Provide **both**: uploaded-company outcomes (one row per upload row) and master-company summary (one row per master Entity ID), plus detailed unique pair export. This resolves ambiguity without hiding relationships. | Confirm which view is the client-designated “Potential Duplicate” download. |

### 2.3 Terms and scope

- **Incoming/uploaded company:** a single CSV row; identified by `(run_id, upload_row_id)`, not by company name.
- **Master company:** a persisted SQL/SQLite entity; identified by authoritative `entity_id`.
- **Candidate pair:** unique `(run_id, upload_row_id, entity_id)`; multiple master candidates for one uploaded row are allowed.
- **Duplicate:** potentially the **same legal entity**; a shared brand, parent/subsidiary relationship or name resemblance alone is not proof.
- **Related-name lead:** similar naming discovered for investigation; does **not** imply duplicate, does **not** count as a mandatory fuzzy match, and must be visually/export-wise separate.
- **Match evidence score / name similarity:** descriptive evidence, **not** measured system accuracy or calibrated duplicate probability.
- **Out of scope:** automatic merge, update or deletion of master records; claiming company identities have been verified from simulated data.

## 3. Group 1 — final demo matching and classification rules

### 3.1 Canonical comparison states

For **each identifier type separately** (`web_domain`, `linkedin_url`):

- `MATCH`: both valid normalized identifiers are equal.
- `CONFLICT`: both valid normalized identifiers exist but differ.
- `UNAVAILABLE`: one or both values missing, blank or invalid. Blank-versus-blank is **never** a match. Retain raw invalid values and validation reasons for audit.

For fuzzy eligibility, `master_both_unavailable = master.normalized_domain IS NULL AND master.normalized_linkedin IS NULL`. A syntactically invalid populated identifier is unusable for comparison but must be flagged in evidence; whether it should count as “blank” for production is included under DEC-01.

### 3.2 One authoritative rule matrix (evaluate in this priority order)

| Rule | Website | LinkedIn | Other condition | Demo result | Implementation obligation |
|---|---|---|---|---|---|
| BR-01 | MATCH | MATCH | — | High-confidence Duplicate Candidate | Record both exact evidences; **candidate**, not legal identity confirmation. |
| BR-02 | MATCH | UNAVAILABLE | — | High-confidence Duplicate Candidate | Record domain evidence and unavailable LinkedIn reason. |
| BR-03 | UNAVAILABLE | MATCH | — | High-confidence Duplicate Candidate | Record LinkedIn evidence and unavailable-domain reason. |
| BR-04 | MATCH | CONFLICT | — | Needs Review | Conflict overrides exact hit; retain both fields. |
| BR-05 | CONFLICT | MATCH | — | Needs Review | Conflict overrides exact hit; retain both fields. |
| BR-06 | CONFLICT | CONFLICT | — | Not a Match (identifier rules) | Can appear separately as `Related-name lead` after approved discovery; never automatically a duplicate. |
| BR-07 | UNAVAILABLE | UNAVAILABLE | master_both_unavailable AND both legal names usable AND normalized legal-name similarity >= configured threshold (default 80%) | Potential Duplicate | Record actual algorithm and pairwise score; exactly 80 qualifies. |
| BR-08 | UNAVAILABLE | UNAVAILABLE | master_both_unavailable AND both legal names usable AND similarity < threshold | Not a Match | Do not output as qualifying candidate pair; still provide uploaded-company outcome. |
| BR-09 | UNAVAILABLE | UNAVAILABLE | master_both_unavailable AND either legal name unusable | Insufficient Data | No fabricated similarity. Optional other-name similarities are supplemental only until DEC-02 signed off. |
| BR-10 | CONFLICT | UNAVAILABLE | master has one or more usable identifiers; no matching identifier | Not a Match (identifier rules) | Do **not** run mandatory fuzzy fallback. Optional distinct related-name lead only. |
| BR-11 | UNAVAILABLE | CONFLICT | master has one or more usable identifiers; no matching identifier | Not a Match (identifier rules) | Do **not** run mandatory fuzzy fallback. Optional distinct related-name lead only. |
| BR-12 | UNAVAILABLE | UNAVAILABLE | master has usable identifier(s), but upload lacks comparable identifier(s) | Insufficient comparable identifiers | Not an exact match and no mandatory fuzzy fallback; optionally queue separate investigation. |
| BR-13 | Any | Any | candidate matches more than one entity | Keep every unique candidate pair | Never exit after first hit; de-dup on `(run_id, upload_row_id, entity_id)`. |
| BR-14 | Any | Any | exact master entity selected for display/export | Show master `entity_id` + original `legal_name` together | Never substitute `IMPORT_BATCH`; never derive IDs from row position. |
| BR-15 | Any | Any | human decision | Persist `confirmed_duplicate` / `not_duplicate` / `needs_review` separately | Never mutate, merge or delete master entity. |

**Priority:** any MATCH+CONFLICT -> `Needs Review`; otherwise unconflicted MATCH -> `High-confidence Duplicate Candidate`; otherwise mandatory eligible fuzzy score >= threshold -> `Potential Duplicate`; otherwise insufficient comparable information -> `Insufficient Data / insufficient comparable identifiers`; otherwise `Not a Match`. A related-name lead exists in a **different discovery channel** and cannot override these outcomes.

**Edge-condition precision:** When both master identifiers are unavailable but the uploaded record has one or both identifiers, Rule BR-07 still applies **provisionally** per DEC-01. When neither record has valid names or identifiers, only the incoming outcome row is produced, not a spurious candidate pair. Classifications depend on pair evidence, not on a blind `100%` score.

### 3.3 Trimark complaint — separate lead-discovery policy

- Purpose: **show** look-alike names even where both sides have present and different identifiers, without falsely declaring them duplicates.
- Candidate search may use distinctive tokens, character n-grams or auxiliary three-character prefix matching; prefix alone is never match proof.
- `Trimark Property Group` vs `Trimark Property Management` is a **related-name lead** if retrieved, not an automatically confirmed duplicate.
- `Trimark Property Group` vs `Trimark Petroleum Group` is a deliberate **hard negative**: may appear as a lead for investigation, but should not be marked duplicate simply because “Trimark” or “Group” overlap.
- Related-name leads are optional enhancement results (`discovery_type=related_name`), with a reason and similarity value when calculated; they do not count as mandatory fuzzy positive results. Final user-facing inclusion requires business-owner confirmation.

### 3.4 Percentages and client-required columns

- Always provide the required client display fields: `Company Name`, `Website Domain`, `LinkedIn`, `Status`; additionally show correct master `Entity ID`, adjacent `Legal Name`, matching basis, and evidence in relevant results/exports.
- A fuzzy result may show e.g. `Name similarity: 84.2%`, meaning **text similarity only**. An exact domain/LinkedIn result should show `Exact domain match`/`Exact LinkedIn match`; **do not** label it `100% accuracy` or `100% duplicate probability`.
- `Status` is a **classification**, and any percentage must be a clearly named `match_evidence_score_percent` (nullable pending scoring-method validation). Where the stakeholder insists on a percentage literally inside Status, use `Status + (Name similarity xx%)` for eligible fuzzy candidates and `Status + (Exact identifier match; score not calibrated)` for exact candidates until a documented evidence-score mapping is approved. This is an explicit **UI contract gap**, not permission to fabricate numbers.
- Independently report measured `precision`, `recall`, `F1`, and candidate recall on held-out labeled tests; do not infer production accuracy from synthetic results or a single fuzzy score.

### 3.5 Output grain / repetition contract

- **Uploaded-company outcomes:** exactly one row per `(run_id, upload_row_id)`; include `candidate_count`, strongest classification, and review/verification state. Handles inputs with no matches.
- **Master-company summary:** exactly one row per `(run_id, entity_id)`; include master Entity ID and original Legal Name, best evidence/status and number of uploaded rows that matched. This prevents repeat company rows.
- **Candidate details:** exactly one row per `(run_id, upload_row_id, entity_id)`; retain ALL distinct relationships. This intentionally repeats a master company across *different uploaded-company pairs*, not accidental duplicate pairs.
- Do not collapse different master Entity IDs solely because names/domains match; doing so could erase distinct legal entities. Do not infer a transitive A=B=C duplicate group without evidence for each relationship.

### 3.6 Client-complaint traceability and objective acceptance checks

| Acceptance ID | Original issue | Required observable behavior | Test / proof |
|---|---|---|---|
| AC-01 | Tool hangs / is slow | Upload and matching run complete without freezing UI; no external API required for core result | End-to-end runtime and p50/p95 benchmarks against 10 x 10,000 baseline; report observed timings, not invented SLA. |
| AC-02 | Trimark look-alikes missed | Related-name discovery can surface Trimark variants, while petroleum comparison is not auto-confirmed duplicate | Positive retrieval and hard-negative test cases; confirm visibility policy with owner. |
| AC-03 | `IMPORT_BATCH` exported instead of Entity ID | Every export containing master matches uses actual `entities.entity_id` | Referential-integrity and export assertion on fixed known seed IDs. |
| AC-04 | Legal Name missing beside Entity ID | Every relevant export has exact `entities.legal_name` beside correct `entity_id` | Round-trip checks for ID/name correspondence, including null Legal Names. |
| AC-05 | Potential Duplicate download repeats companies | Company-level download is unique at its declared grain; details preserve unique pairs | Uniqueness assertions per run, plus multi-match test. |
| AC-06 | URL vs web domain unclear | Website matching uses validated, public-suffix-aware normalized **registered domain**, not full URL | `https://www.example.com/a` and `example.com` match; unrelated `example.net` does not. |
| AC-07 | Confirm accuracy percentage | Publish measured precision/recall/F1 on labeled holdout plus sample size/conditions | Reproducible evaluation report; explicitly mark synthetic-only conclusions. |
| AC-08 | Manager's core matching logic | Canonical LinkedIn/domain matching; legal-name fuzzy fallback at >=80% under provisional eligibility semantics | Rule-by-rule tests covering BR-01–BR-15 and threshold boundary. |
| AC-09 | Manager's required columns/status | Company Name, Website Domain, LinkedIn, Status present; percentages honestly labeled | API/UI/export schema tests; unresolved Status-percent approval tracked. |
| AC-10 | Review safety | Candidate decisions never update/merge/delete master companies | DB snapshot comparison before/after review; review audit test. |

### 3.7 Approval / implementation gates

- **May implement now for local demo:** BR-01–BR-15 using DEC-01–DEC-03 provisional assumptions, normalized identifier matching, exact Entity ID preservation, all unique candidate pairs, non-destructive human reviews, explicit evidence labels.
- **Do not claim client approval or production readiness:** fuzzy eligibility semantics, name-field expansion, designated company-level export grain, status percentage semantics, related-name visibility, production accuracy/SLA.
- **Never implement silently:** automatic company merge, LLM-decided irreversible actions, fuzzy overriding a conflicting populated identifier, score presented as verified probability, or blind transitive company merging.

## 4. Name and identifier normalization

- Preserve raw values as supplied. Store normalized values in distinct columns or computed indexable fields.
- Company and legal names: Unicode NFKC, casefold, normalize whitespace and punctuation; remove whole-token legal suffixes with care; **retain meaningful words** (`Property`, `Petroleum`, `Group`, `Holdings`). Do not assume `Properties` and `Property` are identical.
- Domains: parse safely with a temporary scheme for bare values; validate hostname; use public-suffix-list-aware registered-domain extraction (e.g. `tldextract`), avoiding a live PSL network dependency at runtime; reject social platforms / generic hosting as strong identity signals when they represent shared hosting or profile links rather than company-owned domains. Carefully review subdomain-specific tenant products before collapsing to registered domain.
- LinkedIn: only `linkedin.com/company/<company-slug-or-id>`; canonicalize scheme, hostname, slug, trailing slash and tracking parameters; reject `linkedin.com/in/...`, lookalike hosts (`linkedin.com.evil.test`), blank/invalid URLs.
- `NULL`, `N/A`, empty, whitespace are missing; invalid populated input remains auditable and does not create an exact match.
- Never use substring website matching; compare parsed canonical identifiers.

## 5. Candidate retrieval and matching engine

### Baseline (10 x 10,000)

1. Validate CSV and assign each input an immutable `upload_row_id` and source row number.
2. Read/normalize master once per run (or read pre-normalized columns).
3. Index master candidates by normalized domain and LinkedIn; retrieve the **union** of their hits.
4. For master rows with both identifiers unavailable, evaluate fuzzy Legal Name matching using RapidFuzz `fuzz.ratio` with threshold 80, initially using an exhaustive scan of the small blank-identifier subset to guarantee baseline recall.
5. Add optional related-name discovery **in a separate result category**, never as a way to override mandatory identifier conflict rules.
6. Deduplicate by `(upload_row_id, entity_id)`; sort by evidence strength and stable entity ID; return all candidates.

### Optimized v2 (larger scales)

- Precompute normalized and indexed columns (`normalized_domain`, `normalized_linkedin`, `normalized_legal_name`).
- Multi-pass blocking on n-grams/token inverted index; optional first-three-character and phonetic blocks as auxiliary retrieval only.
- Union candidate sets from different blocks; cap overbroad generic tokens, with a documented fallback; periodically measure *candidate recall* against exhaustive ground truth.
- Never claim scalability merely because blocking was introduced: record p50/p95 latency, peak memory and candidate recall at each tested size.

## 6. Scores, evidence and truthfulness

- For exact URL/domain evidence, show `Exact match` and matched fields. A made-up `100% confidence` must NOT be displayed as calibrated duplicate probability.
- For fuzzy fallback, show true RapidFuzz string similarity percentage. Label explicitly **Name similarity**, not confidence or measured accuracy.
- `match_evidence_score_percent` is an **optional non-UI** field and must remain null until a defensible, approved scoring policy is evaluated on labeled data. If UI contract insists on a single number, use a clearly labeled *heuristic match-evidence score* and document its mapping; do not call it probability.
- All rows include evidence, conflicts, decision reason, source record, candidate record and optional external-source references.
- Measure precision, recall, F1 and candidate-generation recall on **held-out labeled synthetic groups**. Split by source entity/group, not random rows, to prevent duplicate-group leakage. Synthetic metrics must not be presented as production accuracy.

## 7. Optional external enrichment / LLM v3

**Approved Group 4 design:** See Appendix C for the single authoritative verification, evidence, job and cost-control contract. `AI_VERIFICATION_ENABLED=false` by default; AI is optional and removable without affecting the core application. This section is a summary only.

- Invoke only for ambiguous, human-review-worthy candidate pairs AND only with an explicitly enabled feature flag; do not add latency to normal exact/fuzzy matching.
- Resolve legal identity using reliable web evidence (official site, registry identifier, location, LinkedIn company profile, parent/subsidiary relationships). Search snippets are leads, not ground truth.
- Limit requests, cache with TTL, track costs and provider failures, respect website terms and data privacy policies; provide timeout/retry/circuit breaker. Cache must not overwrite original master records.
- Request structured LLM output: `classification`, `supporting_evidence`, `conflicting_evidence`, `reason`, `source_urls`, `needs_human_review`; reject uncited assertions. LLM percentages are not calibrated probabilities. Never auto-merge.
- **Unresolved feasibility:** select an actively supported search provider and verify licensing/API pricing before integration. Do not assume the originally suggested Bing/Azure integration remains available.

## 8. Data model and persistence — authoritative Group 5 contract

See **Appendix D (Group 5)** for canonical tables, constraints, indexes, run snapshots, API endpoints and idempotency. Use one SQLite database for the initial 10,000-record local demo, with **exactly 200 intentional duplicate groups**. Original `entities.entity_id` and its matching `legal_name` are authoritative. The backend must not automatically edit master entities. SQLAlchemy/Alembic and FastAPI are proposed implementation technologies, not already-running code.

## 9. REST API — authoritative Group 5 contract

See **Appendix D.5** for exact routes, schemas, error semantics, pagination, idempotency and export types. The frontend must consume these backend endpoints and never reimplement duplicate matching. Optional AI routes and workers must not be required when `AI_VERIFICATION_ENABLED=false`.

## 10. Frontend — approved Group 6 contract

**Exactly three main pages:** (1) **Dashboard & Upload**, (2) **Matching Results & Reviews**, (3) **Reports & Exports**. Approved **Matching Results Dashboard Interface** screenshot defines the visual reference (navy navigation, teal accents, light background, summary cards, filters, results grid, review actions). See **Appendix E (Group 6)** for page responsibilities and acceptance criteria. AI is a removable panel within candidate details, not a separate page.

## 11. Export contract — authoritative Group 6 requirements, Group 5 backend owner

Three **views from one export service**, not three export engines: (a) uploaded-company summary, unique `(run_id, upload_row_id)`; (b) master-company summary, unique `(run_id, entity_id)`; (c) detailed candidate pairs, unique `(run_id, upload_row_id, entity_id)`. Always display and export the correct `entities.entity_id` and adjacent `entities.legal_name`; never substitute `IMPORT_BATCH`. Distinct master Entity IDs may share names/domains and must not be collapsed. No-match incoming rows remain accounted for. The client's preferred “Potential Duplicate” export grain remains an owner approval item **DEC-03**. Refer to Appendix E for fields, filters and escaping rules.

## 12. Synthetic data and evaluation plan

- Fixed random seed; 10,000 master companies, 10 example uploaded rows, exactly 200 intentional duplicate groups; reserved `.example` domains and synthetic LinkedIn slugs.
- Cases: identical identifiers/different names; only domain match; only LinkedIn match; domain match/LinkedIn conflict; LinkedIn match/domain conflict; both master identifiers missing/name >=80; both missing/name <80; only one identifier populated; missing CSV identifiers; malformed URL; look-alike different industries (`Trimark Property` vs `Trimark Petroleum`); multiple matched entity IDs; parent/subsidiary sharing domain; no usable names.
- Ground-truth pair/group labels stored independently; no leakage into inference.
- Benchmark baseline exhaustive vs optimized blocking using identical seeds and held-out cases. Report precision, recall, F1, candidate recall, p50/p95 runtime, memory, export correctness, review persistence. Record exact dataset configuration, environment and version.
- Synthetic scoring is a controlled experiment, NOT proof of production accuracy.

## 13. Security and operational requirements — see Appendix F (Group 7)

Upload size/type/encoding limits, path traversal protection, SQL parameterization, output encoding, formula-injection protection, pagination, request size/timeout controls, safe logging (no secrets), no source record mutations, review audit trail, idempotent compare runs, API response validation, graceful DB/API failures, minimum necessary data retention. Local single-user demo can omit full authentication; multi-user production requires authentication and authorization before exposing reviews or data.

## 14. Testing and acceptance criteria — see Appendix F (Group 7)

- Normalization unit tests cover URL lookalikes, public suffix parsing, Unicode names, missing values and malformed inputs.
- Matching tests cover BR-01 through BR-15, especially conflict precedence, SQL-side blank-identifier rule, exactly-at-80 threshold, no blank-to-blank evidence, no false certainty, multiple candidates.
- Data tests verify deterministic repeatability, exactly 200 intentional duplicate groups, ground-truth isolation and negative controls.
- API integration tests cover upload, validation errors, compare, paging/filtering, persistent reviews and exports.
- Browser E2E tests cover upload → compare → inspect → review → export; verify original Entity ID and adjacent Legal Name, no duplicate company-summary records.
- Reliability tests cover API timeouts/LLM unavailability, malformed files, database disconnect, repeated submissions and CSV injection.
- Performance benchmarks must report actual observed runtime. Proposed initial targets (not achieved): precision >=95%, recall >=90%, candidate recall >=99%, correct IDs/legal names 100%, company-summary repeated IDs 0. Prioritize correctness before arbitrary latency claims.

## 15. Delivery sequence and milestones — see Appendix G (Group 8)

**M1 — Business rules / data contract:** Resolve approvals; finalize rules and export grain.

**M2 — Seed / baseline:** Create synthetic dataset, schema, normalization, exact match, mandatory fuzzy fallback and unit tests. Measure exhaustive baseline.

**M3 — Scalable retrieval:** Add indexed fields and multi-pass blocking; compare against M2; retain recall.

**M4 — Application:** Build APIs, review persistence, CSV export and responsive UI; E2E tests.

**M5 — Optional intelligence:** Implement feature-flagged external enrichment and LLM evidence review if benchmark demonstrates benefit and provider approval is available.

**M6 — Evaluation/demonstration:** Publish reproducible metrics, limitations, setup guide, automated test report and end-to-end demo.

## 16. Definition of done

- [ ] Business rule ambiguities and export grain approved.
- [ ] Source-to-target traceability of requirements and tests.
- [ ] Synthetic master and held-out ground truth created reproducibly.
- [ ] All mandatory matching rules and conflicts correctly applied.
- [ ] All candidate matches preserved without repeated candidate pairs.
- [ ] Exact source Entity ID and Legal Name in every relevant export.
- [ ] Review decisions persisted and audited; originals never changed.
- [ ] Functional, E2E, security and performance tests pass with recorded results.
- [ ] AI optional, isolated and resilient; unsupported verification claims prevented.
- [ ] Documentation, runnable demo and known limitations delivered.

## 17. Non-goals and known risks

- No automatic company merging, external registry write-back or identity certification.
- Similar names and shared corporate domains do not by themselves establish one legal entity.
- Candidate blocking can reduce recall; measured exhaustive comparison required.
- LLM output and web search snippets may be incorrect; human review stays authoritative.
- Real company data has not been supplied; production precision/recall remain unknown.

---

## Appendix A — Group 2: Dataset & Data Processing (final engineering specification)

**Design status:** Final engineering specification for the local demonstration. Implementation and automated tests remain pending. This appendix is the **authoritative detailed data contract** for Group 2; Sections 4 and 12 above remain concise summaries, not separate implementations. Business-owner approvals listed in DEC-01 through DEC-03 remain open.

### A.1 Objective and scope

Generate realistic synthetic company records; maintain independent duplicate ground truth; validate incoming CSV; normalize company names, legal names, website domains and LinkedIn company URLs; preserve all original inputs and actual Entity IDs; and supply a single consistent data contract to exact matching, candidate blocking, fuzzy matching, and optional evidence review. **One centralized validation/normalization implementation** must serve all consumers.

### A.2 Component 1 — Synthetic company dataset

| Property | Requirement |
|---|---|
| Initial master size | Exactly **10,000** synthetic rows |
| Storage | SQLite for local demo |
| Primary key | `entity_id` (authoritative database ID) |
| Duplicate coverage | **exactly 200 intentional duplicate groups** |
| Reproducibility | Fixed, configurable random seed; same configuration yields identical data |
| Names, URLs | Synthetic business names, reserved example domains, synthetic LinkedIn slugs |
| Reset behavior | Never silently overwrite a database; explicit reset required |
| Truth labels | Stored separately and not exposed to the matching engine |

**Master entity fields:** `entity_id INTEGER`, `company_name TEXT`, `legal_name TEXT`, `web_domain TEXT`, `linkedin_url TEXT`, `created_at TEXT`. Original values are retained; normalized/indexable fields may be maintained in separate columns or tables by the single normalization service. `IMPORT_BATCH` is never substituted for `entity_id`.

**Required controlled scenarios (DS-01–DS-20):** exact names; legal suffix variants; casing changes; typos; word reordering; website URL variants; LinkedIn URL variants; both identifiers equal; domain match/LinkedIn conflict; LinkedIn match/domain conflict; both identifiers absent; website-only; LinkedIn-only; similar-name hard negatives; shared corporate domains; parent/subsidiary; Trimark-style look-alikes across industries; multiple rows representing one identity; malformed URLs; unrelated negative controls. Seed them deliberately, not by chance.

### A.3 Component 2 — Ground-truth data

Ground truth records which synthetic records truly represent the **same legal entity**, independent of strings or matcher predictions.

| Field | Meaning |
|---|---|
| `entity_id_a`, `entity_id_b` | Canonically ordered master-record IDs (`a < b`) |
| `is_duplicate` | Ground-truth boolean, not derived from fuzzy score |
| `relationship_type` | `same_entity`, `related_company`, `unrelated` |
| `scenario_id` | Controlled scenario |
| `label_source` | Synthetic generator |
| `dataset_partition` | Development, validation, or test |

Rules: one stable hidden **underlying-entity identity** defines positive labels; parents/subsidiaries and shared-domain organizations are not automatically positive; hard negatives must include similarly named unrelated businesses; labels remain inaccessible to inference. Partition by underlying identity to prevent train/test leakage. Generate **uploaded-row-to-master-entity labels** as well as master-to-master cases, since upload-to-master is the real workflow. Store canonical pairs only once.

Illustrative labeled cases: `(1001,1002) = same_entity/true`; `(1001,1004) = similar-name-unrelated/false`. These are examples, not findings from live data.

### A.4 Component 3 — CSV input validation

Initial user workflow: upload about 10 company records, without hardcoding exactly 10 as a constraint. Supported headers: `company_name`, `legal_name`, `web_domain`, `linkedin_url`. At least one of `company_name` or `legal_name` must be usable per accepted row; identifiers are optional. Keep original physical CSV row number and a unique `(run_id, upload_record_id)` identity.

| ID | Rule |
|---|---|
| CSV-01 | Accept `.csv` format only; validate content, not extension alone |
| CSV-02 | Initial maximum file size **5 MB**, configurable |
| CSV-03 | Support UTF-8 and UTF-8 BOM |
| CSV-04 | Validate/normalize known headers; report missing/ambiguous headers |
| CSV-05 | Reject/flag rows where both name fields are unusable |
| CSV-06 | Blank website allowed |
| CSV-07 | Blank LinkedIn allowed |
| CSV-08 | Invalid website retained raw but marked unusable |
| CSV-09 | Invalid LinkedIn retained raw but marked unusable |
| CSV-10 | Empty rows skipped and counted |
| CSV-11 | Repeated uploaded content identified; source row identities preserved |
| CSV-12 | Whitespace normalized in derived fields only |
| CSV-13 | Defined null-like placeholders converted to missing derived values |
| CSV-14 | Malformed CSV produces understandable validation errors |
| CSV-15 | All CSV fields are untrusted; guard rendering and spreadsheet-formula export |
| CSV-16 | Preserve original CSV row number and stable internal uploaded-record ID |
| CSV-17 | Never silently drop valid rows |
| CSV-18 | Configurable row limits and resource protections |

An identical uploaded record may reuse the **computation**, not the output identity: distinct upload rows remain separately traceable. Return counts for total, accepted, rejected, empty skipped and invalid identifiers, plus structured per-row errors. Never fabricate similarity for invalid input.

### A.5 Component 4 — Single normalization service

**General:** use one reusable `normalization_service` for ingestion, master-record preparation, matching, blocking and (when enabled) evidence preparation. Preserve raw values and expose normalized values separately; normalization must be deterministic/idempotent.

**Company/legal names:** Unicode normalization (NFKC), casefold, trim/collapse spaces, standardize punctuation and remove configured whole-token **legal suffixes** when suffix position is appropriate. Preserve semantic business words: `Property`, `Petroleum`, `Group`, `Holdings`, `Management`, `Services`, `Solutions`, `Technologies`. Keep an additional lightly normalized variant for explanation/debugging. Examples: `Trimark Property Group LLC` → `trimark property group`; `ABC Technologies Ltd.` → `abc technologies`. Do not conflate `Property` and `Properties` by default.

**Domains:** safely parse bare domains and full URLs; lowercase hostname, remove ordinary `www.` and trailing dots, ignore scheme/path/query/fragment for **registered-domain matching**, use a Public Suffix List-aware extractor, and retain hostname plus registered domain. Invalid values are unusable. Handle IPs, public suffixes, generic hosting, shared platforms and tenant subdomains deliberately; a normalized domain does **not** prove website ownership or availability. Examples: `https://www.example.com/about` and `EXAMPLE.COM` → `example.com`.

**LinkedIn:** parse URLs with exact recognized LinkedIn host validation; accept `/company/<slug-or-id>` only; reject personal profiles and unrelated paths; strip scheme, `www`, tracking queries, fragments and trailing slash; normalize canonical company path while retaining raw input. Example: `https://www.linkedin.com/company/example/?trk=123` → `linkedin.com/company/example`. Reject lookalike hosts that merely contain `linkedin.com` as text.

### A.6 Shared processed-data output contract

This contract is **data handed to matching/reporting services**, not another duplicate-matching or CSV-export service.

| Internal field | Meaning |
|---|---|
| `upload_record_id` | Unique identifier for incoming row within run |
| `csv_row_number` | Original physical CSV row number |
| `company_name_original`, `legal_name_original` | Source name values |
| `web_domain_original`, `linkedin_url_original` | Source identifier values |
| `company_name_normalized`, `legal_name_normalized` | Derived matching names |
| `web_domain_normalized` | Valid registered domain, else null |
| `linkedin_url_normalized` | Valid canonical LinkedIn company URL, else null |
| `website_validation_status`, `linkedin_validation_status` | `valid`, `missing`, `invalid` |
| `record_validation_status` | `accepted`, `rejected` |
| `validation_errors` | Structured row diagnostics |

Compatible normalized values must exist for master records, retaining their authoritative `entity_id` and associated original `legal_name`.

**Downstream detailed result columns (owned by Groups 3 and 6):** Uploaded Company; Uploaded Legal Name; Matched Entity ID; Matched Legal Name; Matched Company Name; Website Domain; LinkedIn; Match Method; **Name Similarity (%)**; **Match Status**; Review Decision. `Name Similarity (%)` replaces ambiguous `Match Score (%)`, is populated **only if fuzzy similarity was actually evaluated**, and is otherwise `N/A`/null, not zero or fabricated 100%. Exact identifier matches show explicit evidence labels. Status percentages as requested by manager are still under Group 1 business approval and must not masquerade as calibrated probability.

**Exports (owned by Group 6):** (a) company-level summary with one row at a **declared** grain (incoming row or master Entity ID, per DEC-03); (b) detailed report with one row per distinct `(run_id, upload_record_id, entity_id)` candidate pair. Retain one-to-many relationships; never conflate distinct Entity IDs sharing a name/domain. The ingestion layer does not separately implement exports.

### A.7 Data integrity / duplicate-prevention requirements

| Rule | Invariant |
|---|---|
| DI-01 | Never mutate original source values during normalization |
| DI-02 | Never substitute import-batch information for actual Entity ID |
| DI-03 | Keep `entity_id` associated with its correct original `legal_name` |
| DI-04 | Preserve every incoming CSV row's source identity |
| DI-05 | A method match is **evidence**, not an additional row for the same candidate pair |
| DI-06 | Website/LinkedIn/fuzzy evidence for a candidate pair combines into one results object |
| DI-07 | Preserve valid one-to-many candidate relationships |
| DI-08 | Never automatically merge, update or delete source company entities |
| DI-09 | Ground truth cannot leak into inference features |
| DI-10 | Repeated normalization yields stable output |

**Ownership boundary:** Group 2 defines identifiers and fields; Group 3 owns **one candidate-pair deduplication and classification engine**; Group 6 owns **one reporting/export implementation**. Do not create duplicates of these systems.

### A.8 Performance and acceptance

Normalize master entities when initially prepared or changed, not repeatedly for every comparison; reuse normalized values across matcher methods; batch incoming rows; avoid network access in normalization; allow indexed candidate retrieval; capture processing timing. Group 7 owns measured performance benchmarks and thresholds.

**Group 2 design acceptance conditions:** reproducible 10,000-row generator specification; exactly 200 labeled duplicate groups; hard negatives; unique Entity IDs; source-row tracking; valid/invalid/missing identifier handling; consistent normalization; preserved originals; stable per-pair identity; separated evaluation labels and partitions; automated tests specified for generation, CSV parsing and URL/name normalization. **These are design requirements, not claims that tests have passed.**

**Approval boundary:** This appendix is the finalized Group 2 engineering design. Group 1 DEC-01/02/03 and the client's percentage/status display remain pending owner approval. Implementation, seed generation, test execution and measured quality remain pending.

## Appendix B — Group 3: Matching & Scoring Engine (final engineering specification)

**Design status:** Approved engineering design for the local demonstration. **Implementation and measured results are pending.** This appendix is the authoritative detailed matching-engine contract. Sections 3, 5 and 6 above are summaries of this contract, **not instructions to build another matcher**. Outstanding business-owner decisions DEC-01, DEC-02 and DEC-03 remain open.

### B.1 Scope and ownership — eight coordinated components

The matching pipeline must identify all eligible exact website/LinkedIn hits, discover eligible fuzzy Legal Name candidates, expose evidence and conflicts, classify candidates, deduplicate each candidate pair, group results for presentation without automatically merging legal identities, and support measurable algorithm comparison. The matching engine never updates or deletes source entities.

| Component | Single responsibility |
|---|---|
| Website domain matching | Compare validated registered domains |
| LinkedIn matching | Compare validated canonical company-page identifiers |
| Fuzzy Legal Name matching | Apply eligibility rule and configured similarity threshold |
| Candidate generation | Union indexed identifier hits and name-block candidates |
| Scoring and classification | Produce evidence, similarity if computed, and one status |
| Candidate-pair deduplication | Aggregate evidence once per unique uploaded-to-master pair |
| Duplicate grouping | Provide non-destructive uploaded-company and master-entity group views |
| Algorithm benchmarking | Compare correctness, candidate recall, runtime and memory using held-out labels |

**One pipeline:** normalization is owned exclusively by Group 2; web/LLM enrichment belongs to Group 4; APIs and persistence to Group 5; dashboard/export rendering to Group 6; final benchmarking and test execution to Group 7. These responsibilities must not be reimplemented in parallel.

### B.2 Authoritative matching sequence

1. Accept validated and normalized uploaded rows and indexed normalized master records from Group 2.
2. Retrieve candidates through **all applicable exact website and LinkedIn indexes** plus name-blocking methods. Exact identifier hits must not depend on name similarity.
3. Union by `entity_id` to create **one candidate per master record per uploaded row**, retaining all retrieval reasons.
4. Compare the two identifiers independently, each producing `MATCH`, `CONFLICT` or `UNAVAILABLE`.
5. Evaluate mandatory **Legal Name-to-Legal Name** fuzzy fallback **only** when the master record's two normalized identifiers are unavailable (provisional DEC-01), and the compared Legal Names are usable.
6. Apply the Group 1 business-rule priority to select exactly one primary classification for the pair.
7. Record supporting and conflicting field evidence and a deterministic human-readable reason; never invent evidence or a calibrated confidence probability.
8. Aggregate any additional retrieval/matching methods into the **same** candidate-pair result.
9. Keep similar-name/related-entity *leads* in a distinct review lane. Discovery does not override mandatory rules or classify as a duplicate.
10. Return all qualifying candidates (not merely the first), plus an explicit per-upload-row outcome for no matches or insufficient data; group non-destructively for review/export.

### B.3 Website matching

Compare **normalized registered domains**, not raw URL strings. Reuse only the Group 2 `normalization_service`. States are:

| State | Condition |
|---|---|
| `MATCH` | Both valid normalized registered domains present and identical |
| `CONFLICT` | Both valid domains present and different |
| `UNAVAILABLE` | At least one domain missing or unusable |

Blank-vs-blank is `UNAVAILABLE`, never `MATCH`. E.g. `https://www.abc.example/about` and `abc.example` match once normalized. Shared corporate/hosting domains are evidence, not proof of a shared legal entity; preserve original URLs, hostname context and flags for manual assessment. An indexed domain hit is never lost to name-block filtering.

### B.4 LinkedIn matching

Compare **canonical LinkedIn company-page identifiers** produced by Group 2; never compare just the LinkedIn hostname. Reject personal profiles, malformed paths and look-alike hostnames upstream. Return `MATCH` for the same valid company-page identifier, `CONFLICT` when two comparable valid identifiers differ, and `UNAVAILABLE` when either is missing/invalid. Preserve original values and reasons. A shared company page does not by itself constitute legally confirmed duplication.

### B.5 Mandatory fuzzy matching — and separate related-name discovery

- **Provisional DEC-01:** eligibility is decided on the **master** record: both normalized website and LinkedIn identifiers are missing/unusable. Incoming identifiers may be present. Keep this assumption flagged until owner sign-off.
- **Provisional DEC-02:** mandatory fuzzy comparison is **normalized uploaded Legal Name versus normalized master Legal Name**. The four combinations in the teammate reference can be supplementary discovery evidence only until approved; they must not silently change mandatory outcomes.
- **Baseline algorithm:** `rapidfuzz.fuzz.ratio`, yielding an actual string similarity from `0` to `100`.
- **Configured threshold:** default `80`, allowed UI range `50–100`; exactly `80` qualifies. Apply the threshold to the **actual unrounded score**, then round only for display.
- **Result:** eligible score `>= threshold` → `Potential Duplicate`; below threshold → Not a Match under fuzzy rule. If either required Legal Name unusable → `Insufficient Data` rather than a fabricated score. A score of `100` for names does not confirm legal identity.
- **Display-only similarity bands:** 80–<90 moderate; 90–<95 high; 95–100 very high. These are **not** separate classifications or probabilities.
- **Name normalization:** use Group 2 only; do not strip meaningful `Property`, `Petroleum`, `Group`, `Management`, `Holdings`, etc.

**Trimark-type discovery:** A separate related-name lead mechanism can find similar legal or display names even when identifiers are present/different. Use informative tokens, name prefixes, n-grams and other independently benchmarked discovery heuristics. A lead is an investigation prompt, **not** a mandatory fuzzy hit or `Potential Duplicate` without rule qualification. Keep it visually and analytically separate to avoid false positives and satisfy the complaint about missed look-alikes.

### B.6 Multi-pass candidate generation and performance

| Retrieval pass | Purpose | Rule |
|---|---|---|
| Indexed normalized domain | Strong identifier candidates | Always include all domain hits |
| Indexed normalized LinkedIn | Strong identifier candidates | Always include all LinkedIn hits |
| Exact normalized names | Obvious name variants | Candidate only, not final match |
| Prefix and distinctive-token blocks | Related names | Union, do not replace exact hits |
| Character n-grams | Typos and spelling variations | Benchmark recall and candidate volume |
| Optional phonetic blocking | Selected variants | Enable only with validated benefit |

At the initial scale (~10 CSV rows × 10,000 master rows), an exhaustive eligible-comparison reference implementation is feasible and is required to establish **candidate recall** and correctness. For larger datasets, precompute normalized master fields, use indexed lookup and multi-pass blocks, cache reusable work and minimize scans. Union candidates rather than emitting separate rows for separate passes. The optimized engine must be compared against exhaustive eligible matching; document missed eligible candidates and provide an explicit fallback for ineffective blocks. Group 7 owns measured latency/memory targets.

### B.7 Classification and evidence priority

Use Group 1 as the **single authoritative** classification matrix:

| Website | LinkedIn | Additional condition | Primary result |
|---|---|---|---|
| `MATCH` | `MATCH` | — | High-confidence Duplicate Candidate |
| `MATCH` | `UNAVAILABLE` | — | High-confidence Duplicate Candidate |
| `UNAVAILABLE` | `MATCH` | — | High-confidence Duplicate Candidate |
| `MATCH` | `CONFLICT` | — | Needs Review |
| `CONFLICT` | `MATCH` | — | Needs Review |
| `CONFLICT` | `CONFLICT` | — | Not a Match under identifier rules; related-name lead separately possible |
| `UNAVAILABLE` | `UNAVAILABLE` | Master both identifiers unavailable + legal name similarity >= threshold | Potential Duplicate |
| `UNAVAILABLE` | `UNAVAILABLE` | Master both unavailable + similarity below threshold | Not a Match |
| `UNAVAILABLE` | `UNAVAILABLE` | Master both unavailable + unusable names | Insufficient Data |
| `UNAVAILABLE` | `UNAVAILABLE` | Master has populated identifiers, but not comparable to incoming | Insufficient Comparable Identifiers (no eligible fuzzy fallback) |

**Precedence:** one matching identifier plus a conflicting populated identifier → `Needs Review` before `High-confidence`. Unconflicted exact matching precedes eligible fuzzy fallback. Missing fields are not evidence of equality. If no qualifying candidate is returned, give the uploaded company an explicit `No Match`/`Insufficient Data` outcome without inventing a matched Entity ID. Preserve all matched/conflicting field states and a deterministic explanation.

### B.8 Scoring labels and truthfulness

Store `name_similarity_percent` **only when a fuzzy comparison actually runs**; otherwise `null`/`N/A`. The client-facing column is **`Name Similarity (%)`**, replacing ambiguous `Match Score (%)`. `Match Status` is separate. Exact website/LinkedIn equality is expressed through `MATCH` evidence, **not a made-up 100% duplicate probability**. Precision/recall/F1 are aggregate evaluation metrics, not individual match percentages. The original manager request for a percentage within `Status` remains an explicit business-owner approval item; do not silently claim it is fulfilled by an uncalibrated score.

### B.9 Candidate-pair uniqueness and evidence aggregation

A candidate-pair identity is **`(run_id, upload_record_id, entity_id)`** (where `upload_record_id` is scoped to the run); the persisted result must have one unique constraint for that key. Multiple hits from website, LinkedIn, fuzzy or blocking are **evidence on that single pair**, not separate result rows. Re-running with the same logical run must be idempotent; do not append duplicates. Distinct uploaded rows and distinct matched master Entity IDs remain independent, even if names are identical. Display methods together (e.g. `Website + LinkedIn`) and retain all matched/conflicting fields.

### B.10 Non-destructive grouping

**Uploaded-company view:** one uploaded row with a list of all distinct candidate master Entity IDs (including multiple genuine candidates). **Master-company summary:** one row per unique matched master Entity ID per run, while the detailed export preserves each distinct uploaded-to-master pair. DEC-03 must be approved to designate which summary is the client's `Potential Duplicate` export. **Never equate group connectedness with duplicate legal identity**: A↔B and B↔C evidence does not automatically prove A↔C. Parent and subsidiary identities remain separate unless verified. Human review is the only route to confirmed disposition.

### B.11 Algorithm comparison and selection

Baseline: RapidFuzz `fuzz.ratio`. Alternatives for a controlled benchmark: Levenshtein, Jaro-Winkler, token sort, token set, TF-IDF cosine, and character n-gram similarity. Compare each against **the same held-out Group 2 truth labels**, including hard negatives and the upload-to-master flow. Report precision, recall, F1, false positives/negatives, candidate recall, candidate reduction, memory and actual execution time. Alternative scores are **not numerically interchangeable**; revalidate the mandated 80% threshold if switching scorers. Promote an alternative only when measured business-rule compliance, recall, precision, performance and interpretability justify it. Optional AI/LLM evaluation belongs to Group 4.

### B.12 Result contract (illustrative, not measured output)

```json
{
  "run_id": "RUN-001",
  "upload_record_id": "CSV-001",
  "matched_entity_id": 1001,
  "uploaded_company_name": "Westbridge Property Group",
  "uploaded_legal_name": "Westbridge Property Group LLC",
  "matched_company_name": "Westbridge Properties",
  "matched_legal_name": "Westbridge Properties LLC",
  "match_methods": ["website", "linkedin"],
  "website_match_state": "MATCH",
  "linkedin_match_state": "MATCH",
  "name_similarity_percent": null,
  "match_status": "high_confidence_candidate",
  "matched_fields": ["web_domain", "linkedin_url"],
  "conflicting_fields": [],
  "reason": "Normalized registered domain and LinkedIn company identifier match.",
  "review_decision": null
}
```

Original master `entity_id` must always map to its correct `legal_name`. One authoritative API object per candidate pair; Group 5 owns endpoint transport and Group 6 renders/exports it rather than recomputing decisions.

### B.13 Logical module boundaries (final directory layout to Group 5)

| Logical module | Exclusive responsibility |
|---|---|
| `candidate_service` | Candidate ID union using indexes/name blocks |
| `matching_service` | Exact identifier and eligible fuzzy comparisons |
| `classification_service` | Apply Group 1 statuses and evidence priority |
| `matching_results_service` | Aggregate evidence and enforce pair uniqueness |
| `grouping_service` | Build non-destructive uploaded/master grouped views |
| `matching_evaluation` | Algorithm and blocking benchmarks |

These are logical responsibilities, **not** six independently deployed engines. There must be no second normalization, second classifier or second result deduplicator elsewhere in the application.

### B.14 Error handling and operational integrity

Reject invalid threshold configurations and malformed inputs with clear errors. Handle missing Legal Names and invalid URLs as absent evidence without crashes. Differentiate `No Match`, `Insufficient Data`, and technical failures; a database or engine error must **not** be silently converted to `No Match`. Preserve all qualifying unique candidates; never truncate without a documented and visible pagination/resource-control response. Make retries idempotent and retain original company records read-only.

### B.15 Group 3 acceptance criteria (design-defined; testing pending)

| ID | Criterion |
|---|---|
| G3-AC-01 | Valid normalized website-domain matches are found correctly |
| G3-AC-02 | Valid normalized LinkedIn company-page matches are found correctly |
| G3-AC-03 | Blank-to-blank identifiers never match |
| G3-AC-04 | Conflicting identifier values are detected |
| G3-AC-05 | Conflicting evidence takes precedence over unconflicted strong status |
| G3-AC-06 | Mandatory fuzzy fallback follows provisional DEC-01 |
| G3-AC-07 | Baseline RapidFuzz score uses a configurable default threshold of 80 |
| G3-AC-08 | Exactly 80 qualifies based on unrounded score |
| G3-AC-09 | Missing Legal Names do not produce fabricated similarity |
| G3-AC-10 | Related-name discovery does not override mandatory duplicate rules |
| G3-AC-11 | Exact identifier matches cannot be lost to name blocking |
| G3-AC-12 | Each run/upload/master candidate pair yields exactly one result |
| G3-AC-13 | All matching methods contribute to one evidence record |
| G3-AC-14 | Every qualifying master candidate is returned, not merely the first |
| G3-AC-15 | Actual master Entity IDs and associated Legal Names remain correct |
| G3-AC-16 | Grouping never automatically merges legal entities |
| G3-AC-17 | `Name Similarity (%)` and `Match Status` are separate |
| G3-AC-18 | Exact identifier matches are not given fake probability percentages |
| G3-AC-19 | Algorithm comparisons use separate, independently labeled test data |
| G3-AC-20 | Blocking candidate recall is checked against exhaustive eligible matching |
| G3-AC-21 | Repeated processing does not append duplicate candidate rows |
| G3-AC-22 | Insufficient evidence and technical errors are distinguished |
| G3-AC-23 | Precision, recall, F1 and runtime are measured and reported after implementation |
| G3-AC-24 | Core matching works with web search and LLM services disabled |

**Group 3 engineering design complete.** No implementation, benchmark or test is claimed complete. All Group 1 client-approval gates stay in force.

## Appendix C — Group 4: AI & External Verification (approved optional engineering design)

**Design status:** Approved as an **optional, removable** enhancement. No paid service has been configured or tested. Implementation, actual provider procurement, business authorization, and measured accuracy/cost remain pending. This appendix is the **authoritative detailed Group 4 contract**; Section 7 above is a summary, not permission to build a second verification service.

### C.1 Scope, separation and dependency contract

Group 4 owns four coordinated capabilities: **(1) selective external web search, (2) structured LLM evidence analysis, (3) evidence provenance and reuse, and (4) persistent background verification jobs.** The Group 3 engine remains authoritative for exact domain/LinkedIn comparisons, mandatory >=80% eligible Legal Name fuzzy matching, pair classification and candidate uniqueness. AI does not replace or recalculate Group 3 matching status. Group 5 owns shared persistence/APIs; Group 6 owns visualization/human decisions; Group 7 owns testing, security and measured cost/accuracy evaluation.

**Non-negotiable removability:** `AI_VERIFICATION_ENABLED=false` by default. When disabled, no search or LLM calls, workers, keys or paid dependencies are necessary to upload CSV, compare companies, review results or export. Disabling/removing Group 4 must not require changing core match logic or deleting required company/review data. External evidence and `ai_verification_status` are optional, separate fields. A failed AI job never changes a core result to `No Match`.

### C.2 Eligibility and routing (only after Group 3)

1. Return initial deterministic/fuzzy results immediately. Identify eligible **ambiguous, review-worthy** candidate pairs (e.g. an exact identifier match with a different populated other identifier; an eligible fuzzy potential duplicate lacking identity evidence; separately flagged related-name look-alikes). Group 1's provisional rules DEC-01/02/03 remain unchanged.
2. Exclude routine unconflicted exact matches, unequivocal negatives, no-evidence inputs and finalized human-reviewed decisions by default. Manual authorized re-verification may be offered.
3. For each eligible pair, check feature flag → role/permissions/consent → prior review → cache → usage limit and available reserved budget → queue. Failing eligibility/budget must return `skipped` or `budget_exceeded`, **not** hide the original candidate.
4. Cap initial candidate pairs per run at **20** (configurable). If over the cap, leave remaining items visible and pending manual review; never silently truncate the candidate list.

### C.3 External search contract

Use an approved, supported provider through **one replaceable `search_provider` adapter**. Do not use the retired original Bing Search API as a new implementation dependency. Brave Search and Tavily are possible evaluation candidates, not selected or commercially approved vendors. Provider availability, terms, permitted usage, pricing and jurisdiction must be verified before enabling live calls.

- Prefer queries using exact Legal Name plus known official identifiers; search for official websites, LinkedIn company profiles and company registrations only as evidence leads. Initial **maximum two queries per distinct company per verification run**, subject to budget. Deduplicate normalized queries and reuse source evidence across candidate pairs.
- Store search provider, query hash, source URL, title, short relevant extracted claim/snippet, retrieval timestamp, status, cache expiration and provider usage record. Do not assume a search snippet is an authoritative legal-company statement.
- Validate exact URL hostnames and safe HTTP(S) destinations; protect against server-side request forgery, redirects to private networks, malicious documents and disallowed scraping. Never collect or send unnecessary personal/confidential information.
- Failed, empty, invalid and blocked searches are explicit outcomes. No fabricated company identities or false matches.

### C.4 Evidence reliability and retention

Prioritize *verified* registry evidence for legal identity, then verified official company pages, official LinkedIn company pages, reputable registries/directories and contextual news. A source label alone does not prove accuracy. Capture supporting **and** contradicting evidence, provenance, retrieval date and cited source links. A shared corporate domain or profile may refer to distinct legal entities. Store evidence independently from master records, never overwrite original legal names or websites.

Initial configurable cache TTLs (not guarantees of accuracy): search response **7 days**, official website evidence **14 days**, directory evidence **14 days**, registry evidence **30 days**. An LLM conclusion may be reused only while normalized pair inputs, validated evidence snapshot, policy/prompt version and model identifier remain unchanged. Invalid/expired evidence triggers re-validation only within budget/permissions. Expiry and retention deletion are distinct policies; Group 7 establishes retention limits.

### C.5 LLM evidence analysis

The LLM is an **advisory analyst**, not a matching engine and not the ultimate reviewer. Send only necessary normalized/original company identifiers, Group 3 comparison evidence, validated external claims and their source references. Retrieved text is untrusted data; it must not instruct the assistant to ignore policies or run actions. Use one prompt/schema implementation, short outputs, bounded input length and strict response validation.

Allowed `relationship_type`: `same_legal_entity`, `related_separate_entities`, `unrelated`, `insufficient_evidence`. Allowed `verification_status`: `completed`, `needs_review`, `failed`, `skipped`. Required output fields: `relationship_type`, `verification_status`, `supporting_evidence[]`, `conflicting_evidence[]`, `source_references[]`, `reason`, `human_review_required`. Reject invented claims, unknown source references, model-format errors and unsupported confidence percentages. No AI result may auto-merge/delete/update master entities or mark a human decision confirmed.

**Three distinct states:** `match_status` (Group 3 authoritative rules), `ai_verification_status` / `ai_relationship_type` (Group 4 advisory), `review_decision` (Group 6 human action). Do not overwrite or conflate these.

### C.6 Background jobs and operational behavior

Initial local demo: one lightweight **persistent** bounded worker; do not add a distributed message bus until justified. Use immutable/run-scoped job identity and idempotency keys to prevent duplicate paid requests. Suggested states: `pending`, `running`, `completed`, `needs_review`, `failed`, `skipped`, `budget_exceeded`, `cancelled`. Include progress, retry count, reservation/actual spend, start/end timestamps and error category. Set timeouts, provider rate limits, maximum **three** concurrent jobs and at most **one** retry for transient failures. Recover interrupted jobs safely on restart; support cancellation where possible. Initial matching/result browsing never waits for jobs.

### C.7 Cost protection (initial development defaults; not forecast)

| Control | Proposed default / policy |
|---|---|
| AI feature flag | `AI_VERIFICATION_ENABLED=false` initially |
| Search queries | At most 2 per distinct company per verification run |
| LLM calls | At most 1 initial LLM analysis per candidate pair |
| Candidate verification cap | 20 candidate pairs per run |
| Background concurrency | 3 jobs maximum |
| Transient retry | At most 1, still charged against budget |
| Per-run spending cap | **USD 1** |
| Daily spending cap | **USD 5** |
| Caching | Enabled with configurable expirations |
| Budget enforcement | Atomic cost reservation **before** dispatch; reconcile actual reported usage afterward; no new paid work on exceeded budget |
| Pricing | Provider/model rates supplied through configuration; verify official current pricing before activation |
| Cost records | Distinguish estimated cost, reserved cost, provider-reported usage and actual billed cost (if known) |

Cost logging per job: `run_id`, `job_id`, provider/model ID, distinct requests, cache hits, input/output tokens (when supplied), estimated USD, reserved USD, reported USD, outcome and timestamps. Never imply calculated expense equals invoiced spend. A useful **illustrative only** scenario: 16 searches at an *assumed* $0.005/search plus 20 analyses of 1,500 input and 300 output tokens at *assumed* $0.75/$4.50 per million tokens gives **$0.1295 external API usage** for that run, excluding hosting, retries, extraction, storage and taxes. These are **assumptions, not an up-to-date provider quote or expected real workload**. Synthetic-data demo should use mock evidence and zero paid requests.

### C.8 Security, privacy and human override

Store provider keys server-side in environment/secrets; never in browser or source control. Use HTTPS, request quotas, access control, safe outbound allowlisting/SSRF checks, prompt-injection defenses, structured validation and content/response size limits. Obtain organization approval before sending real company records externally. Record who manually requested verification, what inputs/evidence were considered, and human final decision separately. AI cannot bypass mandatory business rules, reviewer decisions or the original Entity ID/Legal Name mapping.

### C.9 Evaluation and feature promotion

Evaluate Group 3 baseline, baseline + evidence, and baseline + evidence + LLM on **identical held-out labeled company pairs**, including same-entity, parent/subsidiary, look-alike hard negatives and insufficient-data cases. Report changes in precision/recall/F1, ambiguous-case resolution, unsupported-claim rate, human agreement, verification latency, requests, cache hit rate and **USD per resolved case**. Simulated web evidence suffices for deterministic development testing but does **not** establish real-world search accuracy. Enable paid production use only when evidence quality, measured benefit, provider terms, privacy approvals and cost envelope pass acceptance checks.

### C.10 Acceptance checks (design-defined; execution pending)

| ID | Criterion |
|---|---|
| G4-AC-01 | Core upload, matching, review and export work when optional AI is disabled or removed |
| G4-AC-02 | Only eligible review-worthy pairs trigger verification; no silent changes to Group 1/3 rules |
| G4-AC-03 | Cached valid evidence avoids duplicate paid requests; queries and jobs are idempotent |
| G4-AC-04 | Provider adapters are replaceable and supported/approved before live operation |
| G4-AC-05 | Every external claim preserves provenance, retrieval time, and conflicting evidence |
| G4-AC-06 | LLM schema and source references are validated; no invented claims or probabilities |
| G4-AC-07 | `match_status`, `ai_verification_status`, and `review_decision` remain independent |
| G4-AC-08 | Worker failure, timeout, cancellation and unavailable provider do not break results |
| G4-AC-09 | Per-run/daily caps are enforced before external requests, including in-flight reservations |
| G4-AC-10 | Search/token usage and estimated versus actual cost are separately reported |
| G4-AC-11 | Synthetic test runs can use mock evidence without paid external services |
| G4-AC-12 | Human decisions and original master entities cannot be overwritten by AI |
| G4-AC-13 | Security/privacy restrictions and approved provider terms are enforced |
| G4-AC-14 | The AI feature is enabled only after measurable evaluation of benefit and cost |

**Group 4 engineering design approved with optional/removable AI.** Implementation, test execution, live provider selection, operational pricing and business/production approval remain **pending**. Group 5 may add **optional** verification tables and endpoints, but must not introduce foreign-key or startup dependencies that break the AI-disabled core.


---

## Appendix D — Group 5: Database, Backend & System Architecture (approved engineering specification)

### D.1 Architecture, stack and boundaries

**Deployable architecture:** One modular monolith: React + TypeScript + Vite + Tailwind frontend; Python FastAPI backend; SQLite for demo; SQLAlchemy 2.x plus Alembic migrations; RapidFuzz, tldextract and Python `csv` for core matching. pytest for backend, Playwright for browser E2E. Use optional AI adapters and a persistent worker **only** if feature enabled. No required Redis, Celery, microservices, Kubernetes, paid AI account or PostgreSQL for the base demo. Versions must be pinned in lockfiles/requirements.

**Module responsibility:** `csv_service` (Group 2 input); `normalization_service` (Group 2 canonical fields); `candidate_service`, `matching_service`, `classification_service`, `results_service`, `grouping_service` (Group 3); optional `verification` adapter/worker (Group 4); database/routers/services for runs, reviews and **one** export service (Group 5 backend serving Group 6 contract). React components display server data only. No independent client-side score or duplicate classifier. Build simple modules before creating more abstraction.

### D.2 Schema and constraints — canonical source

| Table | Essential fields / invariant |
|---|---|
| `entities` | `entity_id INTEGER PRIMARY KEY`, `company_name`, `legal_name`, `web_domain`, `linkedin_url`, normalized company/legal/domain/LinkedIn fields, `normalization_version`, `created_at`; preserve original values |
| `import_runs` | `run_id UUID/ULID PK`, filename, safe content hash, fuzzy threshold, `rule_version`, `algorithm_version`, `normalization_version`, `master_snapshot_id` or immutable master-data fingerprint, run status, counts, started/completed timestamps; explicit `idempotency_key` per requested compare action |
| `import_rows` | `upload_record_id` stable key, `run_id FK`, physical `csv_row_number`, original + normalized fields, validation state/errors; unique `(run_id,csv_row_number)` |
| `match_candidates` | `candidate_id PK`, `(run_id,upload_record_id,candidate_entity_id)` UNIQUE and FKs, website/LinkedIn states, nullable `name_similarity_percent`, match methods, matched/conflicting evidence, `match_status`, rationale, optional verification state and timestamps |
| `duplicate_reviews` | append-only `review_id`, `candidate_id FK`, reviewer, prior/new decision, reason, `request_id` UNIQUE per client mutation, reviewed timestamp; never overwrite historical decisions |
| `verification_jobs` *(optional)* | job/pair identity, status, retry count, budget reservations, start/end times and errors; disabled system needs no worker |
| `verification_evidence` *(optional)* | source URL, provenance, retrieved/expires timestamps, evidence snapshot hash, job/candidate reference |
| `api_usage` *(optional)* | provider/model, request count, tokens, estimated/reserved/provider-reported cost, timestamp |

Ground truth remains in separate **evaluation-only** files/tables; no production API or inference query can read it to make matching decisions. Use normalized unique relational keys; do not add a second entity table merely for duplicated companies. Apply `PRAGMA foreign_keys=ON` per SQLite connection. Use schema migrations; never drop an existing DB silently.

**Indexes:** non-unique `entities(normalized_domain)` and `(normalized_linkedin)`, `entities(normalized_legal_name)`; `match_candidates(run_id,match_status)`, `(run_id,upload_record_id)`; `duplicate_reviews(candidate_id,reviewed_at)`; index run and review lookups. For name blocking at larger scales, benchmark a separate tokens/n-grams index rather than adding speculative indexes. Keep normalization version pinned so stored canonical forms are rebuilt safely after rule changes.

**Snapshot correctness:** Master rows are read-only during comparison. Store a master version or deterministic fingerprint with each run; if master data changes mid-run, use a consistent read snapshot or reject/retry rather than mix versions. Store threshold and rule versions per run so a saved result remains explainable. SQLite WAL can improve concurrent reads, but transaction and write-lock handling require tests.

### D.3 Integrity and repeatability

- Fetch master Entity ID and Legal Name from **the same** `entities` row by Entity ID; never map via company name or import batch label.
- Enforce one result record per `(run_id, upload_record_id, candidate_entity_id)` in SQLite, not via UI dedup alone. Collect match reasons first, then upsert one aggregated evidence record transactionally; allow distinct master candidates.
- Multiple source CSV rows retain distinct IDs even if identical text; cache reusable calculation without discarding source lineage.
- Same compare request + same run + idempotency key reuses existing job/results (or rejects simultaneous duplicate execution). Explicitly starting a **new run** with the same CSV is allowed.
- Interrupted/failed runs must never appear `completed`; keep accurate run state and recover safely. Review updates require a new append-only event, unless an idempotency key proves a retry of the same mutation.
- Use parameterized SQL/ORM bindings, safe migrations, bounded transactions and retries only for transient lock errors. No automatic master-record merge/update/delete.

### D.4 Configuration and optional AI

Suggested `.env.example` (no real secrets):

```dotenv
APP_ENV=development
DATABASE_URL=sqlite:///./database/company_duplicates.db
FUZZY_THRESHOLD=80
MATCHING_ALGORITHM=rapidfuzz_ratio
AI_VERIFICATION_ENABLED=false
SEARCH_PROVIDER=none
LLM_PROVIDER=none
MAX_UPLOAD_SIZE_MB=5
MAX_AI_CANDIDATES_PER_RUN=20
MAX_AI_COST_PER_RUN_USD=1
MAX_AI_DAILY_COST_USD=5
LOG_LEVEL=INFO
```

Validate config at startup and refuse unsupported thresholds/types. Secrets are server-side only. Production auth/config must not default to insecure demo mode. Disabled AI must not require network, credentials, job tables to be populated, provider packages or workers for core operation.

### D.5 REST API contracts

| Method/path | Behavior |
|---|---|
| `GET /api/health` | Liveness and DB readiness; service error must not masquerade as healthy |
| `GET /api/database/stats` | Actual master row count and synthetic-only metadata where safe |
| `POST /api/imports` | Multipart CSV upload, parse/validate, create run, return `run_id`, rows/counts and diagnostics |
| `POST /api/imports/{run_id}/compare` | Start/reuse idempotent comparison; accept validated threshold/config; return state and run reference |
| `GET /api/imports/{run_id}/status` | Pending/running/completed/failed and accurate counts |
| `GET /api/imports/{run_id}/results` | Stable paginated results; `page`, `page_size`, `status`, `method`, `review_decision`, `q`, optional similarity range, sortable allowlist; totals and no-match outcomes |
| `GET /api/imports/{run_id}/candidates/{upload_record_id}/{entity_id}` | Raw & normalized pair fields, matched/conflicting evidence, exact IDs, rule reason, review history |
| `POST /api/imports/{run_id}/reviews` | Schema-validated permitted decision, idempotency key, append-only history, return current decision |
| `GET /api/imports/{run_id}/reviews` | Paginated review events/current decisions |
| `GET /api/imports/{run_id}/export?type=uploaded_summary|master_summary|candidate_details` | CSV generated by **single** export service with explicit grain and accurate fields |
| `GET /api/imports/{run_id}/metrics` | Run counts/timings; evaluation precision/recall/F1 only if labeled evaluation executed, never invented |
| `POST /api/imports/{run_id}/verify` *(optional)* | Bounded, budget-checked async verification requests only when enabled/authorized |
| `GET /api/imports/{run_id}/verification-jobs` *(optional)* | Async job progress/cost without blocking results |

Use Pydantic request/response schemas, clear 4xx for invalid user input and 5xx for genuine server faults, safe error codes, pagination with stable ordering (e.g. status then ID), maximum page size, anti-CSRF protections when cookie auth is used, consistent access control on run-specific resources. Export types are explicit: `uploaded_summary`, `master_summary`, `candidate_details`. No second `export` route logic inside React.

### D.6 Group 5 acceptance gates (implementation pending)

All required migrations complete; 10,000 master rows and exactly 200 intentional groups seed reproducibly; SQLite foreign keys and uniqueness constraints tested; normalized identifier indexes exist; all API contracts return real data; actual Entity IDs/Legal Names are correct; retries preserve one candidate pair and one review event; full result and export queries survive restart; AI-disabled mode passes independently; no direct master mutation; backend API tests pass; representative query plans and runtimes recorded. Business approvals DEC-01–DEC-03 remain unresolved until confirmed.

---

## Appendix E — Group 6: Frontend, UI/UX, Human Review & Reporting (approved three-page design)

### E.1 Three-page IA and approved screenshot

Build **only three main pages** and navigation destinations: **Dashboard & Upload** → **Matching Results & Reviews** → **Reports & Exports**. Do not add separate Reviews, AI, Audit, Analytics, Settings, or Evaluation pages for this demo. Put review history in candidate details; optional AI in the same detail panel; related-name leads in results filter/tab.

**Approved visual reference:** `assets/matching-results-approved.png` (the user's approved Matching Results screenshot, distributed alongside this MD in the implementation package). Reproduce its overall information hierarchy: dark navy navigation, clean light canvas, teal/blue accents, five summary cards, compact filter row, clear results grid, status/review badges, actions, restrained spacing. Reconcile screenshot navigation to **three** approved pages. Screenshot counts/text are mockups; fetch all actual data from backend. Other two screens inherit this design language, not extra navigations.

### E.2 Page ownership, actions and states

| Main page | Required workflows |
|---|---|
| **1. Dashboard & Upload** | Live DB count; recent runs; drag/drop or browse CSV; file validation/row diagnostics; 80% default fuzzy threshold (configurable 50–100); clear/reset; start comparison; processing/failure/success and direct link to results |
| **2. Matching Results & Reviews** | Run header and five cards (uploaded rows, strong candidate pairs, potential fuzzy candidate pairs, needs-review pairs, reviewed pairs); company/Entity ID search; match method, status, reviewer decision and similarity filters; backend sorting/pagination; authoritative candidate grid; related-name leads filter; details drawer comparing source vs master; matched/conflicting evidence and rule reason; confirm/not duplicate/needs review; review history; optional AI verification evidence and states |
| **3. Reports & Exports** | Choose run and export type; download uploaded summary, master summary, or detailed candidate pairs; show success/failure; filter scope clearly; no frontend-generated CSV; correct IDs and Legal Names |

**Candidate result grid columns:** selection (only if bulk actions are implemented; otherwise omit checkbox), Uploaded Company, Matched Entity ID, Matched Legal Name, Match Method(s), **Name Similarity (%)**, Match Status, Review Decision, View Details/Review. Names/IDs denote **source vs master** distinctly. Optional selected-row export only if backend supports and tests it; no decorative nonfunctional controls.

**Evidence drawer:** side-by-side original uploaded company/legal name/website/LinkedIn and matched master Entity ID/legal name/website/LinkedIn, plus canonical compared values, matching/contradictory fields, actual fuzzy similarity when calculated, backend-generated reason, review controls and append-only history. For exact matches with no name comparison show `N/A`, not fake `100%`. Keep `match_status`, optional `ai_relationship_type`, and latest `review_decision` separately visible. Related-name leads must never count as mandatory Potential Duplicate.

**Counting units:** uploaded = distinct uploaded rows; candidate status cards = unique candidate pairs by **system** status; reviewed = unique pairs whose latest human decision is non-pending; database records = distinct master Entity IDs. Never sum unrelated units or derive inaccurate counts from only the visible page.

**Data handling:** backend pagination/filter/search, bounded rows per page, debounce search, loading/error/empty/no-match/retry states, preserve existing results during optional AI jobs, no unescaped user HTML, responsive accessible tables/drawers, keyboard and screen-reader support, focus management. UI must never independently calculate classifications or scores.

### E.3 Export contract — one backend export service, three views

| Export type | Row grain | Required fields |
|---|---|---|
| `uploaded_summary` | One `(run_id,upload_record_id)` | Source row/Company Name/Legal Name/Domain/LinkedIn, candidate counts, strongest system outcome, review summary; includes accepted no-candidate inputs |
| `master_summary` | One `(run_id,entity_id)` | Actual `entities.entity_id`, **adjacent** `entities.legal_name`, company name, original web domain and LinkedIn, matched uploaded row count, strongest evidence/status, review summary |
| `candidate_details` | One `(run_id,upload_record_id,entity_id)` | Run/source company/legal, master Entity ID/**adjacent** Legal Name/company/domain/LinkedIn, match method(s), name similarity, system status, evidence, conflicts, optional AI conclusion, latest review decision; optional explicit no-candidate source row only if documented |

Sort deterministically; preserve nullable values; protect against CSV formula injection even with leading whitespace/control characters. Preserve distinct Entity IDs sharing a normalized name/domain. No `IMPORT_BATCH` substitution. **DEC-03 remains business-owner-dependent**: client-designated Potential Duplicate download must be mapped to the requested summary grain before production claim. **Status-percentage issue:** maintain distinct `Name Similarity (%)` and `Match Status`, with no invented exact-match score; obtain approval if stakeholder insists on percentage inside Status.

### E.4 Human review and audit

Actions: `confirmed_duplicate`, `not_duplicate`, `needs_review`. Store review events append-only with reviewer, timestamp, previous/current decisions, reason and idempotency key. Latest valid event defines current human status. Never mutate `entities` or system match evidence. If review POST fails, UI must not claim saved. No separate review page; results drawer handles review/history. For demo, an explicitly marked demo identity may be configured; production requires real auth and authorization.

### E.5 Group 6 acceptance checks (implementation pending)

Three nav pages only; screenshot-conforming Matching Results; all active controls functional; live DB statistics and upload validation; default 80 threshold; backend results, matching evidence and correct Entity IDs/Legal Names; correct `N/A` similarity for non-fuzzy records; unique pairs and preserved one-to-many matches; review survives refresh and history remains intact; all three export views yield correct grain with CSV formula defenses; related-name leads separate; AI-disabled screens work without dead buttons; mobile/keyboard usability; upload→compare→inspect→review→export browser test passes.

---

## Appendix F — Group 7: Security, Performance & Testing (strict quality gates)

### F.1 Non-negotiable test rules

- **Exactly 10,000 deterministic synthetic records; exactly 200 intentional duplicate groups.** Every group contains at least two records and stable underlying truth IDs; generator detects and fails any accidental additional truth groups. Ground-truth labels belong exclusively to evaluation. Include hard negatives: Trimark look-alikes, shared domains across distinct legal entities, parent/subsidiary, conflicts, missing/invalid fields, repeated uploaded rows.
- Rule tests cover **BR-01 through BR-15**, exact threshold `80.0`, below-threshold, master-side missing-ID provisional fallback, malformed LinkedIn/lookalike URLs, public suffix domains, no blank-to-blank match, one-to-many results and candidate aggregation.
- **Mandatory integrity:** real `entity_id` and adjacent `legal_name` 100% accurate on known test fixtures; zero duplicate records at each export's declared grain; distinct legitimate candidate pairs never discarded; zero automatic master record updates/deletes/merges.
- **Benchmark on held-out group-separated labels:** measure precision, recall, F1, candidate recall, false positives/negatives, test sample counts and tested dataset/scenarios. Proposed gates: precision >=95%, recall >=90%, F1 >=92%, candidate recall >=99% on the defined synthetic holdout; not guaranteed on real data. If contradictory results occur, report and fix/seek approval—never relabel the evaluation to pass. Evaluate non-match/insufficient-data separately from candidates.
- **Functional layers:** normalization and matcher unit tests, deterministic seed tests, database constraint/migration tests, API integration, authenticated operation checks, Playwright full upload→compare→filter→details→review→export, no-AI tests, and failed-provider/DB/error regression.

### F.2 Performance targets — baseline reference hardware must be recorded

| Operation | Proposed target | Conditions |
|---|---|---|
| DB stats | p95 <=500 ms | Local reference environment, warmed data; report sample and setup |
| CSV validation | <=1 s | 10 incoming records, 5 MB max CSV |
| Core comparison | <=3 s | 10 records vs 10,000 SQLite master entities, **AI disabled**, with all qualifying candidates retained |
| Paginated results/filter | p95 <=500 ms | Reasonable page size + representative filters |
| CSV export | <=3 s | Up to 10,000 exported rows |
| Optional verification | **nonblocking** | Initial Group 3 results visible regardless of provider latency/failure |

Benchmark both first-run and warmed cases; include hardware/OS, Python/SQLite versions, dataset seed, output counts, p50/p95, peak memory and query-plan/index evidence. Evaluate 100K and 1M **separately** if resources permit; do not assert those sizes were tested when they were not. Do not impose top-K caps that silently omit qualifying candidates. Profiling before optimizations; optimized candidate recall must be compared with exhaustive eligible baseline.

### F.3 Security, data safety and failure recovery

| Area | Mandatory control/test |
|---|---|
| Uploads | Restrict CSV content/type, size 5 MB, encoding, row limits, safe filenames; malformed rows produce bounded readable errors; guard spreadsheet formula output |
| Database | Bound parameters / safe ORM, FKs enabled, migrations backed up, transactions and uniqueness constraints; no master mutations from matching/review |
| Auth | Explicit demo-only mode; before multi-user production require authenticated sessions, run-level authorization, reviewer permissions, CSRF protection when cookie auth, and secure session controls |
| External AI | Feature disabled by default; no secrets in frontend/logs; server-side rate/budget checks; SSRF and prompt-injection defenses; third-party transfer only with owner approval |
| Robustness | Database down != `No Match`; provider down != incorrect duplicate; correct timeouts/retry limits; failed/incomplete runs not shown as complete; repeat requests idempotent |
| Observability | Structured logs keyed by run/candidate/job ID; record counts, versions, latency, memory, errors, review events and optional usage/cost; never log secrets or excessive personal data |
| Retention | Documented configurable policies for raw uploads, temporary files, AI evidence, run results and append-only review history; do not silently delete master entities |

### F.4 Mandatory release gates

| Gate | Required proof |
|---|---|
| QG-01 | All BR-01–BR-15 functional rule tests pass |
| QG-02 | Real Entity ID + correct Legal Name integrity verified; no duplicate result/export keys |
| QG-03 | Precision/recall/F1/candidate-recall measured and satisfy **approved** synthetic targets or documented waiver (cannot claim passing without it) |
| QG-04 | Measured baseline timings meet approved limits on declared reference environment; failure triggers analysis and rerun |
| QG-05 | Full backend+frontend browser E2E workflows pass, including no-match and error states |
| QG-06 | No unresolved critical security vulnerabilities and production auth gate explicitly separated from demo |
| QG-07 | AI-disabled installation works without provider keys or paid calls; optional AI failure does not break core |
| QG-08 | Run retries, review edits, exports and audit history are idempotent/persistent as defined |
| QG-09 | No duplicate implementations of matching, classification, normalization, candidate grouping, or exports |
| QG-10 | All required tests executed; raw results, logs and known limitations retained in delivery |

**Agent rule:** Never mark an unexecuted test or unverified accuracy/performance claim as PASS. Never weaken the business rules or tests merely to pass. Fix failed critical tests, rerun impacted regression tests and clearly report any blocked deployment requirements. Production acceptance also requires owner decisions and real-data evaluation, not only synthetic gates.

---

## Appendix G — Group 8: Deployment, Documentation & Delivery (final engineering specification)

### G.1 Scope and deliverables

Group 8 owns **production integration, deployment architecture, environment setup, final documentation, master Markdown readiness, and the demo handoff**. It does **not** introduce new matching, AI, export or review logic. Deliver a working full-stack repository, not only screenshots or an API stub.

| Deliverable | Required evidence |
|---|---|
| Reproducible repository | Backend + frontend + Alembic migrations + deterministic seed + evaluation fixture/scripts + tests + approved reference asset + `.env.example` + pinned dependencies |
| Local deployment | Documented one-command or short startup sequence; Flask/WordPress is not required in this independent PoC; verify FastAPI + React work together |
| Container option | `Dockerfile`/Compose or equivalent, persistent SQLite volume, proper healthchecks; do not add nonessential services |
| Optional AI removal | With `AI_VERIFICATION_ENABLED=false`, build/run/test without keys, external provider or worker. Optional extras never block core |
| Production integration | Document the actual external WordPress/Yardi/CRM/other data source **only after company confirms**. Do not pretend direct WordPress integration is approved; map real Entity IDs/Legal Names and import/export contracts explicitly |
| Operations | Versioned migrations with backup/restore test, environment/secrets configuration, safe file retention, monitoring, admin/reviewer roles before multi-user release |
| Documentation | README setup/run/seed/reset instructions; sample CSV and expected result; API/OpenAPI contract; matching logic and approved assumptions; troubleshooting; security notes; export format; user review guide; deployment and rollback guide |
| Evaluation report | Actual measured metrics, dataset seed and labeled holdout composition, comparisons against baseline, timings/costs, unresolved tests and limits; no invented benchmark figures |
| Handoff/demo | Live local run of CSV upload → validation → compare → results → candidate details → human review → three export views; show Trimark-like lead (not auto-confirmed), ID/name integrity, no duplicate rows and AI-disabled operation |

### G.2 Strict implementation sequence for the coding agent

1. **Inspect existing repository and this spec.** Reuse/extend existing files; do not rewrite working components. List actual files/dependencies and discrepancies before edits.
2. **Seed and test data.** Create migration and deterministic generator; enforce **exactly 10,000 rows and exactly 200 intentional duplicate groups**, intentional positive/negative scenarios and separate holdout ground truth; do not silently overwrite existing DB.
3. **Pure data/matcher foundation.** Implement one normalization service, exact domain/LinkedIn comparisons, mandatory >=80% eligible Legal Name fuzzy, separate related-name discovery, candidate aggregation and classification. Run unit/ground-truth tests before UI work.
4. **Backend persistence/API.** Add indexed candidates, immutable master data, transactional unique result pairs, run lifecycle/idempotency, append-only reviews, one export service and fully validated FastAPI routes. Demonstrate real API calls.
5. **Three-page UI.** Implement Dashboard & Upload, approved screenshot-styled Matching Results & Reviews, Reports & Exports. All buttons must function; no static placeholder counts or fake results.
6. **Performance and reliability.** Profile matching, improve blocking only with measured candidate recall; run API/browser/security/failure/restart tests. Fix defects, rerun.
7. **Optional AI phase.** Keep OFF by default. Only add mocked verification adapter/worker after core passes. Live provider activation requires explicit credentials, spending limits, data-transfer approval and measured benefit; do not block delivery on paid APIs.
8. **End-to-end handoff.** Start application, validate actual output, export all report formats, capture tests/benchmarks, update README, deliver known limitations and explicit open business approvals.

### G.3 Local commands and minimal runtime verification

Provide executable repo-specific commands; the following are a target layout and must be reconciled with actual files:

```bash
# Backend (after creating virtual environment and installing pinned dependencies)
python -m database.seed_database --reset --seed 42 --rows 10000 --duplicate-groups 200
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend (in a separate shell)
cd frontend
npm ci
npm run dev

# Tests
pytest -q
npm run build
npx playwright test
```

**Ordering caveat:** Create schema via migrations **before** seed if the generator relies on migrated tables; document the actual validated order in README. Do not copy the illustrative module path or flags verbatim unless implemented. In CI, use separate test DB and seeded fixtures; never reset the user's existing database as part of tests. Check `/api/health`, count=10000, exact groups=200 from generator/evaluation metadata, a 10-row upload, results, review history and CSV exports.

### G.4 Delivery manifest and sign-off checklist

Required files/evidence: source tree; version-locked dependencies; database migrations; deterministic seed script and synthetic data manifest; `assets/matching-results-approved.png`; sample CSV; reference ground truth/holdout labels (isolated from runtime); tests and CI commands; readme, API docs, user guide, error/troubleshooting instructions; run and evaluation report; screenshot of **real** working UI (not only approved mock); no secrets; list of deviations.

**Local demo sign-off:** All Group 7 quality gates pass on the stated environment, all 3 pages work, 10k/200 verified, all client complaints demonstrably addressed **within provisional rule assumptions**, original data unchanged, AI-disabled mode works. Mark result “Local demo validated” only if executed.

**Production sign-off is a separate decision:** written owner approval DEC-01, DEC-02, DEC-03 and literal Status-percentage presentation; client confirms intended export grain and source integration; representative real-data precision/recall and false positive review; auth/roles, privacy/compliance, hosting/backups, monitoring, operational SLAs and vendor API approval where used. Without those, mark “Production not yet approved” and list blockers. Never invent production deployment or actual accuracy.

### G.5 No duplicate implementation / no unfinished work contract

- Preserve a single authoritative service for each responsibility. If a new component overlaps a prior one, **extend the existing component** instead of building a second route, matching function, scorer, export pipeline or review store.
- Avoid TODO-only endpoints, buttons without functionality, client-side fake data, unused duplicate page components and untested scaffolds.
- Distinguish **designed**, **implemented**, **tested**, **demo validated**, **business approved**, and **production deployed**; these labels must never be conflated.
- If a dependency is unavailable, complete all work possible offline, record the exact limitation and leave the optional feature disabled. Never claim tests or deployment succeeded if they were not executed.

**Group 8 status: engineering specification complete; implementation, measured results, demo validation and business/production release approval remain pending.**


### G.6 Final agent execution and delivery gate — mandatory last step

**This is the FINAL implementation step. It must be performed after Groups 1–7 have been implemented, not merely planned.** The coding agent must execute the application in the target local environment, verify the complete user journey, and leave independently inspectable evidence. Do not finish with a design summary or say “done” based on source files alone.

**Final execution checklist (all mandatory):**

1. **Fresh setup succeeds:** From clean documented dependencies, run migrations **before** seeding where required; seed the deterministic master; validate exactly **10,000 master records and exactly 200 intentional duplicate groups**, with no accidental true-identity overlaps. Never overwrite an existing client/user database during setup or testing.
2. **Full-stack app launches:** Start the actual FastAPI backend and React frontend; verify health endpoints and visible UI, with **exactly three primary pages**. Use live backend data; all displayed actions work, no mock/static production data or dead controls.
3. **Real workflow passes:** Upload a representative 10-row CSV, inspect validation, start comparison, inspect candidates and evidence, apply filters, save/modify a human review, refresh to confirm persistence, and download **all three** report formats. Verify a no-match row is accounted for.
4. **Client complaint regression passes:** Demonstrate domain-versus-raw-URL normalization, exact LinkedIn match, mandatory eligible 80% fuzzy threshold, Trimark-type **related-name lead** distinct from confirmed matches, correct real `Entity ID` with **adjacent correct Legal Name**, no `IMPORT_BATCH` placeholder, no duplicate rows at any report’s defined grain, and correct one-to-many candidate preservation.
5. **Safety and AI-disabled operation pass:** Show no automatic merge/update/delete; no hidden paid API usage; `AI_VERIFICATION_ENABLED=false` works without any AI credentials/packages. Test failures for bad CSV, unavailable DB and interrupted/export requests without false success or false `No Match`.
6. **Group 7 evidence passes:** Execute unit, integration, browser E2E, regression, security and performance checks; record raw command outputs, failures, measurement conditions, precision/recall/F1/candidate recall and timing results. **Any failed mandatory gate blocks local-demo sign-off.** Never fabricate results or weaken tests.
7. **Package and document:** Deliver runnable source, locked dependencies, migrations, seed, sample input, evaluation labels/scripts, approved UI reference, tests, `.env.example`, README with **verified** startup commands, API/export documentation, troubleshooting, backup/restore procedure, and actual measured test report. Exclude secrets, real credentials and generated caches.
8. **Final handoff report:** Include a concise matrix for **Implemented / Tested / Passed / Failed / Blocked / Not Run** against QG-01–QG-10 and Groups 1–8; exact run commands and environment; known defects; remaining DEC-01/DEC-02/DEC-03 and Status-percentage approval requests; and whether only the **local demo** or also production has been authorized. Production must remain **NOT APPROVED** until client decisions, representative real-data evaluation, production authentication and operational controls are verified.

**Stop rule:** If a required step fails, fix and rerun the affected tests before marking it passed. When an external dependency genuinely prevents completion, deliver the working independent core plus evidence and mark that step **BLOCKED**, never silently substitute mock success. Do not introduce extra pages, duplicate matching pipelines, fabricated confidence scores, or new business rules to close a checklist item.

**Required final agent response:** `(1) what is built; (2) exact local run instructions; (3) executed tests and measured results; (4) output file/repository paths; (5) unresolved defects and business approvals; (6) honest local-demo and production-readiness statuses.`

**End of Group 8 — end of master build specification.**
