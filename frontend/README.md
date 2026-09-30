# Outreach AI Cortex — Frontend

React + Vite + TypeScript + Tailwind CSS.

## Stack

- React 18
- Vite 5
- TypeScript 5
- Tailwind CSS 3
- react-force-graph-2d — graph visualization
- axios — HTTP

## Dev

Backend should listen on http://localhost:8080. Vite proxies `/api` there (`VITE_PROXY_TARGET` overrides the target, e.g. `http://api:8080` inside Compose).

```bash
cd frontend
npm install
npm run dev
```

UI: http://localhost:3000

## Prod

```bash
docker compose up -d frontend
```

nginx serves the Vite build on port 3000 and proxies `/api/` to `api:8080`.

## Layout

- `src/api/` — typed API modules
- `src/components/` — Layout, GraphView, UI primitives
- `src/pages/` — Dashboard, Companies, CompanyDetail, Persons, Graph, WarmIntro

## Add a page

1. Add a file under `src/pages/`
2. Register a `Route` in `src/App.tsx`
3. Add a `NavLink` in `src/components/Layout.tsx`
