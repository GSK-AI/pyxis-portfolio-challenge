/**
 * API Endpoints for E2E Testing
 * These mirror the endpoints defined in frontend/lib/endpoints.ts
 */

const getBaseEndpoint = () => Cypress.env("backendEndpoint");
const getGameBaseEndpoint = () =>
  Cypress.env("gameBackendEndpoint") || getBaseEndpoint();

// =============================================================================
// HEALTH ENDPOINTS
// =============================================================================

export const endpoints = {
  health: () => `${getBaseEndpoint()}/health`,
  clearCache: () => `${getBaseEndpoint()}/clear_cache`,
  root: () => `${getBaseEndpoint()}/`,

  // =============================================================================
  // PORTFOLIO ENDPOINTS
  // =============================================================================

  portfolios: {
    list: () => `${getBaseEndpoint()}/portfolios`,
    projects: (portfolioId: string) =>
      `${getBaseEndpoint()}/portfolios/${portfolioId}/projects`,
    metrics: (portfolioId: string) =>
      `${getBaseEndpoint()}/portfolios/${portfolioId}/metrics`,

    forecastPlots: (portfolioId: string, plotName: string) =>
      `${getBaseEndpoint()}/portfolios/${portfolioId}/forecast/${plotName}`,
    distribution: (portfolioId: string) =>
      `${getBaseEndpoint()}/portfolios/${portfolioId}/distribution`,
    save: () => `${getBaseEndpoint()}/portfolio/save`,
    update: (portfolioId: string) =>
      `${getBaseEndpoint()}/portfolio/${portfolioId}/update`,
    delete: (portfolioId: string) =>
      `${getBaseEndpoint()}/portfolios/${portfolioId}/delete`,
    publish: (portfolioId: string) =>
      `${getBaseEndpoint()}/portfolios/${portfolioId}/publish`,
    unpublish: (portfolioId: string) =>
      `${getBaseEndpoint()}/portfolios/${portfolioId}/unpublish`,
    combine: () => `${getBaseEndpoint()}/portfolios/combine`,
  },

  // =============================================================================
  // PROJECT ENDPOINTS
  // =============================================================================

  projects: {
    list: () => `${getBaseEndpoint()}/all_projects`,
    phases: () => `${getBaseEndpoint()}/all_project_phases`,
    details: (projectId: string) => `${getBaseEndpoint()}/project/${projectId}`,
    updatePtrsEffect: (projectId: string) =>
      `${getBaseEndpoint()}/project/${projectId}/view_update_ptrs_effect`,
    aiReport: (projectId: string) =>
      `${getBaseEndpoint()}/project/${projectId}/report`,
    fromIds: () => `${getBaseEndpoint()}/project/from_ids`,
    forecast: () => `${getBaseEndpoint()}/projects/forecast`,
    forecastPlots: (plotName: string) =>
      `${getBaseEndpoint()}/projects/forecast/${plotName}`,
    distribution: () => `${getBaseEndpoint()}/projects/distribution`,
  },

  // =============================================================================
  // OPTIMISATION ENDPOINTS
  // =============================================================================

  optimisation: {
    options: () => `${getBaseEndpoint()}/portfolio/optimise_options`,
    constraintOptions: () =>
      `${getBaseEndpoint()}/portfolio/optimise_constraint_options`,
    defaultOptions: () =>
      `${getBaseEndpoint()}/portfolio/default_optimise_options`,
    paretoFrontierOptions: () =>
      `${getBaseEndpoint()}/portfolio/default_pareto_frontier_options`,
    paretoFrontierPoints: () =>
      `${getBaseEndpoint()}/portfolio/frontier_points?ts=${Date.now()}`,
    optimise: () => `${getBaseEndpoint()}/portfolio/optimise`,
    paretoFrontier: () =>
      `${getBaseEndpoint()}/portfolio/pareto_frontier?ts=${Date.now()}`,
    paretoFrontierV2: () => `${getBaseEndpoint()}/portfolio/pareto_frontier_v2`,
  },

  // =============================================================================
  // BD DEALS ENDPOINTS
  // =============================================================================

  bdDeals: {
    options: () => `${getBaseEndpoint()}/portfolios/bd_deal_options`,
    defaults: (ta: string, pysValueType: string) =>
      `${getBaseEndpoint()}/portfolios/bd_deal_defaults?ta=${encodeURIComponent(
        ta,
      )}&pys_value_type=${encodeURIComponent(pysValueType)}`,
    predefined: () =>
      `${getBaseEndpoint()}/portfolios/predefined_bd_deal_defaults`,
    create: () => `${getBaseEndpoint()}/portfolios/new_bd_deal`,
    createFromPredefined: () =>
      `${getBaseEndpoint()}/portfolios/new_predefined_bd_deal`,
  },

  // =============================================================================
  // INVESTMENT GAME ENDPOINTS
  // =============================================================================

  investmentGame: {
    start: () => `${getGameBaseEndpoint()}/game/start`,
    step: (gameId: string) => `${getGameBaseEndpoint()}/game/${gameId}/step`,
    hint: (gameId: string, agentName?: string) => {
      const baseUrl = `${getGameBaseEndpoint()}/game/${gameId}/hint`;
      return agentName
        ? `${baseUrl}?agent_name=${encodeURIComponent(agentName)}`
        : baseUrl;
    },
    levels: () => `${getGameBaseEndpoint()}/game/levels`,
    leaderboardGlobal: () => `${getGameBaseEndpoint()}/game/leaderboard/global`,
    leaderboardLevels: (levelId: number) =>
      `${getGameBaseEndpoint()}/game/leaderboard/${levelId}`,
    agents: () => `${getGameBaseEndpoint()}/game/agents`,
    comparison: (gameId: string) =>
      `${getGameBaseEndpoint()}/game/${gameId}/comparison_dashboard`,
    highscore: (levelId: number) =>
      `${getGameBaseEndpoint()}/game/highscore/${levelId}`,
    customSeed: (numAssets: number) =>
      `${getGameBaseEndpoint()}/game/custom_seeds?initial_num_assets=${numAssets}`,
  },
};

/**
 * Helper to get endpoint by path notation
 * Example: getEndpoint('portfolios.list')
 */
export function getEndpoint(path: string, ...args: any[]): string {
  const parts = path.split(".");
  let current: any = endpoints;

  for (const part of parts) {
    if (current[part] === undefined) {
      throw new Error(`Endpoint not found: ${path}`);
    }
    current = current[part];
  }

  if (typeof current === "function") {
    return current(...args);
  }

  return current;
}
