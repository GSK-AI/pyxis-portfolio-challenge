/**
 * Test data generators and fixtures for E2E tests
 */

/**
 * Generates a unique portfolio name for testing
 */
export function generatePortfolioName(
  prefix: string = "Test Portfolio",
): string {
  return `${prefix} ${Date.now()}`;
}

/**
 * Creates a valid portfolio object for testing
 */
export function createTestPortfolio(
  overrides?: Partial<{
    portfolio_name: string;
    portfolio_description: string;
    project_ids: string[];
  }>,
) {
  return {
    portfolio_name: generatePortfolioName(),
    portfolio_description: "Created by automated E2E tests",
    project_ids: [],
    ...overrides,
  };
}

/**
 * Creates an invalid portfolio object for negative testing
 */
export function createInvalidPortfolio(
  type:
    | "missing_name"
    | "missing_description"
    | "missing_project_ids"
    | "empty_name",
) {
  const base = {
    portfolio_name: "Test Portfolio",
    portfolio_description: "Test Description",
    project_ids: [],
  };

  switch (type) {
    case "missing_name":
      const { portfolio_name, ...withoutName } = base;
      return withoutName;
    case "missing_description":
      const { portfolio_description, ...withoutDesc } = base;
      return withoutDesc;
    case "missing_project_ids":
      const { project_ids, ...withoutProjects } = base;
      return withoutProjects;
    case "empty_name":
      return { ...base, portfolio_name: "" };
    default:
      return base;
  }
}

/**
 * Common test project IDs (if available in your test environment)
 */
export const TEST_PROJECT_IDS = {
  // Add your test project IDs here if you have specific ones
  SAMPLE_PROJECT_1: "test-project-1",
  SAMPLE_PROJECT_2: "test-project-2",
};

/**
 * Common test constants
 */
export const TEST_CONSTANTS = {
  MAX_RESPONSE_TIME: 5000, // 5 seconds
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000, // 1 second
};
