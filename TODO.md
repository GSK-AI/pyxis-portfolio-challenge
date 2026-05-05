# TODO: Deployment Cleanup

Items to address before handing off to RY for Azure hosting.

## CORS Origins

The CORS origins list in `app/app.py` (lines 81-93) is hardcoded with GSK-internal URLs. These need to be replaced with RY's deployment URLs, or made configurable via an environment variable (e.g., `APP_CORS_ORIGINS`).

## CSP / Security Headers

`app/middleware.py` `SecurityHeadersMiddleware` builds Content Security Policy headers using URL settings from `app/settings.py` — these are all GSK-internal:

- `dev_url`: `https://*.rd-iase-devtest-us6.appserviceenvironment.net`
- `uat_url`: `https://*.rd-iase-uat-us6.appserviceenvironment.net`
- `prod_url`: `https://*.rd-iase-prod-us6.appserviceenvironment.net`
- `main_url`: `https://pyxis.gsk.com`

Replace with RY's domains or make them configurable. The `docs_cdn` and `docs_api` settings are fine (public CDN / FastAPI docs).

## Auth (if access control is needed)

The app currently uses a simple session cookie (UUID) with no login required — anyone can play. If RY needs to restrict access:

- **Recommended**: Use Azure App Service Authentication ("Easy Auth") as a reverse proxy. It handles Entra ID login and injects user identity via `X-MS-CLIENT-PRINCIPAL-NAME` headers.
- **App change needed**: Update `SessionMiddleware` in `app/middleware.py` to read identity from the Easy Auth header instead of generating a random UUID.

## Game Assets

`app/settings.py` defaults `game_assets_dir` to `rl-environment-assets/`. RY needs to ensure this directory is populated with the generated asset data on the deployed instance, or configure it to point to the correct location.

## Redis

The app expects a Redis instance. Settings in `app/settings.py`:
- `redis_host` (default: `localhost`)
- `redis_port` (default: `6379`)
- `use_local_redis` (default: `True`)

For Azure, set `APP_USE_LOCAL_REDIS=0` and configure `APP_REDIS_HOST` / `APP_REDIS_PORT`. The `create_azure_redis_client()` in `app/redis_cache.py` supports password-based auth via the `password` parameter — RY will need to pass the Azure Redis access key.

## Pre-existing Test Failures

Several tests fail due to a missing `rd_capacity_config` parameter in test fixtures — this is unrelated to the cleanup work and predates it:
- `tests/agents/test_utils.py` — `json_game_state_factory` fixture doesn't pass `rd_capacity_config`
- `tests/environment/test_training_gym.py` — `_make_env` helper missing `rd_capacity_config`
- `tests/game/test_game_state.py` — some tests affected
- `tests/app/test_app.py::test_start_game` — `assert_called_once_with` doesn't match new kwargs passed to `initialise_new_game`
