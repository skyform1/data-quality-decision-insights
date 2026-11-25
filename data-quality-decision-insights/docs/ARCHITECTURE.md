# Architecture

React/TypeScript upload UI → local FastAPI upload endpoint → local stored file and preview → analysis endpoint → pandas checks → typed analysis response → local JSON persistence → result view and Markdown report.

Backend: app/main.py provides upload, analysis, history, detail and report routes. app/services/analyzer.py holds analysis rules and recommendations. app/services/context.py implements header matching. app/models.py defines result contracts.

Frontend: Vite/React presentation retains the prior upload-to-history workflow. An optional key is held only in React state and attached to data requests. Reports are downloaded through the same key-protected API path.

Data storage: backend/runtime by default, configurable through DATA_INSIGHTS_DIR. No external storage integration, provider SDK or hosted account connection is included. Optional key protection is shared development access, not per-user authentication.

This edition adapts existing application code, replaces the sample and removes brand names, historical data, build caches, hard-coded confidence/ROI claims and hosting-specific dependencies. The original archive remains unchanged.

Potential later AI work: source-grounded explanations of confirmed findings, with numeric calculations remaining deterministic. No such adapter is implemented here.
