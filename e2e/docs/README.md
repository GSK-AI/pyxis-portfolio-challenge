# E2E Testing Documentation

This directory contains all documentation for the E2E testing setup.

## 🚀 Quick Start Guide

1. **Set up environment files**: Configure `e2e/.env` and `e2e/cypress/.env` files (contact FE engineers for values)
2. **Install dependencies**: Navigate to `e2e` directory and run `pnpm install`
3. **Install Cypress**: Run `pnpm cy:install`
4. **Launch Cypress**: Run `pnpm start` to authenticate and open the Cypress UI

## 📚 Documentation Files

### Setup Guides

- **[GITHUB-ACTIONS-SETUP.md](./GITHUB-ACTIONS-SETUP.md)** - Complete guide for setting up GitHub Actions CI/CD
- **[CI-SETUP-SUMMARY.md](./CI-SETUP-SUMMARY.md)** - Quick reference for CI setup

### Test Documentation

- **[API-TEST-SUITE.md](./API-TEST-SUITE.md)** - Comprehensive API test suite documentation
- **[UPDATES.md](./UPDATES.md)** - Summary of recent changes and improvements

## 🚀 Quick Start

1. **For GitHub Actions Setup**: Start with [CI-SETUP-SUMMARY.md](./CI-SETUP-SUMMARY.md)
2. **For Test Development**: See [API-TEST-SUITE.md](./API-TEST-SUITE.md)
3. **For Detailed CI Configuration**: Read [GITHUB-ACTIONS-SETUP.md](./GITHUB-ACTIONS-SETUP.md)

## 📋 What's Covered

### CI/CD Setup

- GitHub Actions workflow configuration
- Authentication setup for automated testing
- Backend service configuration options
- Secrets management and security

### Test Suite

- API endpoint testing patterns
- Helper functions and utilities
- Type safety with frontend integration
- Best practices and maintenance

### Architecture

- Frontend type integration
- Centralized endpoint management
- Reusable validation helpers
- Test data generation

All documentation is kept up-to-date with the latest changes and improvements to the E2E testing infrastructure.
