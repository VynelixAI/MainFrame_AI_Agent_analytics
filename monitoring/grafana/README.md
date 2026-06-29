# Grafana provisioning for Mainframe AI Copilot

Auto-loaded when the `grafana` service starts via Docker Compose.

## Layout

```
monitoring/grafana/provisioning/
├── datasources/
│   └── datasources.yml          # Prometheus datasource (http://prometheus:9090)
└── dashboards/
    ├── dashboards.yml           # File provider configuration
    └── mainframe-copilot-overview.json
```

## Access

| Item | Value |
|------|-------|
| URL | http://localhost:3000 |
| Username | `admin` |
| Password | `admin` (set via `GF_SECURITY_ADMIN_PASSWORD` in docker-compose.yml) |
| Dashboard folder | **Mainframe AI Copilot** |
| Dashboard name | **Mainframe AI Copilot Overview** |

## Panels

- **Service Health** — API and Prometheus `up` status, scrape duration
- **Investigations** — investigation count/rate and duration percentiles
- **HTTP** — request rate and p95 latency by endpoint

Metrics are exposed by the API at `GET /metrics` (Prometheus format).

## Customize

1. Edit `mainframe-copilot-overview.json` or create new JSON files in `dashboards/`
2. Restart Grafana: `docker-compose restart grafana`
3. Or edit live in the UI (provisioning allows UI updates)
