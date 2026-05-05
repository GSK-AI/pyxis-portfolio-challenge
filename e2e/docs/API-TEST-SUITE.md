# API Test Suite Documentation

## Overview

This test suite provides comprehensive coverage for the Portfolio Simulator backend API endpoints with a focus on reusability, maintainability, and alignment with the frontend architecture. All tests use the same types and endpoint definitions as the frontend application.

## Test Structure

### Helper Files

#### `endpoints.ts`

Centralized endpoint definitions that mirror `frontend/lib/endpoints.ts`:

- Organized by domain (health, portfolios, projects, optimisation, bd_deals)
- Type-safe endpoint generation
- Consistent with frontend endpoint structure

Example:

```typescript
import { endpoints } from "../helpers/endpoints";

// Use endpoints in tests
makeAuthenticatedRequest("GET", endpoints.portfolios.list());
makeAuthenticatedRequest("GET", endpoints.portfolios.metrics(portfolioId));
```

#### `api-helpers.ts`

Provides reusable functions for API testing:

- `makeAuthenticatedRequest()` - Makes authenticated API calls with proper headers
- `assertStatusCode()` - Validates HTTP status codes
- `assertResponseIsArray()` - Validates array responses
- `assertHasProperty()` - Validates object properties
- `assertResponseBody()` - Custom response body validation
- `logResponse()` - Debugging helper

#### `portfolios.ts`

Portfolio-specific validation helpers using **frontend types** from `frontend/lib/definitions.ts`:

- `assertPortfoliosResponse()` - Validates `Portfolio` type structure
- `assertPortfolioMetrics()` - Validates `PortfolioMetrics` type (eNPV, NPV, eROI, etc.)
- `assertPortfolioProjectsResponse()` - Validates `PortfolioProjectCalls` type
- `assertPortfolioForecastResponse()` - Validates `PortfolioForecast` type

#### `test-data.ts`

Test data generators for creating test portfolios:

- `createTestPortfolio()` - Generate valid test portfolios
- `createInvalidPortfolio()` - Generate invalid data for negative tests
- `generatePortfolioName()` - Unique naming utility

## Test Coverage

### Health Check Tests (`01-health.cy.ts`)

Tests for backend health and availability:

1. **Basic Health Check**
   - ✅ Returns 200 status code
   - ✅ Returns correct response structure
   - ✅ Status is "ok"
   - ✅ Response time under 5 seconds
   - ✅ Consistent responses on multiple calls

2. **Root Endpoint**
   - ✅ Returns welcome message
   - ✅ Endpoint is accessible

### Portfolio Tests (`01-portfolio.cy.ts`)

Comprehensive tests for portfolio operations:

#### GET /portfolios

- ✅ Returns 200 status code
- ✅ Returns array of portfolios
- ✅ Validates structure of each portfolio
- ✅ Validates project_ids arrays
- ✅ Distinguishes published/unpublished portfolios
- ✅ Identifies edited portfolios

#### GET /portfolios/{portfolio_id}/projects

- ✅ Returns 200 for valid portfolio ID
- ✅ Returns valid projects structure

#### GET /portfolios/{portfolio_id}/metrics

- ✅ Returns 200 for valid portfolio ID
- ✅ Returns valid metrics (eNPV, eNP)

#### GET /portfolios/{portfolio_id}/forecast

- ✅ Returns 200 for valid portfolio ID
- ✅ Returns valid forecast structure

#### POST /portfolio/save

- ✅ Creates new portfolio with valid data
- ✅ Rejects portfolio with missing required fields

#### PUT /portfolios/{portfolio_id}/publish

- ✅ Publishes an unpublished portfolio

#### PUT /portfolios/{portfolio_id}/unpublish

- ✅ Unpublishes a published portfolio

#### PUT /portfolios/{portfolio_id}/delete

- ✅ Deletes an existing portfolio
- ✅ Returns error for non-existent portfolio

#### POST /portfolio/{portfolio_id}/update

- ✅ Updates portfolio name and description

#### Error Handling

- ✅ Handles invalid portfolio IDs gracefully
- ✅ Requires authentication for protected endpoints

## Running the Tests

### Run all API tests

```bash
cd e2e
npx cypress run --spec "cypress/e2e/00-api-tests/**/*.cy.ts"
```

### Run specific test file

```bash
npx cypress run --spec "cypress/e2e/00-api-tests/01-health.cy.ts"
npx cypress run --spec "cypress/e2e/00-api-tests/01-portfolio.cy.ts"
```

### Open Cypress UI

```bash
npx cypress open
```

## Best Practices

### Reusable Code

- All common API operations use helper functions from `api-helpers.ts`
- Portfolio-specific validations are centralized in `portfolios.ts`
- Avoid code duplication across test files

### Test Independence

- Each test should be able to run independently
- Tests clean up after themselves (delete created portfolios)
- Use `before()` and `beforeEach()` hooks for setup

### Assertions

- Use specific assertion helpers for better error messages
- Validate both status codes and response structure
- Log important information for debugging

### Error Handling

- Set `failOnStatusCode: false` when expecting errors
- Test both success and failure scenarios
- Validate error responses are meaningful

## Adding New Tests

### 1. Create a new test file

```typescript
import {
  makeAuthenticatedRequest,
  assertStatusCode,
} from "../helpers/api-helpers";

describe("New API Tests", () => {
  it("should test something", () => {
    makeAuthenticatedRequest("GET", "/endpoint").then((response) => {
      assertStatusCode(response, 200);
      // Add your assertions
    });
  });
});
```

### 2. Add new helper functions if needed

Add to `api-helpers.ts` or create a new helper file for domain-specific validations.

### 3. Update this README

Document the new tests and any new patterns introduced.

## Future Enhancements

### Potential additions

- [ ] Tests for BD Deal endpoints
- [ ] Tests for optimization endpoints
- [ ] Tests for Pareto frontier endpoints
- [ ] Tests for project endpoints
- [ ] Performance benchmarking tests
- [ ] Data validation tests with schemas
- [ ] Integration tests for complex workflows
- [ ] Load testing scenarios

## Maintenance Notes

- Keep helper functions generic and reusable
- Update TypeScript types when API contracts change
- Add comments for complex test scenarios
- Regular review of test coverage metrics
