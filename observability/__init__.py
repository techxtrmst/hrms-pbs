"""
Observability - First-party error tracking and monitoring for Django.

A comprehensive solution similar to Sentry but as a first-party component.
Provides:
- Exception tracking with full stack traces
- Request/response logging
- Performance metrics (response time, SQL queries)
- Admin interface for log analysis
"""

default_app_config = "observability.apps.ObservabilityConfig"
