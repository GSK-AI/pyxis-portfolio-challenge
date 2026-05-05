# E2E Testing Suite

End-to-end testing suite for the Portfolio Simulator application using Cypress.

## 🚀 Quick Start

### Local Development

```bash
# Install dependencies
pnpm install

# Start authentication and open Cypress UI
pnpm start
```

### CI/CD

```bash
# Run tests in CI mode with automatic authentication
pnpm e2e:ci
```

## 📁 Directory Structure

```
e2e/
├── docs/                     # 📚 All documentation
│   ├── README.md
│   ├── GITHUB-ACTIONS-SETUP.md
│   ├── CI-SETUP-SUMMARY.md
│   ├── API-TEST-SUITE.md
│   └── UPDATES.md
├── cypress/
│   ├── auth/                 # 🔐 Authentication setup
│   │   ├── index.mjs         # Interactive OAuth flow
│   │   └── ci-auth.mjs       # CI authentication
│   ├── e2e/
│   │   ├── 00-api-tests/     # 🧪 API endpoint tests
│   │   └── helpers/          # 🛠️ Reusable test utilities
│   ├── fixtures/             # 📄 Test data and session files
│   └── support/              # 🔧 Cypress configuration
└── package.json              # 📦 Dependencies and scripts
```

## 📚 Documentation

All documentation is located in the [`docs/`](./docs/) directory:

- **[Setup Guide](./docs/GITHUB-ACTIONS-SETUP.md)** - GitHub Actions CI/CD setup
- **[Quick Reference](./docs/CI-SETUP-SUMMARY.md)** - CI setup summary
- **[API Tests](./docs/API-TEST-SUITE.md)** - API test suite documentation
- **[Updates](./docs/UPDATES.md)** - Recent changes and improvements

## 🧪 Test Coverage

### ✅ Health API (6 tests)

- API availability and performance checks
- Response structure validation

### ✅ Portfolio GET APIs (33 tests)

- Portfolio CRUD operations
- Metrics and forecasting endpoints
- Error handling and authentication
- Performance testing

### ✅ Investment Game APIs (75+ tests)

#### 🎮 Core Game APIs (25+ tests)

- Game start/step/levels endpoints
- Asset validation and game state consistency
- Performance and error handling

#### 👥 Social Features APIs (30+ tests)

- Global and level leaderboards
- Agent management and comparison dashboard
- Highscore tracking and cross-feature validation

#### 🔧 Utility APIs (20+ tests)

- Game hints (with/without agents)
- Custom seed generation
- Concurrent request handling and integration tests

**Total: 114+ comprehensive tests**

## 🛠️ Available Scripts

```bash
# Local development
pnpm start              # Auth + open Cypress UI
pnpm cy:auth            # Generate session only
pnpm cy:open            # Open Cypress UI only

# Running tests
pnpm e2e                # Auth + run all tests
pnpm e2e:run            # Run tests (requires existing session)
pnpm e2e:ci             # CI mode with auto auth

# Code quality
pnpm format             # Format code
pnpm format:check       # Check formatting
```

## 🔐 Authentication

### Local Development

Uses interactive OAuth flow - opens browser for Microsoft authentication.

### CI/CD

Uses non-interactive authentication with GitHub Secrets:

- `E2E_ID_TOKEN` (recommended)
- `E2E_CLIENT_ID` + `E2E_CLIENT_SECRET`

See [CI Setup Guide](./docs/CI-SETUP-SUMMARY.md) for details.

## 🏗️ Architecture

### Frontend Type Integration

Tests use the same TypeScript types as the frontend application from `frontend/lib/definitions.ts`:

- `Portfolio`
- `PortfolioMetrics`
- `PortfolioProjectCalls`
- `PortfolioForecast`

### Centralized Endpoints

Endpoint definitions mirror `frontend/lib/endpoints.ts` for consistency.

### Reusable Helpers

Modular helper functions for API testing, validation, and test data generation.

## 🎯 Next Steps

1. **Set up CI/CD**: Follow the [GitHub Actions setup guide](./docs/GITHUB-ACTIONS-SETUP.md)
2. **Add more tests**: Extend coverage to other API endpoints
3. **Monitor results**: Use automated reporting and artifacts

For detailed information, see the [documentation](./docs/).
