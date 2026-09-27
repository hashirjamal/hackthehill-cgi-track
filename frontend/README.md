# Northwind Triage: frontend

React, TypeScript, Vite and Tailwind CSS 4, with TanStack Query for the API. One page for each view, with a header
and a sidebar. Every page reads the reporting API (`GET /reports/...`) except the Simulator, which still runs a
preview calculation in the browser.

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173, forwards /api to the FastAPI server on port 8000
npm run build    # type-check and bundle
npm run lint
npm test         # unit tests (vitest)
```

Start the API first (`uvicorn app.main:app` from the repo root, with the database in `.env`). To call a server on
another address, set `VITE_API_URL` when building, or `API_PROXY_TARGET` for the dev server.

## Pages

| Route | View | API |
|---|---|---|
| `/worklist` | Open complaints, most urgent first. **Classify** the unclassified ones on the page | `/reports/worklist`, `POST /complaints/process` |
| `/cases`, `/cases/:id` | Search every complaint, and one case's full context (with **Classify this case**) | `/reports/cases`, `/reports/cases/{id}` |
| `/backlog` | Backlog by month and by any grouping | `/reports/backlog-flow`, `/reports/backlog-breakdown` |
| `/root-cause` | Estimated reads against billing and metering complaints, and backlog clusters | `/reports/root-cause`, `/reports/root-cause/clusters` |
| `/accounts` | Complaints per account, with repeats | `/reports/account-history` |
| `/profiles` | How closed cases of each type ended | `/reports/case-profiles` |
| `/classification` | Classifier results and AI agent activity | `/reports/agent-results`, `/reports/classifications/summary` |
| `/simulator` | What-if levers for time, cost and score (a preview calculation) | none yet |

## How the API is used

- `src/api/client.ts`: a fetch wrapper. It builds query strings, times out, and turns failures into an `ApiError`
  with a message a person can act on. Server details are shown for a rejected request (422, 404) and hidden for a
  server fault (500). `isRetryable` says whether trying again could help.
- `src/api/reports.ts`: one React Query hook for each endpoint. Every report query shares a key prefix, so one call
  refreshes them all after data changes. The previous page stays on screen while the next one loads.
- `src/api/queryClient.ts`: retries a server fault or an unreachable server twice, and a rejected request never.
  Once a load has failed for good, it shows an error toast. Queries that share a `meta.label` (the stat cards) become
  one toast, and Retry reloads all of them. Retry is only offered when it could help.
- Paging, sorting and filters are on the server. `src/hooks/useListParams.ts` keeps them in the URL, so a filtered
  view can be shared and the back button works. A page with two tables gives the second a `prefix`.
- `src/components/DataTable.tsx` takes a `server` prop (built by `lib/serverTable.ts`). It shows placeholders on the
  first load, dims the rows while the next page loads, and shows an error state with Try again, or an empty state.
  Stat cards and chart blocks have their own loading and error states (`StatCard`, `QueryState`).

## Toasts

`sonner`, styled in `src/lib/toast.tsx` (whitish card, soft shadow, no border, a coloured icon). Use the helpers in
`src/lib/notify.ts`: `toastError` (message from `userMessage`), `toastSuccess`, `toastLoading`, `toastInfo`. The
classify action shows "Classifying N complaints", which is replaced by a summary on success or an error on failure.

## Design

- Brand colour is a deep purple (`--color-brand`, purple-800), used for titles, links, buttons, stat numbers and
  charts. Page background is a gray tint and cards are a bit whitish (`--color-page`, `--color-card`). All three,
  plus the type scale and the font (Inter, self-hosted through `@fontsource-variable/inter`), are set at the top of
  `src/index.css`, so the look changes in one place. Use `text-brand`, `bg-brand` and so on, not raw purple classes.
- Text is a step bigger than Tailwind's defaults (`text-sm` is 15px). Stat numbers are `text-4xl`.
- Badges are soft tinted chips with a small dot (`components/Badge.tsx`).
- No borders anywhere, only rounded corners.

## Layout of the code

- `src/layout/`: app shell, header and sidebar. `src/nav.ts` lists the pages in the sidebar.
- `src/api/`: the client, the query client and the report hooks. `src/types.ts` holds the row types, which match the API.
- `src/components/`: cards, tables, badges, filter controls, charts and the loading and error pieces.
- `src/pages/`: one file per page. `src/constants.ts` holds the values the filters offer.
