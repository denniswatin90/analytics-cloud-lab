# DEW-style Analytics Cloud Lab

[![CI](https://github.com/denniswatin90/analytics-cloud-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/denniswatin90/analytics-cloud-lab/actions/workflows/ci.yml)

A hands-on project for a personalization and experimentation vendor. You play the vendor: generate experience data, load it into Snowflake, analyse A/B tests, share client-specific data through secure data sharing, and automate a daily experiment report in Python.

> The schema is a simplified teaching model (sessions, page views, variant assignments, conversions). It is **not** Dew's actual data dictionary and contains only synthetic data.

## What you'll practise
| Area | Skills |
| --- | --- |
| Snowflake core | Warehouses, credits, resource monitors, RBAC |
| Loading | Stages, file formats, `PUT`, `COPY INTO`, load history |
| SQL | `QUALIFY`, window functions, `MATCH_RECOGNIZE`, attribution logic |
| Semi-structured | `VARIANT`, path notation, `LATERAL FLATTEN` |
| Data sharing | Secure views, per-client row filtering with `CURRENT_ACCOUNT()`, shares, reader accounts |
| Pipelines | Streams, tasks, dynamic tables, time travel, clones |
| Python | Connector, key-pair auth, Snowpark, pandas, REST APIs with retries and pagination |
| Engineering | OOP (dataclasses, properties, context managers), logging, pytest, GitHub Actions |
| Analytics | Conversion lift, z-test, confidence intervals, experiment pitfalls |

## Repository layout
```
├── src/analytics_cloud_lab/
│   ├── config.py            # settings from env / .env (key-pair, SSO or password)
│   ├── snowflake_client.py  # context-managed connector wrapper
│   ├── generate_data.py     # deterministic synthetic data (CSV + JSONL)
│   ├── loader.py            # PUT + COPY INTO
│   ├── local_metrics.py     # offline reference implementation of the SQL logic
│   ├── experiment.py        # lift, z-test, confidence intervals, markdown report
│   ├── report.py            # CLI: daily experiment report (online/offline)
│   ├── snowpark_job.py      # same summary built with Snowpark DataFrames
│   └── api_client.py        # REST client with retries + pagination
├── sql/                     # 01–08: setup → load → analysis → sharing → pipelines → cost
├── tests/                   # pytest suite (runs without Snowflake)
├── docs/client-onboarding-guide.md
└── .github/workflows/ci.yml # lint + tests + offline smoke test
```

## Data model
| Table | Grain | Notes |
| --- | --- | --- |
| `EXPERIENCES` | experience | 3 experiences across 2 fictional retailers |
| `SESSIONS` | session | device, browser, country, client |
| `PAGE_VIEWS` | page view | home → category → product → cart → checkout |
| `OFFERS` | qualification | **contains duplicates on purpose** (practise `QUALIFY`) |
| `CONVERSIONS` | order | revenue, items |
| `EVENTS_RAW` | JSON event | page views and purchases with product arrays |

True effects built into the generator: EXP-001 +0.6 pp, EXP-002 +0.1 pp (hard to detect), EXP-003 +0.7 pp.

## Clean up
```sql
ALTER WAREHOUSE LAB_WH SUSPEND;
-- To remove everything:
-- DROP SHARE MAC_LAB_SHARE; DROP MANAGED ACCOUNT CLIENT_READER; DROP DATABASE MAC_LAB; DROP WAREHOUSE LAB_WH;
```

## License
MIT
