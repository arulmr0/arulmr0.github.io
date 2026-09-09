# ADR-0003: Stateless JWT sessions with role-based access control

**Status**: accepted

## Context
Seven roles with clearly different permissions; clients are a browser SPA and possibly
future tablets at the counter.

## Decision
Password login returns an HS256 JWT containing the user id and role. Each route declares
the roles it accepts via `require_roles`. The user is re-loaded from the database on every
request so deactivating a user takes effect immediately even though tokens are stateless.

## Consequences
- No session table; horizontal scaling is trivial.
- Token lifetime is bounded (`HFS_ACCESS_TOKEN_MINUTES`); rotating the secret logs
  everyone out.
- Fine-grained permissions (per-outlet, per-department) can be added as extra claims later.
