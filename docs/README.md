# Documentation map

The repository keeps only the project entry point (`README.md`) and the
tooling instructions (`CLAUDE.md`) at the root. All other Markdown documents
are grouped here by purpose.

These documents were written at different points in the project's history.
Names such as "complete", "final", or "100 percent" are historical titles,
not a statement about the current production-readiness of the service. Start
with the current audit documents below before relying on an older report.

## Current engineering state

- [Backend production-readiness audit](current/AUDIT.md)
- [Backend working notes](current/NOTES.md)
- [Infrastructure audit notes](current/INFRA_NOTES.md)

The current OpenAPI schema is generated and validated in CI and is not committed
at the repository root. Historical partial schemas and Postman samples are kept
under [legacy API artifacts](api/legacy-artifacts/README.md); they are not the
authoritative API contract.

## API and frontend integration

- [Hand-written API documentation](api/API_DOCUMENTATION.md)
- [API documentation progress](api/API_DOCUMENTATION_PROGRESS.md)
- [Endpoint validation report](api/ENDPOINT_VALIDATION_REPORT.md)
- [Frontend integration checklist](api/FRONTEND_CHECKLIST.md)
- [API delivery notes](api/README_DELIVERY.md)
- [Postman collection guide](api/ASOUD_API_Postman_README.md)
- [Postman collection analysis](api/POSTMAN_COLLECTION_ANALYSIS.md)
- [Postman collection report](api/POSTMAN_COLLECTION_REPORT.md)

## Security

- [Security audit quick summary](security/SECURITY_AUDIT_QUICK_SUMMARY.md)
- [Security audit report](security/SECURITY_AUDIT_REPORT.md)
- [Complete security audit report (Persian)](security/COMPLETE_SECURITY_AUDIT_REPORT_FA.md)
- [Round 2 security issues](security/ROUND_2_SECURITY_ISSUES.md)
- [Phase 1 security implementation](security/PHASE1_SECURITY_IMPLEMENTATION.md)
- [Product view security fixes](security/PRODUCT_VIEWS_SECURITY_FIXES.md)

## Deployment and infrastructure

- [Canonical production operations runbook](current/GROUP_1_OPERATIONS_RUNBOOK.md)
- [Production foundation plan](current/GROUP_1_PRODUCTION_FOUNDATION_PLAN.md)
- [Development environment guide](deployment/DEVELOPMENT_README.md)
- [Development security guide](deployment/DEVELOPMENT_SECURITY_GUIDE.md)
- [Dockerfile analysis](deployment/DOCKERFILE_CRITICAL_ANALYSIS.md)
- [Nginx analysis](deployment/NGINX_CRITICAL_ANALYSIS.md)
- [Redis analysis](deployment/REDIS_CRITICAL_ANALYSIS.md)
- [Database analysis](deployment/DATABASE_CRITICAL_ANALYSIS.md)

The deployment documents describe several conflicting paths. Do not treat one
as production-canonical until the live server runtime has been identified, as
explained in the current infrastructure notes.

## Architecture and data

- [Code documentation](architecture/CODE_DOCUMENTATION.md)
- [Database index migration guide](architecture/DATABASE_INDEX_MIGRATION_GUIDE.md)

## Analytics and machine learning

- [Analytics API documentation](analytics/ANALYTICS_API_COMPLETE_DOCUMENTATION.md)
- [Analytics and ML documentation](analytics/ANALYTICS_ML_DOCUMENTATION.md)
- [Analytics and ML quick reference](analytics/ANALYTICS_ML_QUICK_REFERENCE.md)

Analytics routes are currently disabled. These documents describe the legacy
surface and should not be read as an enabled production contract.

## Performance

- [Performance implementation](performance/PHASE2_PERFORMANCE_IMPLEMENTATION.md)
- [Performance final review](performance/PHASE2_FINAL_REVIEW.md)
- [Database optimization report](performance/PERFORMANCE_DATABASE_OPTIMIZATION_FINAL.md)
- [Optimization usage guide](performance/PERFORMANCE_OPTIMIZATION_USAGE_GUIDE.md)
- [Performance quick reference](performance/PERFORMANCE_QUICK_REFERENCE.md)
- [Performance architecture visual](performance/PERFORMANCE_ARCHITECTURE_VISUAL.md)
- [Optimization report](performance/OPTIMIZATION_REPORT_FINAL.md)
- [Performance completion report](performance/PERFORMANCE_DONE.md)

## Plans and ideas

- [Remaining phases plan](planning/REMAINING_PHASES_PLAN.md)
- [Phase 4 detailed plan](planning/PHASE4_DETAILED_PLAN.md)
- [AI ideas and roadmap](planning/AI_IDEAS_AND_ROADMAP.md)

## Historical reports

The following files are retained as project history. They may contain stale
counts, missing-file references, or completion claims superseded by the current
audit.

- [Final 100 percent completion](archive/FINAL_100_PERCENT_COMPLETION.md)
- [Status from October 24, 2025](archive/FINAL_STATUS_OCTOBER_24_2025.md)
- [Final API documentation summary](archive/FINAL_SUMMARY.md)
- [Phases 1 and 2 deep review](archive/PHASES_1_2_DEEP_REVIEW.md)
- [Phases 1 through 3 deep review](archive/PHASES_1_3_DEEP_REVIEW_FINAL.md)
- [Legacy main README](archive/README_MAIN.md)
- [Seed data fix report](archive/SEED_DATA_FIX_REPORT.md)
- [Ultimate deep review](archive/ULTIMATE_DEEP_REVIEW_FINAL.md)
- [Ultimate phases 1 and 2 review](archive/ULTIMATE_PHASES_1_2_REVIEW.md)
