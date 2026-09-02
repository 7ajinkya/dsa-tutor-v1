# V1 Slice 1C Plan — Vue Frontend (design only, implementation gated on approval)

| | |
|---|---|
| **Plan version** | 0.1.0 (draft — FOR REVIEW) |
| **Date** | 2026-09-03 |
| **Author** | AutoClaw |
| **Instruction source** | User authorization 2026-09-03: plan Slice 1C only, based on the **actual 1B implementation** |
| **Basis documents** | `docs/V1_SLICE_1_API_BOUNDARY_DESIGN.md` v1.2 (frozen contract) · `plans/V1_SLICE_1C_AUDIT.md` (live audit) · `plans/V1_SLICE_1C_API_CAPTURE.json` (28 real request/response payloads) |
| **Deliverable of Slice 1C** | A Vue 3 single-page frontend that renders the 1B API exactly |
| **Status rule** | **No Vue code, scaffolding, or dependency changes until this plan is reviewed and approved.** |

**Navigation:** [1 Objectives](#1-objectives--the-four-learner-questions) · [2 Scope](#2-scope-boundary) · [3 Real-API basis](#3-real-api-basis) · [4 Structure](#4-application-structure) · [5 Screens & wireframes](#5-screens--wireframes) · [6 State](#6-state-management) · [7 API client](#7-api-client-specification) · [8 Lifecycle](#8-session-lifecycle--flows) · [9 Interaction types](#9-activity-rendering-per-interaction-type) · [10 Theory](#10-theory-experience) · [11 Tone](#11-diagnostic-vs-instructional) · [12 step.why](#12-stepwhy-presentation) · [13 Sequences](#13-planned-vs-adaptive) · [14 Progress/Home](#14-progressive-home--progress) · [15 Hints/Reveal/Explain](#15-hintsrevealreveal-explain) · [16 Stale recovery](#16-stale-activity-recovery) · [17 States](#17-loadingerrorerror-empty-states) · [18 Resume](#18-session-resume--refresh) · [19 Responsive](#19-responsive-layout) · [20 Testing](#20-frontend-testing-strategy) · [21 Risks](#21-risks--exception-paths) · [22 Milestones](#22-implementation-milestones-for-slice-1c-after-approval) · [23 Reviewer pack](#23-reviewer-pack) · [24 Versioning](#24-versioning--change-log) · [A Orientation](#appendix-a--learner-orientation-traceability) · [B Payloads](#appendix-b--real-payload-excerpts)

---

## 1. Objectives — the four learner questions

Slice 1C turns the 1B API into a learner-facing Vue application. The acceptance-level design rule:
**every screen must answer all four questions with concrete UI elements** (traceability table:
Appendix A; verification: no blank cells).

| Question | Design principle |
|---|---|
| Where am I? | Every surface shows the session/skill/unit context and position (progress header, plan position, mastery state) |
| Why am I doing this? | Every activity/theory turn renders `step.why` + a plain-language `purpose` line (mode-aware) |
| What do I do now? | The current turn is always the single focal point; `available_actions` drives the visible controls |
| What happens next? | Post-action transitions render the authoritative next turn immediately + explain the transition via `step.why`; theory states the upcoming check count; home shows the plan preview |

Success definition: a learner can start, study, answer all 7 interaction types, use hints/reveal/explain,
recover from stale/refresh states, stop/resume, and always answer the four questions — without reading
any engine code.

## 2. Scope boundary

IN: Vue 3 SPA design (structure, routes, state, typed API client, per-type rendering, theory, tone,
step.why, sequences, progress/home, hints/reveal/explain, stale recovery, states, resume, responsive,
testing strategy) — all based on the live 1B API (audit + capture).

OUT (this plan produces design only): no Vue code/scaffolding/deps; no 1B API changes (discrepancies go
to the audit log); no hosting/CI-CD decisions (later slice); no new interaction types (future work);
no auth (1B contract has none).

## 3. Real-API basis

Everything in this plan is grounded in the live 1B implementation (commit `4c0da98`):

- **Live capture:** 28 requests/responses (`plans/V1_SLICE_1C_API_CAPTURE.json`) covering every endpoint
  and error path; status summary: 22 expected-success, 6 expected-error, 0 anomalies.
- **Audit:** `plans/V1_SLICE_1C_AUDIT.md` — conformance matrix (12/12 endpoints), session-flow walk,
  discrepancy log D-1…D-12 with rulings.
- **Interaction types the API actually serves today** (verified against the 75-exercise curriculum +
  live runs — nothing invented, nothing missing):

| Turn/interaction | `turn.type` / `activity.type` | `answer_format` | Where it occurs |
|---|---|---|---|
| Theory turn | `theory` | — (button instead) | start of every teach unit |
| Multiple choice | `activity`/`mcq` | `letter` | most checks (50 exercises) |
| Free-form explanation | `activity`/`free_form` | `text` | conceptual checks (6) |
| Output prediction | `activity`/`output_prediction` | `lines` | trace-then-predict (with `code`) |
| Code tracing | `activity`/`code_tracing` | `lines` | (with `code`) |
| Complexity question | `activity`/`complexity_question` | `big_o` | module F (with `kind`: sum/space) |
| Code writing | `activity`/`code_writing` | `code` | BFS/DFS implementation (with `starter`, `function_name`) |
| Graph construction | `activity`/`graph_construction` | `edges` | build-a-graph exercise (with `nodes`) |
| AI-generated remediation | `activity` (generated=true, `rem_*` id) | per generated type | after first failure (observed mcq-shaped) |
| Notice | `notice` | — | degraded AI, already-paused, info fallbacks |
| Ended | `ended` | — | learner stop / budget / curriculum complete |

## 4. Application structure

Stack (decision point D1): **Vue 3 (Composition API) + Vite + TypeScript + Pinia + Vue Router**;
styling: hand-rolled CSS custom properties (no component library — D3); testing: Vitest +
Vue Test Utils + Playwright (D5). Rationale: matches the approved direction; Pinia matches the
single-turn stateflow; no UI kit keeps the bundle small and the design contract-exact.

```
frontend/
  index.html  vite.config.ts  tsconfig.json  package.json
  src/
    main.ts  App.vue  router/index.ts
    api/
      client.ts        # fetch wrapper: base URL, JSON, errors -> ApiClientError{code,...}
      types.ts          # TurnEnvelope/Activity/SessionInfo/Step/Result/Hint... (from live capture)
      endpoints.ts      # typed functions per 1B endpoint (the only fetch call sites)
    stores/
      session.ts        # useSessionStore: session, turn, actions (start/answer/hint/...)
      learner.ts        # useLearnerStore: home dashboard, progress
      ui.ts             # useUiStore: toasts, stale-notice, confirm dialogs
    views/
      HomeView.vue      # /           dashboard: daily, plan preview, start/resume CTA, progress
      SessionView.vue   # /session/:id  renders the current turn (theory/activity/ended/notice)
      ProgressView.vue  # /progress     full qualitative mastery report
      NotFoundView.vue  # catch-all
    components/
      activity/         # one renderer per interaction type + ActivityDispatcher
      TheoryPanel.vue  WhyPanel.vue  StepBadge.vue  HintDrawer.vue
      RevealDialog.vue  ExplainPanel.vue  SessionHeader.vue  NoticeBanner.vue
      ResultCard.vue  DailyTarget.vue  PlanPreview.vue  MasteryBadge.vue
    composables/
      useTurn.ts        # turn dispatch helpers (available_actions -> handlers)
      useStaleRecovery.ts
```

Router map (D2): `/` (Home) · `/session/:id` (Session shell; turn type decides inner rendering)
· `/progress` · `/:pathMatch(.*)*` (404). Route guard: entering `/session/:id` with no loaded turn
triggers `GET /sessions/:id` (snapshot); 404/409 redirect to `/` with a toast.

## 5. Screens & wireframes

### 5.1 Home (`/`) — dashboard + entry point

```
+----------------------------------------------------------------------+
| DSA Tutor                                    [Progress]              |
+----------------------------------------------------------------------+
| Today                                   | Plan preview (planned)     |
| target 2/4 units  [][][][]  ~25 min     | 1. graph_definition (9)    |
| Overall mastery: 1/38 skills            | 2. vertices_edges (5) ...  |
| +------------------------------------+ | (question counts per unit) |
| | [Start new session]  [Resume 25m] | | next up: why this order -> |
| +------------------------------------+ | Why: prereq order (step.why|
+----------------------------------------+-----------------------------+
```

Data: `GET /home` (daily, plan, progress_summary, resume) + `GET /learner/progress` (states).
`Start` enabled only when `resume.available == false`; otherwise `Resume` CTA (observed 409
`SESSION_ALREADY_ACTIVE` otherwise — the UI prevents it, D-11 note).

### 5.2 Session shell (`/session/:id`) — renders the current turn

```
+----------------------------------------------------------------------+
| SessionHeader: [skill: What is a graph?] [unit 1/9] [mode: study]     |
|                 [step: advance · as planned] [~24 min] [Stop]        |
+----------------------------------------------------------------------+
| WhyPanel (collapsible, open on transitions):                          |
|   Why this step: "skill 'graph_definition' not yet mastered..."       |
+----------------------------------------------------------------------+
| ACTIVITY AREA (per type — MCQ shown):                                |
|   purpose: "Practice check on 'What is a graph?'"  [generated: no]    |
|   prompt: Which statement best describes a graph?                     |
|   ( ) A set of vertices connected by edges...                         |
|   ( ) A linear sequence of elements...                                |
|   [Answer]  [Hint] [Explain]                          [Reveal]        |
+----------------------------------------------------------------------+
| ResultCard (after answer): correct · score · feedback · answered_by   |
|           + auto-advanced next turn (authoritative, from server)      |
+----------------------------------------------------------------------+
| progress strip: mastery badge (skill) · position 1/2 · plan: adaptive |
+----------------------------------------------------------------------+
```

### 5.3 Theory screen (turn.type = theory)

```
+----------------------------------------------------------------------+
| SessionHeader (same)                                                  |
+----------------------------------------------------------------------+
| STUDY: "What is a graph?"                                             |
|   <theory text, reading-optimized, ≥ 16px, max 70ch>                 |
|   [I've read this — start the 2 quick checks]  (POST theory-seen)   |
+----------------------------------------------------------------------+
```

### 5.4 Ended screen (turn.type = ended)

```
+----------------------------------------------------------------------+
| Session complete / paused                                             |
| end_reason_code badge + end_reason_detail text                        |
| units completed: N · daily: 2/4                                       |
| [Back to Home]  (resume CTA if paused)                                |
+----------------------------------------------------------------------+
```

### 5.5 Hint drawer / Reveal dialog / Explain panel (overlays on the activity area)

```
HintDrawer (right side, <768: bottom sheet):            RevealDialog (confirm first):
| Hint 1/4 (kind: socratic)                             | "Revealing counts as assisted |
| text...                                               |  — you won't earn independent |
| [Next hint (2/4)] [Close]                             |  evidence for this exercise." |
                                                        | [Reveal anyway] [Cancel]      |
ExplainPanel (below prompt): "Why this task?" + explanation text (AI/builtin)
```

State machine per overlay: closed → loading → open → (exhausted → reveal CTA) → closed.

### 5.6 Notice & error surfaces

`turn.type = notice` renders as an inline banner (info | solution_revealed | ended kinds);
API errors render `ErrorBanner` (code + message + retry button when `retryable`) at the top of the
activity area; `STALE_ACTIVITY` is handled silently (auto-adopt, see §16) with a small toast.

## 6. State management

Pinia stores (D1). Convention: **server truth wins** — every mutation response replaces the stored
turn entirely (no optimistic merging of activity state; the only optimistic UI is disabling the
submit button while in flight).

- `useSessionStore`: `session: SessionInfo | null`, `turn: TurnEnvelope | null`,
  `status: idle|loading|ready|error`, actions: `start(pace)`, `resume(id)`, `stop(id)`,
  `theorySeen(id)`, `answer(id, activityId, answer, key)`, `hint(...)`, `reveal(...)`,
  `explain(...)`, `fetchSnapshot(id)`, `confidence(id, skill, rating)`. Each action calls
  `api/endpoints.ts` and then `this.turn = response.turn` (+ `this.result` handling).
- `useLearnerStore`: `home`, `progress`; actions `fetchHome()`, `fetchProgress()`.
- `useUiStore`: `toasts[]`, `staleAdopted: boolean`, `confirmState`.

Loading/error conventions: per-action `loading` flags in the session store (single in-flight mutation
at a time; buttons disabled while loading); errors raise `ApiClientError` → store catches →
`useUiStore` toast / ErrorBanner; `STALE_ACTIVITY` is intercepted before display (§16).

## 7. API client specification

Typed client generated from the **live capture** (`plans/V1_SLICE_1C_API_CAPTURE.json`), not from the
old document. Base URL: `import.meta.env.VITE_API_BASE` (dev default `http://127.0.0.1:8000`;
CORS origins already configured server-side for the Vite dev ports).

```ts
// src/api/types.ts (shapes verified against real 1B responses)
interface TurnEnvelope {
  type: "activity" | "theory" | "ended" | "notice";
  session: SessionInfo | null;
  step: { action: string; why: string[]; sequence: "planned" | "adaptive" } | null;
  notice: { kind: string; text: string } | null;
  activity: Activity | null;      // see §9: per-type public fields only
  theory: { unit: UnitRef; text: string; checks_upcoming: number } | null;
  result: Result | null;          // correct, score, feedback, confidence_signal,
                                  // misconception, answered_by, assisted, duplicate
  hint: { level: number; kind: string; text: string } | null;
  confidence_request?: { skill_id: string };
}
interface ErrorEnvelope { error: { code: ErrorCode; message: string; retryable: boolean;
                                   turn?: TurnEnvelope; activity?: Activity;
                                   resume?: string; session_id?: number } }
```

Endpoint functions (1:1 with 1B routes): `startSession(pace)`, `getSessionSnapshot(id)`,
`resumeSession(id)`, `stopSession(id, reason?)`, `theorySeen(id)`,
`answer(id, activityId, answer, idempotencyKey)`, `hint(id, activityId)`,
`revealSolution(id, activityId)`, `explain(id, activityId)`, `confidence(id, skillId, rating)`,
`progress()`, `home()`.

- **Idempotency:** `answer` generates `crypto.randomUUID()` when the learner submits and **reuses the
  same key for automatic retries** of that submission; a fresh intentional submission uses a new key
  (design §4.5; observed replay behavior C-04).
- **Error mapping (observed codes → UI):** `STALE_ACTIVITY` → adopt `error.turn`, toast "Skipped
  ahead — showing the current task"; `LADDER_EXHAUSTED` → hint drawer shows reveal CTA;
  `MISSING_IDEMPOTENCY_KEY`/`MALFORMED_JSON`/`VALIDATION_ERROR` → should not happen (client bug —
  report dialog); `SESSION_ALREADY_ACTIVE` → home shows resume; `SESSION_NOT_ACTIVE`/
  `SESSION_NOT_FOUND`/`SESSION_MISMATCH`/`ANOTHER_SESSION_ACTIVE` → redirect `/` + toast;
  `NO_SOLUTION` → inline info; `INVALID_PACE`/`INVALID_CONFIDENCE`/`UNKNOWN_SKILL` → client-side
  prevention + report dialog; `AI_UNAVAILABLE`/`STORAGE_UNAVAILABLE` (retryable 503) → modal with
  Retry; `CONFIG_ERROR`/`INTERNAL_ERROR` → error screen with home link.
- **Retry rule:** only `retryable: true` errors show an automatic Retry affordance; answer retries reuse
  the same key; everything else is user-initiated.
- **Session token handling:** none (no auth in V1) — single-user localhost; the client holds no
  credentials.

---

## 8. Session lifecycle & flows

Every flow below is annotated with the **observed real 1B behavior** it relies on (capture entry refs).

| Flow | Frontend behavior | Real 1B behavior relied on |
|---|---|---|
| **Start** (home CTA) | `POST /sessions {pace}` → render returned turn; navigate `/session/{id}`. If 409 `SESSION_ALREADY_ACTIVE` (should not happen — CTA is hidden), toast + offer resume link from `error.resume` | C-01 201; C-19 409 + resume link |
| **Resume** (home resume card) | `POST /sessions/{id}/resume` → 200 `resumed:true` renders turn; `resumed:false` (already active) renders snapshot silently | C-17 (paused→active); C-18 (no-op, zero writes) |
| **Theory** | theory turn renders study view; button `POST theory-seen` → render returned activity turn | C-02 (advance to first check) |
| **Theory-seen retry** | double-click/network retry: 200 no-op with authoritative current turn — client just re-renders (no duplicate state) | contract test 5; C-16 analog |
| **Answer** | `POST answer` with fresh `Idempotency-Key` → render `turn` + top-level `result` | C-03 (correct, advance) |
| **Answer retry (lost response)** | same key, same path → 200 replay `duplicate=true` + authoritative current turn; toast "Your answer was already recorded" | C-04 (replay, one attempt) |
| **Stale tab / multi-tab** | 409 `STALE_ACTIVITY` → **adopt `error.turn`** (replace stored turn), toast "Skipped ahead — showing the current task" | C-05 (409 + fresh turn payload) |
| **Refresh / reload (F5)** | app state is memory-only by design; router guard on `/session/:id` calls `GET /sessions/:id` (read-only snapshot, zero writes server-side) → learner continues exactly where they were | C-14 (snapshot 200); audit §1 (zero-write verified by test 27) |
| **Server restart mid-session** | mutations/get return the persisted truth via context reattach (targeting helper); if MySQL down → 503 `STORAGE_UNAVAILABLE` retry modal | targeting helper §4.13; C-14 |
| **Stop** | confirm → `POST stop` → ended/paused rendering; repeat stop is a 200 no-op (button already hidden) | C-15; C-16 (no-op) |
| **Session end (engine)** | ended turn renders summary + `end_reason_code` badge + detail; CTA home | §4.4/§5.1; C-15 shapes |
| **Budget exhaustion** | engine ends the session itself → ended turn arrives inside an answer response → same ended rendering | §5.1 ended handling |
| **Expiration/abandonment** | V1 has no server-side expiry; a paused session stays resumable (observed). Long-absence UX: home shows resume card with remaining minutes recomputed client-side | C-17; §7 lifecycle |

## 9. Activity rendering per interaction type

Common frame: `purpose` line → `prompt` → type-specific input → action bar (`available_actions`).
Loading: submit button spinner; disable double-submit. Error: ErrorBanner per §7 mapping.
Per type (input + validation + notes):

| type | Input UI | Client validation | Notes |
|---|---|---|---|
| `mcq` | radio list from `choices[{id,text}]`; keyboard 1-4/a-d | selection required before submit | `answer_format=letter`; only `choices` exposed (answer_id never sent — verified test 25) |
| `free_form` | multi-line textarea (4 rows) | non-empty encouraged (soft) | graded by rubric/AI; `answered_by` shown |
| `output_prediction` | `code` block (monospace, scroll-x) + single-line-per-row input | lines joined with `\n` | expected output never sent |
| `code_tracing` | same as prediction | | |
| `complexity_question` | text input with hint chip from `kind` ("sum"/"space") | normalization client-side display only (`O(V+E)` ≡ `O(N+M)` server-side) | |
| `code_writing` | `function_name` label + `starter` pre-filled code editor (textarea, monospace, tab=2 spaces) | non-empty | tests/solution stay server-side |
| `graph_construction` | node list chips + edge pair inputs (`A-B`) | pair format `X-Y` | `expected_edges` never sent |
| generated (`rem_*`) | rendered by its own type; amber "extra practice" badge (`generated=true`) | same | produced by the struggle ladder |
| theory | see §10 | | |
| notice/ended | banner/summary (see §5.6/5.4) | | |

Unknown future type (defensive): fallback card showing `purpose` + raw prompt + free-text answer with a
"report unsupported activity" note (risk R2) — never a crash.

## 10. Theory experience

- Reading-optimized: max-width 70ch, ≥ 16px, comfortable line-height; theory text from
  `turn.theory.text` (unit-bound).
- Read gate: single primary button "I've read this — start the N quick checks"
  (`checks_upcoming`) → `POST theory-seen`.
- Retry-safe: double-click harmless (observed no-op); scroll-through is not enforced (learner trust).
- Resume mid-theory: snapshot re-renders the same theory turn (unit context header shows position).
- `step.why` shown in the WhyPanel: "why this unit now" comes from the engine decision.

## 11. Diagnostic vs instructional

| mode (from `activity.mode`) | Visual treatment | Verbal framing |
|---|---|---|
| teach | "Study" badge, calm surface | "Here is the idea — read, then quick checks" |
| practice | "Practice check" badge, standard | "Quick check — shows what you can do" |
| assess | "Assessment" badge, stronger border | "This one counts as evidence" |
| apply | "Application" + problem tag | "Put it together — real problem" |
| remediation | "Extra practice" amber badge (generated) | "Smaller step to unblock — why: step.why" |
| prerequisite_revisit | "Back to a foundation" badge | "Earlier idea needs one more look — why: step.why" |
| repeat/variation | "Again"/"New variant" badge | "One more rep — why: step.why" |

The `purpose` line is always rendered verbatim above the prompt; badges are visual-only (never change
content). Both come from the server-projected `mode`/`purpose` — the frontend does not re-derive
diagnostic vs instructional (invariant: frontend renders engine truth).

## 12. step.why presentation

- WhyPanel placement: directly under the session header, collapsible.
- Default state: **expanded on transitions** (after answer/theory-seen/resume), collapsed on first
  render of a turn (the badge row summarizes).
- Content: `step.why` list items as bullet lines (engine-generated human sentences, observed:
  "skill 'graph_definition' not yet mastered (required dims: knowledge)"); action shown as a chip
  (`advance`), sequence as "as planned"/"adapted for you".
- Learner-facing rule: never translate engine why-strings; the engine already writes learner language
  (verified in captures).

## 13. Planned vs adaptive

- Home plan preview: labeled "as planned" (static preview, question counts are estimates).
- Per-step: `step.sequence` badge — "as planned" when `planned`, "adapted for you" when `adaptive`
  (remediation/revisit/difficulty shifts).
- When a deviation happens the WhyPanel explains it (the engine why says why) and the session header
  switches the sequence chip; the plan preview is never presented as a promise.

## 14. Progressive home & progress

- Home: daily target progress (n/m units), budget, mastery summary (m/38), plan preview with
  "next up" + why-line, Start/Resume CTA (mutually exclusive by state).
- Progress view: `GET /learner/progress` — per-skill rows: MasteryBadge (NOT_SEEN→INDEPENDENT
  colored chips), evidence count, module/section grouping; qualitative only (no percentages, per
  contract). Filter: module tabs; empty state before first session.
- Data: fetched on mount + after each ended turn; stale-while-revalidate optional (D3 decision).

## 15. Hints/reveal/explain

- Hint drawer: shows current `hint.{level,kind,text}`; "Next hint (n/4)" escalates; on
  `LADDER_EXHAUSTED` the drawer switches to the reveal CTA (observed behavior). Hint count chip on
  the button.
- Reveal: confirmation dialog warns "counts as assisted" (engine semantics: attempt can never be
  independent); after reveal the activity stays current with the solution shown in an inset and
  `available_actions` updated.
- Explain: panel under the prompt with the AI/builtin explanation; a small "answered by" note comes
  from `result.answered_by` only on results (explain text itself is provider-neutral).

## 16. Stale-activity recovery

Single handler (`useStaleRecovery`) wrapping all activity-scoped mutations:

1. Client submits with the current `activity.id` + fresh idempotency key.
2. On 409 `STALE_ACTIVITY`: replace `sessionStore.turn` with `error.turn` (authoritative), toast
   "Skipped ahead — showing the current task", **do not** re-submit automatically.
3. On 200 `result.duplicate=true`: toast "Your answer was already recorded" (lost-response retry).
4. Rationale from real 1B behavior: stale submissions are rejected server-side (evidence protection,
   audit D-4/D-5); replay is safe and idempotent (C-04).

## 17. Loading/error/empty states

| Surface | Loading | Error | Empty |
|---|---|---|---|
| Home | skeleton cards | ErrorBanner + Retry (home refetch) | n/a (always renders; resume hidden when unavailable) |
| Session shell | full-turn skeleton | ErrorBanner per §7; 503 retryable modal | notice turns render their message |
| Theory | skeleton text block | ErrorBanner | n/a |
| Activity input | submit spinner; buttons disabled | ErrorBanner; stale auto-adopt | n/a |
| Hint drawer | drawer spinner | LADDER_EXHAUSTED → reveal CTA | no hints yet → button only |
| Progress | skeleton rows | ErrorBanner + Retry | "No evidence yet — start a session" |

## 18. Session resume & refresh

- Reload on `/session/:id`: router guard → `GET /sessions/:id` snapshot (zero server writes, observed)
  → render authoritative current turn. If 409 `SESSION_NOT_ACTIVE`/`SESSION_MISMATCH` → redirect `/`.
- Resume entry: home resume card (`resume.available`) → `POST resume` → snapshot-or-advanced turn.
- No client persistence (localStorage) in V1: the server is the storage (single source of truth).
- Multi-tab: each tab follows the same contract; the stale guard makes the losing tab resync
  automatically (observed semantics). Recommended: single-tab per learner (note in UI help).

## 19. Responsive layout

Breakpoints: `≥1280` desktop (session: activity + WhyPanel side-by-side; home: two columns),
`1024–1279` (WhyPanel collapsible, home single column), `768–1023` (nav condenses, hint drawer
becomes overlay sheet), `<768` mobile (single column; bottom action bar for the activity; nav as
compact top bar; theory text full-width; code blocks horizontal scroll; touch targets ≥ 44px;
tables → stacked cards).

Per-screen: Home (cards stack), Session (header wraps; action bar sticky bottom on mobile), Theory
(read button full-width), Progress (module cards), overlays (full-screen sheets <768). Keyboard:
answer inputs focusable, MCQ radio natively keyboard-navigable, Enter submits where unambiguous.

## 20. Frontend testing strategy

Staged, with "done" per level:

- **L1 Unit (Vitest):** pure logic — api client (fetch mocked; error mapping; idempotency key reuse),
  stores (actions replace turn; stale handler; end-reason mapping). Mock-API phase: fixtures generated
  from `plans/V1_SLICE_1C_API_CAPTURE.json` (real payloads). Done = all client/store branches covered,
  error codes mapped 1:1.
- **L2 Component (Vitest + Vue Test Utils):** each renderer with mock api module — per interaction
  type: renders prompt/input, disables during submit, shows result/errors; WhyPanel/StepBadge/HintDrawer
  states; responsive classes present. Done = every component has render + interaction + error tests.
- **L3 E2E (Playwright) against the real 1B server** (`python -m dsa_tutor.api --offline`):
  full learner journeys — start→theory→answer→advance; wrong answer → remediation appears;
  hint ladder → exhaustion → reveal; stale recovery (two pages, advance in one, act in the other);
  stop/resume across reloads; 503 modal; CORS-negative check. Done = journeys pass on Chromium +
  WebKit, mobile viewport pass for the main journey.
- Regression gate for every 1C change: `pytest tests -q` (1B backend stays green: 120/4) + frontend
  suites green.

## 21. Risks & exception paths

| ID | Risk | L | I | Mitigation / containment | Rollback |
|---|---|---|---|---|---|
| R1 | API drift from the frozen contract during 1C implementation | M | H | Client types generated from the capture; contract tests pinned; changes require a plan revision | `git revert` of the 1C branch |
| R2 | Unknown/malformed activity type from the API (future types) | L | M | Fallback renderer + report dialog (§9); never crash | type added in a patch release |
| R3 | Contract violation discovered in 1B while implementing (e.g., replay edge) | L | H | Stop-and-report rule (same as 1A/1B); discrepancy log entry; fix belongs to a 1B patch | revert 1C commits touching api/ |
| R4 | Session interruption (browser crash, network) | H | M | Server-truth model + snapshot on reload + stale guard (all observed) | n/a (state is server-side) |
| R5 | CORS misconfiguration in dev/prod | M | M | Origins from env; explicit list; E2E CORS-negative test | revert env change |
| R6 | Scope creep into engine/backend changes | M | M | This plan fixes the boundary; discrepancies → audit log → reviewer | plan revision process (§24) |

## 22. Implementation milestones for Slice 1C (after approval)

| ID | Milestone | Content | Est. |
|---|---|---|---|
| C1 | Scaffold | Vite + Vue3 + TS + Pinia + Router project, lint, folder skeleton, env config | 0.5 h |
| C2 | API client | types from capture, fetch wrapper, endpoint functions, unit tests | 1.0 h |
| C3 | Stores | session/learner/ui stores + unit tests | 1.0 h |
| C4 | Home + Progress | dashboard, progress view, start/resume CTA logic | 1.0 h |
| C5 | Session shell + theory | SessionView, SessionHeader, WhyPanel, theory flow | 1.0 h |
| C6 | Activity renderers | dispatcher + 7 type renderers + result card | 2.0 h |
| C7 | Hints/reveal/explain | drawer, dialog, panel + exhaustion CTA | 1.0 h |
| C8 | Stale/recovery/resume | stale handler, reload guard, resume flows | 0.75 h |
| C9 | Responsive polish | breakpoints, mobile action bar, a11y pass | 0.75 h |
| C10 | E2E | Playwright journeys against the real 1B server | 1.0 h |

Total ≈ 10 h focused work (draft estimate; AI-executed, human-reviewed).

## 23. Reviewer pack

Approval checklist (tick to authorize Slice 1C implementation):

1. Stack confirmed: Vue 3 + Vite + TypeScript + Pinia + Vue Router; no UI kit (D1/D3).
2. Routes/paths confirmed (§4 router map) (D2).
3. All 11 realized endpoints + turn envelope accepted as the client contract (§3/§7 + audit).
4. Per-type rendering designs (§9) acceptable, including generated-remediation badge.
5. Theory experience (§10) and read-gate acceptable.
6. Diagnostic vs instructional treatment (§11) acceptable.
7. step.why presentation (§12) and planned/adaptive badges (§13) acceptable.
8. Stale-activity auto-adopt + duplicate toast semantics (§16) acceptable.
9. Loading/error/empty states (§17) and resume/refresh flows (§18) acceptable.
10. Responsive breakpoints (§19) and browser matrix (evergreen Chrome/Edge/Firefox/Safari) acceptable (D4).
11. Testing strategy (§20): staged levels, mock→real phases, Playwright (D5) acceptable.
12. UI language English (D6); open questions OQ-1…OQ-4 answered or defaulted.

Decision points: D1 stack · D2 router paths · D3 styling (hand-rolled CSS, no kit) · D4 browser matrix
(evergreen only) · D5 E2E tool (Playwright) · D6 UI language (English) · D7 audit items D-7 hardening
(now vs later).

Open questions: OQ-1 exact Vite dev port binding for CORS defaults (5173 assumed); OQ-2 code editor:
plain textarea (proposed) vs Monaco in 1C (recommend later); OQ-3 dark mode (recommend later);
OQ-4 screen-reader verbosity for why-panels (recommend standard aria-live).

## 24. Versioning & change log

Same scheme as the Slice 1A plan: 0.x drafts; 1.0.0 = approved (tag `plan-slice1c-v1.0.0`); one
consolidated revision per review round; every revision = one commit `plans(slice1c): v<ver> <summary>`
+ a change-log row here; prior versions stay diffable in git.

| Version | Date | Trigger | Corrections |
|---|---|---|---|
| 0.1.0 | 2026-09-03 | Initial draft from the live 1B audit + capture | all sections; submitted for review |

---

## Appendix A — Learner orientation traceability

Every screen × four questions → the concrete UI element that answers it. No blank cells.

| Screen / route | Where am I? | Why am I doing this? | What do I do now? | What happens next? |
|---|---|---|---|---|
| Home `/` | Daily target n/m, mastery m/38, resume card | Plan preview "next up" + why-ordered curriculum; daily adaptation note | Start / Resume CTA (single primary) | Plan preview shows the coming units + question estimates |
| Session shell (activity) `/session/:id` | SessionHeader: skill, unit k/n, position j/m, sequence chip, remaining minutes | Purpose line + mode badge + WhyPanel (`step.why`) | Activity prompt + input + `available_actions` buttons | After submit: ResultCard + the authoritative next turn renders; WhyPanel explains the transition |
| Theory (turn.type=theory) | Unit/skill header + position | "Study — prepares the N checks below" + WhyPanel | Theory text + "I've read this" gate button | "N quick checks" announced; next turn renders on gate |
| Ended (turn.type=ended) | Session summary: units completed, daily progress | `end_reason_code` badge + detail text | Back to Home / Resume CTA | Home plan preview shows what comes next |
| Notice (turn.type=notice) | Session header context retained | Notice text (engine message, e.g. degraded AI) | Follow notice; actions per `available_actions` | Next authoritative turn on the next action |
| Hint drawer open | Same activity context (drawer overlays) | Why: "stuck? take a smaller step — assistance is tracked" | Next-hint / close / reveal CTA on exhaustion | Ladder exhaustion → reveal offer |
| Reveal dialog | Same activity context | Why: evidence warning (assisted semantics) | Reveal anyway / Cancel | Solution inset + updated availability |
| Explain panel | Same activity context | "Connects this task to the idea" | Close / re-ask on new turns | No state change (pure read) |
| Progress `/progress` | Full mastery map (per skill/module) | Evidence counts show why each state holds | Filter modules; navigate home to act | Mastery progression over future sessions |
| 404 / error screen | "This page does not exist" + home link | n/a (never a learner surface in normal flow) | Home link | n/a |

## Appendix B — Real payload excerpts

Full capture: `plans/V1_SLICE_1C_API_CAPTURE.json` (28 entries). Excerpts (verbatim from the live run):

- Answer (new submission, `C-03`): `result.correct=true`, `result.answered_by="engine-deterministic"`,
  next `turn.activity.id="e002_vertices_edges"`, `step.sequence="planned"`.
- Replay (`C-04`): `result.duplicate=true`, same stored evaluation, current turn returned.
- Stale (`C-05`): 409 envelope carries the full authoritative `error.turn`.
- Hint (`C-06`): `turn.hint={level:1, kind:..., text:...}` with the same activity still current.
- Stop (`C-15`): `session.end_reason_code="learner_stop"`; retry `C-16` no-op.
- Resume (`C-17`): `resumed=true` with the exact pre-stop activity; retry `C-18` no-op.
