**DiagramGPT (GraphTech_V1) --- Implementation Plan**

**From Frontend Prototype to the Target AI Diagram-Generation Pipeline**

**1. Current System Assessment**

I inspected the uploaded repository directly (not a generic template).
Here is the ground truth.

**1.1 What actually exists in the repo**

The repository contains **only a frontend** --- a Vite + React 19 SPA.
There is no backend/ directory, no server code, no API routes, no
database schema, no Python at all. package.json lists exactly three
runtime dependencies: react, react-dom, three, and lucide-react for
icons. There is no mermaid, no HTTP client (axios/fetch wrapper), no
.env handling, and no auth SDK.

What **is** well-built, and should be preserved:

-   **Layout shell**: Navbar, CleanBackground, Background3D (three.js),
    HistorySidebar, ChatGPTWelcomeHero (discover/landing page).

-   **Unified Studio workspace** (UnifiedStudioTab.jsx): resizable split
    view with ChatPanel (left) and DiagramPanel (right), layout modes
    (split/canvas/chat), fullscreen lightbox (FullScreenImageViewer).

-   **Diagram viewer chrome** (DiagramViewer.jsx): preview/code toggle,
    zoom in/out/reset, copy-DSL-to-clipboard, download-as-SVG,
    \"Regenerate\" button --- all wired to props/handlers, ready to
    receive real data.

-   **Chat UI** (ChatPanel, ChatInput, MessageBubble): message list,
    attachment picker (image/PDF/SVG), Enter-to-send, distinct \"Chat\"
    vs \"Generate Diagram\" actions.

-   **Pipeline progress UI** (PipelineProgress.jsx,
    ClaudeWorkingProgress.jsx): a 6-step visual stepper with labels
    already named after the target pipeline stages (Prompt
    Understanding, Information Extraction, Complexity Classification,
    Routing, Diagram Generation, Validation).

-   **History sidebar**: list, select, delete, \"new chat\".

This is a solid, reusable component layer. **The task is to wire it to a
real backend, not to redesign it.**

**1.2 What is mocked / simulated (confirmed by code inspection)**

  -------------------------------------------------------------------------------------
  **Area**             **File(s)**               **What\'s actually happening**
  -------------------- ------------------------- --------------------------------------
  **Diagram            data/diagramSamples.js,   getDiagramDataForPrompt() runs a
  generation**         App.jsx                   **keyword includes() match**
                                                 (microservice, erd/schema, workflow)
                                                 against 3 **hand-written, hardcoded**
                                                 SVG+Mermaid-DSL pairs. Any prompt that
                                                 doesn\'t hit a keyword falls into
                                                 getCustomArchitectureDiagram(), which
                                                 returns the **same generic 6-node SVG
                                                 every time**, just captioning it with
                                                 a truncated copy of the user\'s prompt
                                                 text. No LLM, no embeddings, no
                                                 rendering engine is ever invoked.

  **AI pipeline**      App.jsx:                  The \"6-stage AI pipeline\" is
                       runGenerationPipeline,    setTimeout calls at a fixed
                       PipelineProgress.jsx      320ms/step. activeStepIndex just
                                                 increments on a timer. There is no
                                                 correlation between the visual steps
                                                 and any real computation --- the
                                                 diagram (from the hardcoded table
                                                 above) is already fully formed before
                                                 the animation starts.

  **Validation**       App.jsx completion        Every generated diagram is
                       message,                  unconditionally stamped validation:
                       diagramSamples.js         \'✓ Passed\' / *\"Structural AST
                                                 validation passed with zero
                                                 topological violations.\"* This is a
                                                 string literal, not a check.

  **Complexity         diagramSamples.js         complexity: \'Moderate\' (or
  classification**                               \'Simple\') is a **static field on the
                                                 hardcoded sample**, not computed from
                                                 the prompt.

  **Authentication**   GoogleAuthModal.jsx       \"Google Sign-In\" and email/password
                                                 login are both setTimeout(() =\>
                                                 onLoginSuccess({\...fakeUser}), 700).
                                                 No OAuth flow, no password check, no
                                                 backend call, no session/token.
                                                 handleGoogleOneTap hardcodes the same
                                                 fake user (Alex Rivera) every time.

  **Chat replies**     App.jsx:                  AI chat responses are if/else string
                       handleSendMessage         templates keyed on substrings in the
                                                 user\'s text (microservice, database,
                                                 cloud, workflow) --- not an LLM call.

  **Attachments /      ChatInput.jsx             Files are read client-side via
  reference images**                             FileReader.readAsDataURL and held in
                                                 React state only. They are **never
                                                 sent anywhere** --- not to a vision
                                                 model, not to storage.
                                                 handleGenerateDiagram ignores the
                                                 attachment entirely when building the
                                                 diagram.

  **History            App.jsx,                  history is an in-memory React array
  persistence**        HistorySidebar.jsx        seeded from INITIAL_HISTORY. No
                                                 localStorage, no API, no database ---
                                                 a page refresh wipes everything.
                                                 Selecting a history item just re-runs
                                                 the same keyword matcher on the stored
                                                 prompt string.

  **Similar-diagram    ---                       Does not exist in any form. There is
  reuse**                                        no concept of \"similarity,\"
                                                 \"embeddings,\" or \"reuse\" anywhere
                                                 in the code --- I grepped for fetch(,
                                                 axios, localStorage, process.env,
                                                 import.meta.env across the whole src/
                                                 tree and the only matches were
                                                 unrelated SVG logo markup.

  **General image      ---                       Does not exist. There\'s no separate
  generation (Gemini                             flow, button, or code path for
  path)**                                        creative/general image generation.
  -------------------------------------------------------------------------------------

**1.3 What is entirely missing (not even mocked)**

-   Any backend service (FastAPI/Flask/Node --- none exists).

-   Any database (PostgreSQL, pgvector extension, schema, migrations).

-   spaCy preprocessing.

-   Voyage embeddings client.

-   Groq LLM client / prompt templates / structured-output parsing.

-   Pydantic models and deterministic validation rules.

-   A diagram-type taxonomy/detector.

-   A renderer abstraction (Mermaid CLI, PlantUML, Graphviz, Schemdraw)
    and the renderer-selection logic.

-   Output/image validation (SVG/PNG structural checks, node/edge count
    reconciliation, OCR/label checks).

-   Repair/regeneration retry loop with bounds.

-   Real authentication/session management and per-user data isolation.

-   Rate limiting, request idempotency/dedupe, timeouts, and error
    surfaces in the UI.

-   API-key/secrets handling of any kind.

-   A Gemini-backed general-image-generation path, kept isolated from
    the diagram pipeline.

**1.4 Important technical gaps that will shape sprint order**

1.  **There is no contract between frontend and backend yet.** The
    diagram object shape (title, type, complexity, renderer, dslCode,
    svgContent, nodesCount, edgesCount, validation, latency) that the UI
    already expects is a good starting point for the real API response
    schema --- reuse it rather than inventing a new one, to minimize
    frontend churn.

2.  **The pipeline UI is a fixed-step animation, not an event stream.**
    To show real progress (e.g., \"similarity search,\" \"Groq call,\"
    \"rendering,\" \"validating\") the frontend needs to move from a
    setTimeout loop to consuming real backend status (either polling a
    job-status endpoint or a simple SSE/WebSocket stream) --- this is a
    frontend architecture change, not just a data-source swap.

3.  **Nothing enforces separation between reused and freshly-generated
    diagrams today**, so the \"never blindly reuse a merely similar
    diagram\" requirement must be designed in from the first backend
    sprint, not bolted on later.

4.  **No security surface exists at all today** (no auth backend, no key
    handling), so basic hardening (real session auth, key storage,
    per-request validation) has to land in Sprint 0, before any AI
    functionality, or every later sprint inherits an insecure
    foundation.

**2. Target System Summary**

The existing frontend becomes the **presentation layer** for a new
FastAPI backend that owns the entire pipeline in the diagram you
provided. Concretely:

-   ChatInput\'s \"Generate Diagram\" action stops calling
    getDiagramDataForPrompt() and instead calls POST
    /api/diagrams/generate, which runs: spaCy (optional) → Voyage
    embedding → pgvector similarity search → reuse-or-generate branch →
    Groq structured JSON (only when generating fresh) → independent
    complexity classification → Pydantic + deterministic validation →
    diagram-type detection → renderer selection → renderer code
    generation → Mermaid/PlantUML/Graphviz/Schemdraw execution →
    output/image validation → bounded repair loop → response.

-   The response is shaped to match (a superset of) the existing diagram
    object already consumed by DiagramViewer/DiagramPanel, so those
    components need field-mapping changes, not rewrites.

-   PipelineProgress is repointed at real backend stage events
    (job-status polling to start; upgrade to SSE later if time allows)
    instead of a timer.

-   GoogleAuthModal is repointed at real OAuth (Google) + a backend
    session, with history and diagrams scoped per authenticated user and
    persisted in PostgreSQL instead of React state.

-   A new, clearly separate POST /api/images/creative (Gemini-backed)
    path is added for general/creative image requests, with its own UI
    affordance so it is never confused with --- or silently substituted
    into --- the technical diagram pipeline.

-   Reuse from pgvector is treated as a **candidate**, never an
    automatic answer: it is always re-validated (schema + deterministic
    rules) before being returned, and is only returned unchanged when it
    passes the same validation bar as a freshly generated diagram.

**3. Agile Sprint Plan**

Assumptions: 4-person team, \~1-week sprints, one shared Postgres
instance, no microservices --- a single FastAPI monolith with clearly
separated internal modules (ingestion/, retrieval/, generation/,
rendering/, validation/, auth/). Each sprint ends with something
demoable end-to-end, even if narrow.

**Sprint 0 --- Foundations, Auth, and Project Skeleton**

**Sprint goal:** Replace the fake-everything shell with a real backend
skeleton and real authentication, with zero AI functionality yet --- so
every later sprint builds on a secure, testable base.

-   **Backend:** Scaffold FastAPI app; /health endpoint; project
    structure (app/api, app/core, app/models, app/services); centralized
    settings via environment variables (never hardcoded); CORS config
    for the Vite dev server.

-   **Frontend:** Replace GoogleAuthModal\'s fake setTimeout logins with
    real Google OAuth (Authorization Code flow) + a backend
    /auth/session exchange; store session via httpOnly cookie or
    short-lived token (not localStorage of raw credentials); wire
    App.jsx\'s isLoggedIn/currentUser state to real session data instead
    of the fabricated Alex Rivera/avatar object.

-   **AI/LLM work:** None yet.

-   **Database work:** Provision PostgreSQL with the pgvector extension
    enabled; create users and diagram_requests tables (schema per the
    provided architecture diagram: id, prompt, embedding VECTOR(1024),
    structured_json JSONB, complexity, renderer, created_at,
    output_path, plus user_id, status); set up Alembic (or equivalent)
    migrations.

-   **Validation/testing:** Auth flow integration test (login → session
    → protected route); DB connection health check.

-   **Dependencies:** None (first sprint).

-   **Deliverables:** Running FastAPI backend behind auth; real login
    replacing the fake modal; empty-but-correct DB schema.

-   **Definition of Done:** A user can really sign in with Google, get a
    real session, and hit one authenticated backend route from the
    deployed frontend; no credentials or user data are fabricated
    client-side.

**Sprint 1 --- Ingestion, Embeddings, and Similarity Search (Reuse
Path)**

**Sprint goal:** Stand up the \"left half\" of the pipeline --- prompt
in, similarity search out --- without any generation yet, so the
reuse-vs-generate decision can be built and tested in isolation.

-   **Backend:** POST /api/diagrams/prepare (internal/dev-only at this
    stage) that accepts a prompt, runs optional spaCy preprocessing
    (tokenization, normalization, entity extraction), calls Voyage for
    the embedding, and performs a pgvector top-k similarity query
    against diagram_requests.

-   **Frontend:** No user-visible change yet; add a debug panel or
    logging only if useful for the team.

-   **AI/LLM work:** Integrate spaCy pipeline (optional stage --- a
    config flag to skip it, since it\'s marked optional in the target
    workflow); integrate Voyage embeddings client with retry/timeout
    handling.

-   **Database work:** Seed diagram_requests with a handful of manually
    validated diagrams (structured JSON + embeddings) so similarity
    search has something real to match against; add an index
    (ivfflat/hnsw) on the embedding column.

-   **Validation/testing:** Unit tests for the embedding client
    (timeout, malformed response); tests asserting the similarity search
    returns ranked candidates, not just \"found/not found.\"

-   **Dependencies:** Sprint 0 (DB, auth, config plumbing).

-   **Deliverables:** A working, testable \"given a prompt, return the
    top-k similar validated diagrams with scores\" capability.

-   **Definition of Done:** For a known prompt near a seeded diagram,
    the top match\'s similarity score is above threshold and the correct
    record is returned; for an unrelated prompt, nothing crosses the
    threshold.

**Sprint 2 --- Groq Generation, Pydantic Validation, and Independent
Complexity Scoring**

**Sprint goal:** Build the \"generate fresh\" branch and make it
impossible for the LLM\'s own claims (validity, complexity) to be
trusted blindly.

-   **Backend:** POST /api/diagrams/generate (still without rendering)
    that: on cache miss (or low-confidence match) calls Groq with a
    constrained prompt to produce structured JSON (nodes, edges, diagram
    type, attributes); on cache hit re-validates the retrieved JSON
    through the same validators before returning it as a \"reused\"
    result.

-   **Frontend:** None yet --- this sprint is backend/AI-only.

-   **AI/LLM work:** Define the Groq prompt/response contract;
    **independently compute complexity** from the structured JSON itself
    (e.g., node count, edge count, cyclomatic-style graph metrics,
    nesting depth) rather than accepting any complexity value the LLM
    reports; reject/flag prompts whose independently computed complexity
    exceeds a configured ceiling *before* any rendering is attempted.

-   **Database work:** Persist every generation attempt (including
    rejected ones) to diagram_requests with status (validated,
    rejected_complexity, rejected_invalid, etc.) for auditability and
    future reuse.

-   **Validation/testing:** Pydantic schema for the structured JSON
    (required fields, types, referential integrity --- every edge must
    reference existing node IDs); deterministic rules (no orphan edges,
    no duplicate node IDs, graph must be connected unless the diagram
    type explicitly allows disconnected components); unit tests with
    deliberately malformed/hallucinated Groq-style responses to confirm
    they\'re rejected, not silently coerced.

-   **Dependencies:** Sprint 1 (embeddings/reuse path must exist so this
    sprint\'s endpoint can decide reuse-vs-generate).

-   **Deliverables:** A single generation endpoint that returns either a
    re-validated reused diagram or a freshly validated one, with
    rejected/oversized requests failing fast and cheaply (before
    rendering).

-   **Definition of Done:** Structurally invalid or hallucinated Groq
    output never reaches the client as a \"success\"; an intentionally
    oversized prompt is rejected pre-render with a clear reason, not
    after burning render time.

**Sprint 3 --- Diagram-Type Detection, Renderer Selection, and
Deterministic Rendering**

**Sprint goal:** Turn validated structured JSON into an actual image,
choosing the right renderer deterministically rather than guessing.

-   **Backend:** Diagram-type detector (rules over the validated JSON\'s
    shape/keywords --- e.g., presence of primary-key/foreign-key fields
    ⇒ ERD; state/transition fields ⇒ state machine --- LLM-assisted only
    as a fallback, never as the sole source of truth);
    renderer-selection mapping (diagram type →
    Mermaid/PlantUML/Graphviz/Schemdraw); deterministic
    JSON→renderer-source compiler for each supported renderer (the
    \"Option B\" path in the diagram --- prefer this over LLM-generated
    renderer code for reliability and cost).

-   **Frontend:** Wire DiagramViewer\'s preview/code toggle to real
    svgContent/dslCode/renderer fields returned by the backend; keep the
    zoom/download/copy features as-is (they already operate on generic
    props).

-   **AI/LLM work:** Only as an optional fallback code-generation path
    when the deterministic compiler doesn\'t yet support an edge case
    --- flagged and logged distinctly from the deterministic path so
    quality can be tracked separately.

-   **Database work:** Store renderer, diagram_type, and output_path
    (rendered file location) per request.

-   **Validation/testing:** Confirm renderer choice matches diagram type
    for a labeled test set; confirm the compiled DSL is syntactically
    valid for its target engine before invoking the renderer binary
    (catch errors before shelling out).

-   **Dependencies:** Sprint 2 (needs validated structured JSON as
    input).

-   **Deliverables:** End-to-end: prompt → validated JSON → correct
    renderer chosen → real SVG/PNG produced and shown in the existing
    DiagramViewer UI.

-   **Definition of Done:** For each of the 4 target diagram types, a
    real prompt produces a real rendered image via the correct engine,
    visible in the actual frontend (not a hardcoded sample).

**Sprint 4 --- Output Validation and Bounded Repair Loop**

**Sprint goal:** Stop trusting \"an image was produced\" as proof of
correctness; add the repair loop.

-   **Backend:** Output validator that checks the rendered artifact
    exists, is a valid SVG/PNG, and --- critically --- that the rendered
    content\'s node/edge count and labels reconcile with the structured
    JSON that was supposed to produce it (catching cases where rendering
    silently dropped or merged elements); bounded repair/regeneration
    loop (e.g., max 2 retries) that can re-invoke the compiler or fall
    back to a different renderer, with a hard stop and an honest failure
    response if repairs are exhausted.

-   **Frontend:** Surface real validation/failure states in the UI
    (replace the hardcoded \"✓ Passed\" badge with the actual validation
    result, including a visible \"regeneration attempted\" or \"failed
    after N attempts\" state) so failures are never silently shown as
    success.

-   **AI/LLM work:** None new --- this sprint is about not over-trusting
    the AI/rendering output from prior sprints.

-   **Database work:** Track repair attempts per request (attempt_count,
    final_status) for observability.

-   **Validation/testing:** Inject deliberately broken renders (e.g.,
    truncate the SVG, mismatch node counts) and confirm the system
    retries then correctly reports failure rather than declaring
    success.

-   **Dependencies:** Sprint 3 (needs a real renderer to validate the
    output of).

-   **Deliverables:** A pipeline that only reports success when the
    rendered artifact actually reflects the validated structure, with
    visible, bounded retries.

-   **Definition of Done:** A forced rendering failure is retried up to
    the configured bound, then surfaces as a clear failure state in the
    UI --- never as a false \"Validated ✓.\"

**Sprint 5 --- Frontend Wiring, Real Pipeline Progress, and Persistent
History**

**Sprint goal:** Retire every remaining mock in the frontend and connect
the full user journey end-to-end.

-   **Backend:** Job-status endpoint (GET /api/diagrams/{id}/status)
    reporting current pipeline stage, for the frontend to poll;
    endpoints for listing/deleting a user\'s own history (GET/DELETE
    /api/history), replacing the in-memory array.

-   **Frontend:** Replace App.jsx\'s runGenerationPipeline setTimeout
    loop with real polling (or SSE) against job status, driving
    PipelineProgress\'s existing step UI with real stage transitions;
    replace handleSendMessage\'s keyword-based canned replies with a
    real (lightweight) chat/QA call, clearly scoped as
    conversational-only (not diagram generation); replace in-memory
    history/INITIAL_HISTORY with data fetched from the backend and
    scoped to the logged-in user; wire the file-attachment flow
    (ChatInput) to actually upload the reference image to the backend so
    it can inform generation context (or explicitly disable/relabel it
    if reference-image-guided generation is out of scope for this
    project).

-   **AI/LLM work:** Decide and implement the scope of the
    \"attachment\" feature honestly --- either it feeds into the Groq
    prompt (e.g., as descriptive context extracted via a lightweight
    caption step) or the UI is updated to stop implying it does
    something it doesn\'t.

-   **Database work:** User-scoped queries for history; cascade delete
    rules for removed history entries.

-   **Validation/testing:** End-to-end test: log in → type a prompt →
    watch real progress stages → see a real diagram → refresh the page →
    history persists and reloads the same diagram.

-   **Dependencies:** Sprints 0--4 (needs auth, full pipeline, and
    validation all functioning).

-   **Deliverables:** A frontend with no remaining hardcoded diagrams,
    fake timers, or fabricated chat replies.

-   **Definition of Done:** Every interactive element in the Studio tab
    is backed by a real API call; a page refresh does not lose the
    user\'s diagram history.

**Sprint 6 --- Separate Gemini Creative Path, Security Hardening, and
Concurrency Safety**

**Sprint goal:** Add the explicitly separate general-image path and
close the security/robustness gaps identified in Section 4.

-   **Backend:** New, isolated POST /api/images/creative route calling
    Gemini, with its own request/response schema (never sharing a code
    path, prompt template, or validator with the technical diagram
    pipeline); request idempotency keys to collapse duplicate/concurrent
    submissions of the same prompt from the same user; rate limiting per
    user/IP; timeouts and circuit-breaking around all three external
    calls (spaCy is local, but Voyage/Groq/Gemini are not) with clear,
    distinct user-facing error states for each failure mode.

-   **Frontend:** A clearly separate UI entry point (e.g., a toggle or
    distinct button) for \"creative image\" vs. \"technical diagram,\"
    so users --- and the code --- never conflate the two; friendly
    error/timeout states instead of an infinite spinner.

-   **AI/LLM work:** Basic prompt-injection defenses on all LLM-facing
    inputs (the user prompt, and worryingly, anything extracted from an
    uploaded attachment) --- strip/neutralize instructions embedded in
    user content before they reach the Groq/Gemini system prompt, and
    never let extracted \"instructions\" alter validation, complexity,
    or security rules.

-   **Database work:** API keys and secrets moved fully to
    environment/secret-manager config (never in the repo or client
    bundle); audit log table for security-relevant events (auth
    failures, rejected oversized requests, repeated validation
    failures).

-   **Validation/testing:** Load-test duplicate/concurrent submission of
    the same prompt to confirm dedupe works; test that a prompt
    containing embedded \"ignore previous instructions\" style text does
    not change the diagram type, complexity classification, or bypass
    validation.

-   **Dependencies:** Sprint 5 (needs the full real pipeline to secure
    and to attach the creative path alongside).

-   **Deliverables:** A working, isolated creative-image feature; a
    hardened, rate-limited, injection-resistant technical pipeline.

-   **Definition of Done:** Gemini calls never occur as part of
    /api/diagrams/generate, and vice versa; duplicate rapid submissions
    produce one billable pipeline run, not N.

**Sprint 7 --- Corner-Case Hardening, Test Pass, and Demo Readiness**

**Sprint goal:** Systematically work through Section 4\'s table, close
remaining gaps, and prepare a stable demo.

-   **Backend:** Fix any remaining items from the corner-case table not
    already covered (stale-state handling, DB failure fallbacks,
    oversized-payload rejection at the API boundary, etc.).

-   **Frontend:** Handle stale-state edge cases (e.g., a diagram
    finishes generating in the background after the user has navigated
    to a different history item --- the result must not silently
    overwrite the wrong view).

-   **AI/LLM work:** Tune thresholds (similarity cutoff, complexity
    ceiling, retry bounds) based on test-set results.

-   **Database work:** Backup/restore drill; confirm migrations are
    idempotent and reversible.

-   **Validation/testing:** Full regression pass against the corner-case
    table; a fixed demo script covering all 4 diagram types, one reuse
    case, one rejection case, and one repair case.

-   **Dependencies:** All prior sprints.

-   **Deliverables:** A demo-ready system with known, tested behavior
    for every corner case in Section 4.

-   **Definition of Done:** Every row in the Section 4 table has a
    corresponding passing test or verified manual check.

**4. Corner Cases & Loopholes**

  ------------------------------------------------------------------------------------
  **Case**                    **Risk**                **Required Handling**
  --------------------------- ----------------------- --------------------------------
  Incorrect similarity match  Silently returns the    Never treat similarity score
  (semantically different     wrong diagram as if it  alone as sufficient; always
  prompt, numerically close   were correct            re-validate the retrieved
  embedding)                                          structured JSON\'s
                                                      Pydantic/deterministic rules and
                                                      re-check it against the
                                                      *current* prompt\'s extracted
                                                      entities before reuse; expose
                                                      the similarity score to
                                                      logs/audit even on reuse

  Hallucinated or missing     Structurally invalid    Pydantic schema + deterministic
  nodes/relationships from    diagram looks plausible graph checks (no dangling edges,
  Groq                        but is wrong            no duplicate IDs, required
                                                      fields present) run on every
                                                      Groq response before it
                                                      proceeds; reject and trigger
                                                      repair rather than passing
                                                      through

  Diagram-type mismatch       Renderer produces a     Diagram-type detection must run
  (e.g., ERD content routed   \"valid\" but           on the *validated structured
  to a flowchart renderer)    meaningless image       JSON*, not raw prompt text
                                                      alone; renderer selection is a
                                                      deterministic lookup from
                                                      detected type, never a free LLM
                                                      choice

  Complexity bypass (LLM      Expensive/unbounded     Complexity is computed
  under-reports complexity to rendering attempted on  independently from the
  avoid rejection)            something that should   structured JSON\'s own graph
                              have been rejected      metrics (node/edge counts,
                                                      depth) --- the LLM\'s
                                                      self-reported complexity is
                                                      logged for comparison but never
                                                      authoritative

  Invalid LLM JSON            Backend crash or silent Strict Pydantic parsing with
  (malformed, truncated,      partial diagram         explicit error handling;
  wrong types)                                        malformed output triggers the
                                                      bounded repair/re-prompt loop,
                                                      not a raw exception to the
                                                      client

  Renderer/source mismatch    Rendering fails or      Renderer identity is attached to
  (DSL generated for one      produces garbage        the compiled source at
  engine, executed with       silently                generation time and checked
  another)                                            immediately before invoking the
                                                      render binary; mismatch is a
                                                      hard validation failure, not a
                                                      warning

  Visually valid but          False sense of          Output validation reconciles the
  structurally incorrect      correctness;            rendered artifact\'s element
  diagrams (image renders     \"success\" reported    count/labels against the source
  cleanly but omits/merges    wrongly                 structured JSON, not just \"did
  elements)                                           a file get produced\"

  Validation false positives  Either bad diagrams     Maintain a small labeled
  (validator too permissive,  ship, or the system is  regression set of known-good and
  or too strict and blocks    unusable                known-bad structured JSON
  valid diagrams)                                     payloads; run it in CI whenever
                                                      validation rules change

  Repair loops (infinite or   Runaway cost/latency,   Hard-coded max retry count
  excessive retries)          hung requests           (e.g., 2) with exponential
                                                      backoff between attempts; on
                                                      exhaustion, return an honest
                                                      failure state, never a
                                                      partial/best-effort success

  Duplicate/concurrent        Wasted API spend, race  Idempotency key per (user,
  requests (double-click      conditions writing to   prompt, timestamp-window);
  \"Generate,\" multiple      history                 server-side de-duplication
  tabs)                                               before triggering a new
                                                      Groq/render cycle

  Stale frontend state        Wrong diagram displayed Tag every in-flight
  (diagram result arrives     against the wrong       request/response with its
  after user navigated away,  prompt/history item     request ID; frontend discards
  or after a newer request                            responses whose ID doesn\'t
  was started)                                        match the currently active
                                                      request

  API failures/timeouts       Hung UI, unclear        Per-dependency timeouts and
  (Voyage, Groq, Gemini,      errors, retries         circuit breakers; distinct,
  renderer binaries)          hammering a down        user-legible error states per
                              service                 failure point rather than a
                                                      generic spinner or crash

  Prompt injection (via user  Injected text alters    Treat all user-supplied text
  prompt or extracted         system behavior,        (including OCR/caption text from
  attachment content)         bypasses                attachments) as untrusted data
                              validation/complexity   passed to the LLM, never as
                              rules                   instructions to the backend;
                                                      validation/complexity/security
                                                      rules are enforced in code,
                                                      outside the LLM\'s control, so
                                                      no prompt content can disable
                                                      them

  Oversized requests (huge    Resource exhaustion,    Hard size limits at the API
  prompt, huge attachment,    cost blowup             boundary (prompt length, file
  pathologically large graph)                         size) enforced before any
                                                      external call is made;
                                                      complexity ceiling enforced
                                                      before rendering

  Database/storage failures   Silent data loss, hung  Explicit error handling around
  (Postgres down, disk full,  requests, corrupted     all DB calls with
  pgvector query timeout)     history                 retries/backoff for transient
                                                      errors; writes are
                                                      transactional; failures surface
                                                      as a clear \"try again\" state,
                                                      not a blank/broken UI

  Security & API-key handling Key leakage,            All keys in server-side
  (keys for                   unauthorized use, cost  environment/secret storage only,
  Voyage/Groq/Gemini/Google   abuse                   never shipped to the client
  OAuth)                                              bundle or logged; per-user rate
                                                      limiting; audit log of key usage
                                                      anomalies

  Fake/absent auth carried    No real access control, Real Google OAuth + backend
  into production (current    no per-user data        session issuance (Sprint 0)
  state)                      isolation               before any user-scoped data
                                                      (history, diagrams) is persisted

  Reference-image attachment  Users trust a feature   Either wire the attachment into
  implying capability it      that silently does      generation context for real, or
  doesn\'t have (current      nothing                 visibly relabel/disable it ---
  state)                                              never leave it appearing
                                                      functional while being ignored
  ------------------------------------------------------------------------------------

**5. Final Architecture (End State, After All Sprints)**

prompt + optional attachment

above threshold candidate

no suitable match

over ceiling

ok

invalid

valid

fails

passes

separate creative request

User - Studio UI

FastAPI Backend

Auth/Session - Google OAuth

spaCy Preprocessing - optional

Voyage Embeddings

pgvector Similarity Search

Re-validate candidate JSON

Groq: structured JSON + self-reported complexity

Independent Complexity Calculation

Reject before render

Pydantic + Deterministic Validation

Bounded Repair/Re-prompt Loop

Diagram-Type Detection

Renderer Selection

Deterministic JSON to Renderer Source

Mermaid / PlantUML / Graphviz / Schemdraw

Output + Image Validation

Validated Diagram Response

POST /api/images/creative

Gemini API

PostgreSQL + pgvector - diagram_requests, users, audit_log

Key architectural properties of this end state:

-   One FastAPI monolith, internally modular --- appropriate for a
    4-person team; no unnecessary service boundaries.

-   The Gemini creative path shares infrastructure (auth, rate limiting,
    DB) but **no code path, prompt template, or validator** with the
    diagram pipeline.

-   Every reuse candidate is re-validated; nothing from pgvector is
    returned \"as-is.\"

-   Complexity and validation are computed in deterministic code, never
    delegated to LLM self-reporting.

-   The repair loop is bounded and feeds back into validation, not
    directly to the user.

**6. Definition of Done (System-Level)**

The system is complete when all of the following are concretely true:

1.  A logged-in user (real Google OAuth session) can submit a
    natural-language prompt and receive a diagram whose type was
    autonomously and correctly detected for each of the 4 supported
    types (Cloud/VPC, Microservices/Architecture, ERD, State/Workflow).

2.  At least one demoable case shows a diagram served from pgvector
    reuse, and that reused diagram passed the same
    Pydantic/deterministic validation as a freshly generated one
    (verifiable via logs).

3.  At least one demoable case shows a prompt correctly rejected for
    excessive complexity *before* any Groq/render cost was incurred.

4.  At least one demoable case shows a deliberately
    malformed/hallucinated structured JSON payload being caught by
    validation and triggering the bounded repair loop, ending in either
    a corrected diagram or an honest failure --- never a false
    \"Passed.\"

5.  Every diagram result shown in the UI carries a real validation
    status derived from actual checks, not a hardcoded string.

6.  The PipelineProgress UI reflects real backend stage transitions for
    a live request, not a fixed timer.

7.  History persists across page reloads and is correctly scoped to the
    authenticated user.

8.  A general/creative image request never touches the
    diagram-validation or complexity code path, and vice versa.

9.  Duplicate rapid-fire submissions of the same prompt result in one
    pipeline execution, not several.

10. No API key, secret, or credential appears in client-side code,
    browser storage, or logs.

11. Every corner case in Section 4 has a passing automated test or a
    documented, verified manual check.

**7. Recommended Implementation Order**

Follow the sprint sequence in Section 3 in order --- each sprint is a
hard dependency for the next:

1.  **Sprint 0** --- Backend skeleton + real auth (unblocks everything;
    nothing else should be built on top of the current fake-login
    state).

2.  **Sprint 1** --- Embeddings + similarity search (the reuse path must
    exist before the reuse-vs-generate decision in Sprint 2 can be
    built).

3.  **Sprint 2** --- Groq generation + Pydantic validation + independent
    complexity (the core trust boundary of the whole system).

4.  **Sprint 3** --- Diagram-type detection + deterministic rendering
    (turns validated JSON into an actual image for the first time).

5.  **Sprint 4** --- Output validation + bounded repair (closes the
    \"success ≠ image exists\" gap).

6.  **Sprint 5** --- Full frontend wiring, real pipeline progress,
    persistent history (retires all remaining frontend mocks).

7.  **Sprint 6** --- Isolated Gemini creative path +
    security/concurrency hardening.

8.  **Sprint 7** --- Corner-case regression pass and demo readiness.

Do not parallelize Sprints 1--4 across team members working
independently on disconnected pieces --- the
reuse/generate/validate/render chain has tight sequential dependencies,
and building renderer or validation logic ahead of a stable
structured-JSON contract (finalized in Sprint 2) risks costly rework.
Sprint 5 (frontend wiring) and Sprint 6 (Gemini path + hardening) can
run partially in parallel across two pairs, since they touch largely
disjoint parts of the codebase once Sprint 4 is complete.
