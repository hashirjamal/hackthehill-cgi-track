# Northwind Triage: frontend

React, TypeScript, Vite and Tailwind CSS 4. One page for each view, with a header and a sidebar.
**It shows sample data only.** Nothing calls the API yet, so the filters are not connected either.

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
npm run build    # type-check and bundle
npm run lint
```

## Pages

| Route | View |
|---|---|
| `/worklist` | Open complaints, most urgent first |
| `/cases`, `/cases/:id` | Search every complaint, and one case's full context |
| `/backlog` | Backlog by month and by group |
| `/root-cause` | Estimated reads against billing and metering complaints |
| `/accounts` | Complaints per account, with repeats |
| `/profiles` | How closed cases of each type ended |
| `/classification` | Classifier results and AI agent activity |
| `/simulator` | What-if levers for time, cost and score (a preview calculation for now) |

## Design

- Primary colour is `text-purple-600`. Page background is a gray tint and cards are a bit whitish, both set as
  `--color-page` and `--color-card` in `src/index.css`, so the look changes in one place.
- No borders anywhere, only rounded corners.

## Layout of the code

- `src/layout/`: app shell, header and sidebar. `src/nav.ts` lists the pages in the sidebar.
- `src/components/`: `Card`, `StatCard`, `DataTable` (sorting and paging in the browser for now), `Badge`, the
  filter controls and the charts.
- `src/pages/`: one file per page.
- `src/mock.ts` and `src/types.ts`: sample data. The row types match the reporting API in `app/reports/`, so a page
  can switch from `mock.ts` to a fetch without changing its columns.

## Connecting the API

The reporting API runs on port 8000 (`uvicorn app.main:app`). Each list endpoint takes `page`, `page_size`, `sort`
and filters (see the main README). When wiring a page, sorting, paging and filtering move to the server, and
`DataTable` takes them as props.
