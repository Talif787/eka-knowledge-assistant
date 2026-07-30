# Configuration

All configuration is read from environment variables with the `EKA_` prefix and
validated at startup (the process fails fast on invalid config).

| Variable                | Default                                             | Description                          |
|-------------------------|-----------------------------------------------------|--------------------------------------|
| EKA_ENVIRONMENT         | development                                         | development / staging / production   |
| EKA_LOG_LEVEL           | INFO                                                | Log level                            |
| EKA_DATABASE_DSN        | postgresql+asyncpg://eka:eka@localhost:5432/eka     | Async Postgres DSN                   |
| EKA_DATABASE_POOL_SIZE  | 10                                                  | Connection pool size (1-100)         |
| EKA_DATABASE_ECHO       | false                                               | Echo SQL (debug only)                |
| EKA_OTLP_ENDPOINT       | (unset)                                             | OTLP gRPC endpoint for traces        |
| EKA_API_ROOT_PATH       | (empty)                                             | Root path when served behind a proxy |

In non-development environments logs are emitted as JSON. Secrets (database
credentials, provider keys) are injected from the environment and, in production,
sourced from a secrets manager rather than committed files.
