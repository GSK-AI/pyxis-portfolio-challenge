# API Tests

This directory contains the E2E API test suite.

## 📁 Test Files

- **`01-health.cy.ts`** - Health check and basic API availability tests
- **`01-portfolio-get.cy.ts`** - Comprehensive Portfolio GET API tests

## 📚 Documentation

For detailed documentation about the test suite, see:

- **[API Test Suite Documentation](../../docs/API-TEST-SUITE.md)** - Complete guide to the API tests
- **[E2E Documentation](../../docs/)** - All E2E testing documentation

## 🚀 Running Tests

```bash
# Run all API tests
npx cypress run --spec "cypress/e2e/00-api-tests/**/*.cy.ts"

# Run specific tests
npx cypress run --spec "cypress/e2e/00-api-tests/01-health.cy.ts"
npx cypress run --spec "cypress/e2e/00-api-tests/01-portfolio-get.cy.ts"
```

## 🔧 Test Helpers

Test helpers are located in `../helpers/`:

- `api-helpers.ts` - Common API testing utilities
- `endpoints.ts` - Centralized endpoint definitions
- `portfolios.ts` - Portfolio-specific validation helpers
- `test-data.ts` - Test data generators
