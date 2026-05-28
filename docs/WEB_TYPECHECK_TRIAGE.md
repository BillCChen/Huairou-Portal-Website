# Web Typecheck Triage

## 1. Context

- Branch: codex/portal-baseline-attribution
- Relevant baseline commit: 0095e93
- Command: `pnpm check:web`
- Current status: FAIL, but the typecheck entrypoint is now valid.

## 2. Error Summary

Current `pnpm check:web` output contains 9 TypeScript errors and one Vue language plugin warning.

```text
nuxt.config.ts(7,16): error TS2591: Cannot find name 'process'.
pages/cases/index.vue(80,22): error TS2339: Property 'message' does not exist on type '{}'.
pages/cases/index.vue(80,45): error TS2339: Property 'detail' does not exist on type '{}'.
pages/index.vue(427,30): error TS2339: Property 'message' does not exist on type '{}'.
pages/index.vue(427,53): error TS2339: Property 'detail' does not exist on type '{}'.
pages/institutes/index.vue(21,22): error TS2339: Property 'message' does not exist on type '{}'.
pages/institutes/index.vue(21,45): error TS2339: Property 'detail' does not exist on type '{}'.
pages/news/index.vue(86,24): error TS2339: Property 'message' does not exist on type '{}'.
pages/news/index.vue(86,47): error TS2339: Property 'detail' does not exist on type '{}'.
```

Additional warning:

```text
[Vue] Load plugin failed: vue-router/volar/sfc-route-blocks
[Vue] Failed to create plugin TypeError: plugin is not a function
```

The warning does not currently produce the listed TS error locations, but it should be tracked because it indicates a Volar/plugin compatibility issue in the generated Nuxt typecheck environment.

## 3. Error Classification

| File | Error | Category | Root Cause | Business Logic Impact | Recommended Fix |
|---|---|---|---|---|---|
| `apps/web-portal/nuxt.config.ts` | `TS2591: Cannot find name 'process'` | Type declaration missing | The Nuxt config uses `process.env.NUXT_PUBLIC_API_BASE`, but the web project typecheck environment does not expose Node globals/types. | No direct business logic error. Runtime build already works; the failure is type environment coverage. | Prefer a minimal config-level type fix, such as adding the correct Node type availability for Nuxt config or replacing the global access with an explicitly typed Node process import if accepted by the Nuxt runtime. |
| `apps/web-portal/pages/cases/index.vue` | `TS2339: Property 'message'/'detail' does not exist on type '{}'` | API error object type narrowing insufficient | `useAsyncData` exposes `error`; template accesses `error.data?.message` and `error.data?.detail`, but `error.data` is inferred as `{}`. | No confirmed business field error. This is error rendering type safety, not case data rendering. | Use a local type guard or shared helper to safely extract API error text. |
| `apps/web-portal/pages/index.vue` | `TS2339: Property 'message'/'detail' does not exist on type '{}'` | API error object type narrowing insufficient | Homepage uses the same `error.data?.message/detail` pattern for news loading errors. | No confirmed business field error. It affects typechecking of fallback error display only. | Use the same local or shared helper instead of direct template access. |
| `apps/web-portal/pages/institutes/index.vue` | `TS2339: Property 'message'/'detail' does not exist on type '{}'` | API error object type narrowing insufficient | Institute list page accesses `error.data?.message/detail` while `error.data` remains `{}`. | No confirmed business field error. It affects error fallback display only. | Use the same local or shared helper instead of direct template access. |
| `apps/web-portal/pages/news/index.vue` | `TS2339: Property 'message'/'detail' does not exist on type '{}'` | API error object type narrowing insufficient | News list page accesses `error.data?.message/detail` while `error.data` remains `{}`. | No confirmed business field error. It affects error fallback display only. | Use the same local or shared helper instead of direct template access. |
| Generated Nuxt/Vue typecheck environment | `vue-router/volar/sfc-route-blocks` plugin load warning | Other | Nuxt-generated Vue compiler options reference a plugin shape that the installed Vue language tooling reports as invalid. | No direct business logic impact observed. It may reduce typecheck fidelity or produce noisy output. | Track separately after TS errors are resolved; avoid changing dependencies in P0 without explicit approval. |

## 4. Candidate Fix Strategy A: Minimal Type Fix

Goal: make `pnpm check:web` pass with the smallest scoped changes and without changing page behavior.

Suggested changes:

1. Address `process` typing in `apps/web-portal/nuxt.config.ts`.

   Possible low-impact approaches:

   - Add Node type availability for Nuxt config typechecking if the project accepts a config-only typing change.
   - Or import `process` from `node:process` and keep the same environment variable access.

   Runtime behavior should remain unchanged because the same `NUXT_PUBLIC_API_BASE` value and fallback URL would be used.

2. Replace direct page template access to `error.data?.message/detail` with safe error text extraction.

   Possible minimal approach:

   - Add a local helper in each affected page, such as a function that accepts `unknown` and returns `message`, `detail`, or fallback text only after object checks.
   - Keep the displayed fallback strings unchanged.

   Runtime behavior should remain effectively unchanged for normal cases. The only observable difference would be safer handling of unexpected error shapes.

Tradeoff:

- This strategy touches four pages and Nuxt config, but each change is local and narrow.
- It is appropriate for a P0-3e validation repair if the user authorizes type-only source edits.

## 5. Candidate Fix Strategy B: Centralized API Error Typing

Goal: provide one reusable error model for `usePortalApi.ts` and all page error rendering.

Suggested changes:

1. Define an `ApiErrorLike` or equivalent type in a shared web helper.
2. Define `getErrorMessage(error, fallback)` or similar helper.
3. Update pages so they no longer access `error.value.data.message` or template `error.data?.message` directly.
4. Reuse the helper in all current and future API-backed pages.

Potential implementation locations:

- `apps/web-portal/composables/usePortalApi.ts`, if the helper is API-specific.
- A separate web utility/composable, if the project wants generic error extraction.

Tradeoff:

- This strategy touches more pages or shared composable code.
- It creates a cleaner long-term convention and reduces future repeated type errors.
- It is better suited to P1 or a clearly scoped P0-3e if the objective is to standardize API error handling before further V1 work.

## 6. Recommended Next Step

Recommended next step: Strategy B for `P0-3e Web Typecheck Error Repair`, with tight scope.

Reasoning:

- Four pages have the same error access pattern, so a shared helper avoids duplicating local type guards.
- The fix can preserve runtime behavior by keeping current fallback text and extraction precedence.
- It establishes a reusable convention before P1 adds more API-backed pages.

For the `process` error, apply the smallest config-compatible typing fix in the same P0-3e task, but do not install dependencies unless separately authorized.

## 7. Non-goals

- No page behavior change.
- No API behavior change.
- No database/model change.
- No dependency installation.
