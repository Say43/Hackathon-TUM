# osapiens Deforestation Monitor (Makeathon 2026)

Hackathon-ready frontend for the **osapiens** challenge: **multimodal satellite monitoring** for deforestation signals (Sentinel-1, Sentinel-2, AEF / foundation embeddings, weak labels) with **EUDR-oriented risk** and a **human validation** workflow.

Stack: **React**, **TypeScript**, **Vite**, **Tailwind CSS**, **lucide-react**, **recharts**. All data is **mock JSON** — no backend.

## Run

```bash
cd frontend
npm install
npm run dev
```

Open the URL shown (default `http://localhost:5173`).

```bash
npm run build   # typecheck + production bundle
npm run preview
```

## Layout

- **Left sidebar** — Overview, Land Plots, Time Series, Predictions, Risk Analysis, Validation  
- **Top bar** — Title `osapiens Deforestation Monitor`, search, tile selector, monitoring status (click to toggle), profile  
- **Main area** — page content  
- **Right panel (xl+)** — selected tile summary, risk breakdown, monitoring feed shortcuts  

Default route **Overview** is tuned for demo: large **map-style plot panel**, **risk summary**, **temporal preview**, **activity feed**, and **top detections**.

## Key files

| Path | Role |
|------|------|
| `src/data/mock.ts` | 12 land plots, overlays, time series generator, activity feed, validation queue metadata |
| `src/types/index.ts` | `LandPlot`, `TimeSeriesPoint`, `ActivityItem`, layers, nav keys |
| `src/components/PlotMapPanel.tsx` | Synthetic satellite workspace + overlay legend |
| `src/components/TimeSeriesChart.tsx` | Recharts multimodal timeline + change window + event markers |
| `src/components/RiskBreakdownPanel.tsx` | Enterprise-style risk breakdown + EUDR tier |
| `src/components/ValidationPanel.tsx` | HITL actions with mock feedback |
| `src/App.tsx` | Navigation, plot/region/layer state, insights panel |

## Challenge assets (repo root)

Reference notebooks and scripts (`challenge.ipynb`, `download_data.py`, `submission_utils.py`, description markdown) inform the **domain language** used in the UI; the frontend does not load those files at runtime.
