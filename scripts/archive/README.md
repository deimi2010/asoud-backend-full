# Archived backend utilities

Files below this directory are retained only for traceability. They are not
part of the canonical Docker runtime, production deployment path, CI test
suite, or supported operator workflow.

- `legacy-deployment/`: obsolete Gunicorn/systemd/root-Nginx deployment and
  monitoring helpers superseded by `docker-compose.production.yml`, Daphne,
  and `config/nginx/production.conf`.
- `legacy-data/`: one-off seed/admin scripts with old model assumptions or
  hard-coded container paths.
- `legacy-validation/`: standalone HTTP/performance/security scripts that are
  not deterministic regression tests and may target old endpoints or paths.
- `legacy-migration/`: temporary settings from the pre-reconciled migration
  workflow; never use it against production.

Do not execute an archived utility without reviewing its endpoints, paths,
credentials handling, and current model/API compatibility. Supported local
verification lives in Django test modules and the canonical Compose stack.
