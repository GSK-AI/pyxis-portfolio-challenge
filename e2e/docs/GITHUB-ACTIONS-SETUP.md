# E2E Testing GitHub Actions Setup

This document explains how to set up GitHub Actions to automatically run E2E tests on every Pull Request.

## Overview

The E2E testing workflow (`e2e-tests.yml`) automatically runs when:

- A Pull Request is created or updated
- Changes are made to E2E tests, backend, or frontend code
- Manual workflow dispatch is triggered

## Authentication Setup

Since the E2E tests require authentication with Microsoft OAuth, you need to set up GitHub Secrets for CI authentication.

### Required GitHub Secrets

Go to your repository → Settings → Secrets and variables → Actions, and add these secrets:

1. **`E2E_CLIENT_ID`** - Your Microsoft Azure App Registration Client ID
2. **`E2E_CLIENT_SECRET`** - Your Microsoft Azure App Registration Client Secret
3. **`E2E_NEXTAUTH_SECRET`** - Secret key for NextAuth.js encryption
4. **`E2E_ID_TOKEN`** - (Recommended) Pre-generated ID token for testing

### Authentication Options

The CI authentication script supports three methods in order of preference:

#### Option 1: Pre-generated Token (Recommended)

Set the `E2E_ID_TOKEN` secret with a valid token that can be used for API calls.

```bash
# Example: Get a token manually and set as secret
E2E_ID_TOKEN=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6...
```

#### Option 2: Client Credentials Flow

If your Azure App Registration supports client credentials flow, set:

- `E2E_CLIENT_ID`
- `E2E_CLIENT_SECRET`

#### Option 3: Dummy Token (Fallback)

If no credentials are provided, a dummy token is created. This may cause tests to fail if real authentication is required.

## Backend Service Setup

Currently, the workflow assumes your backend is available at `http://localhost:8000`. You have several options:

### Option 1: External Backend

If you have a test backend deployed somewhere, update the `CYPRESS_backendEndpoint` in the workflow:

```yaml
env:
  CYPRESS_backendEndpoint: https://your-test-backend.example.com
```

### Option 2: Docker Service

Uncomment and configure the services section in the workflow:

```yaml
services:
  backend:
    image: your-backend-image:latest
    ports:
      - 8000:8000
    env:
      # Backend environment variables
    options: --health-cmd="curl -f http://localhost:8000/health || exit 1" --health-interval=30s --health-timeout=10s --health-retries=3
```

### Option 3: Start Backend in Workflow

Add steps to build and start your backend:

```yaml
- name: Start Backend
  run: |
    # Build and start your backend
    cd ../aiml_portfolio_simulator
    # Add your backend startup commands here
    python -m uvicorn main:app --host 0.0.0.0 --port 8000 &

    # Wait for backend to be ready
    timeout 60 bash -c 'until curl -f http://localhost:8000/health; do sleep 2; done'
```

## Manual Workflow Trigger

The workflow can be triggered manually from the GitHub Actions tab with the following parameters:

### Input Parameters

1. **User Authentication Token** (optional)
   - Provide a valid user token for authentication
   - If not provided, uses the `E2E_ID_TOKEN` secret
   - To get a valid token: Run `pnpm cy:auth` locally, then copy the token from `cypress/fixtures/session.json`

2. **Backend URL** (optional)
   - Override the default backend endpoint
   - Defaults to: `https://rdfn-portfolio-be-dev-001.rd-iase-devtest-us6.appserviceenvironment.net`

3. **Test Suite** (optional)
   - `all`: Run all E2E tests (default)
   - `api-only`: Run only API tests (00-api-tests/\*)
   - `health-only`: Run only health check tests

### How to Run Manually

1. Go to **Actions** tab in GitHub
2. Click **E2E Tests** workflow
3. Click **Run workflow** button
4. Fill in the optional parameters:
   - Paste your user token (from local `cypress/fixtures/session.json`)
   - Select test suite if needed
5. Click **Run workflow**

### Getting a Valid User Token

```bash
cd e2e
pnpm cy:auth  # This opens browser for interactive login
# After login, copy the id_token from cypress/fixtures/session.json
```

## Workflow Features

### ✅ What the workflow does

- Installs Node.js and pnpm
- Installs E2E test dependencies
- Creates authentication session for testing
- Runs code formatting checks
- Executes all E2E tests
- Uploads test results and artifacts
- Comments on PR with test results

### 📊 Test Results

- Screenshots and videos are uploaded as artifacts
- Test reports are generated and stored
- PR comments show pass/fail status

### 🔧 Available Scripts

- `pnpm e2e:ci` - Run E2E tests with CI authentication
- `pnpm cy:auth:ci` - Generate CI authentication session only
- `pnpm format:check` - Check code formatting

## Local Development

For local development, continue using the interactive authentication:

```bash
# Local development (with browser OAuth)
pnpm start

# Or step by step
pnpm cy:auth  # Opens browser for authentication
pnpm cy:open  # Opens Cypress UI
```

## Troubleshooting

### Authentication Issues

1. Verify all required secrets are set in GitHub
2. Check that your Azure App Registration allows the authentication method
3. For client credentials flow, ensure proper permissions are granted

### Backend Connection Issues

1. Verify the backend is accessible at the configured endpoint
2. Check health endpoint returns 200 status
3. Ensure proper CORS configuration if needed

### Test Failures

1. Check uploaded artifacts for screenshots/videos
2. Review test logs in GitHub Actions
3. Verify environment variables are correctly set

### Secrets Not Available Error

The lint warnings about invalid secrets are normal - they just indicate the secrets haven't been configured yet in your repository.

## Security Considerations

- Never commit real credentials to the repository
- Use least-privilege principles for service accounts
- Regularly rotate authentication tokens
- Consider using environment-specific test accounts

## Next Steps

1. Set up the required GitHub Secrets
2. Configure your backend service approach
3. Test the workflow by creating a Pull Request
4. Monitor and adjust based on your specific needs

The workflow is now ready to provide automated E2E testing for every Pull Request! 🚀
