# Authentication and multi-tenancy

Every `/v1` endpoint except the dev token endpoint requires a bearer token. The
tenant the request operates on is taken from the verified token, not from a
client header, so tenant isolation is proven rather than asserted. This replaces
the `X-Tenant-ID` placeholder used in earlier phases.

## How a request is authenticated

1. The client sends `Authorization: Bearer <jwt>`.
2. `get_current_identity` verifies the token (signature, expiry, issuer, required
   claims) and returns an `AuthenticatedIdentity` (tenant, subject, roles).
3. `get_tenant_id`, which every router already used, now returns
   `identity.tenant_id`. No router changed; the tenant source did.

A missing or invalid token raises `AuthenticationError`, which the API maps to
401.

## Tokens

Tokens are JWTs signed with HS256 and a shared secret, which is adequate for
development. The `TokenVerifier` and `TokenIssuer` ports let a production
deployment swap in RS256 with a JWKS endpoint from a real identity provider
(Auth0, Cognito, Keycloak) without changing any caller.

Claims: `iss` (issuer), `sub` (subject), `tid` (tenant id), `roles`, `iat`, `exp`.
The tenant claim is validated as a UUID at verification time.

## The dev token endpoint

`POST /v1/auth/token` mints a signed token and stands in for a real identity
provider. It is enabled by `EKA_AUTH_DEV_TOKEN_ENABLED` (default true in
development) and responds 404 when disabled, so it is not advertised in
production. A real deployment sets it false and relies on its IdP.

Request body: `{"tenant_id": "<uuid>", "subject": "alice", "roles": ["admin"]}`.
Response: `{"access_token": "...", "token_type": "bearer", "expires_in": 3600}`.

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| EKA_JWT_SECRET | dev-secret-change-me | HS256 signing secret. Override in production. |
| EKA_JWT_ALGORITHM | HS256 | Signing algorithm |
| EKA_JWT_ISSUER | eka | Expected `iss` claim |
| EKA_JWT_ACCESS_TTL_SECONDS | 3600 | Token lifetime |
| EKA_AUTH_DEV_TOKEN_ENABLED | true | Whether the dev token endpoint is served |

## Roles

The identity carries roles, and `AuthenticatedIdentity.has_role` is available for
route-level authorization. This phase enforces tenant isolation; finer-grained
role and attribute checks (and retrieval-time per-principal ACLs) build on this
foundation.

## What this does not cover yet

Token issuance in production (delegated to a real IdP), refresh tokens, and
per-document ACLs beyond tenant scoping. The verification path and the identity
model are in place for those to build on.
