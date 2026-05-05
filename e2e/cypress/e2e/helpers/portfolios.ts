// Import types from frontend
import type {
  Portfolio,
  PortfolioMetrics,
  PortfolioProjectCalls,
  PortfolioForecast,
} from "../../../../frontend/lib/definitions";

/**
 * Validates the structure of a portfolio response object
 */
export function assertPortfoliosResponse(portfolio: Portfolio) {
  // Required string fields
  expect(portfolio).to.have.property("user_id");
  expect(portfolio.user_id).to.be.a("string");
  expect(portfolio.user_id).to.not.be.empty;

  expect(portfolio).to.have.property("session_id");
  // session_id can be null, undefined, or string
  if (portfolio.session_id) {
    expect(portfolio.session_id).to.be.a("string");
  }

  expect(portfolio).to.have.property("portfolio_id");
  expect(portfolio.portfolio_id).to.be.a("string");
  expect(portfolio.portfolio_id).to.not.be.empty;

  expect(portfolio).to.have.property("portfolio_name");
  // portfolio_name can be null or string
  if (portfolio.portfolio_name !== null) {
    expect(portfolio.portfolio_name).to.be.a("string");
  }

  expect(portfolio).to.have.property("portfolio_description");
  // portfolio_description can be null or string
  if (portfolio.portfolio_description !== null) {
    expect(portfolio.portfolio_description).to.be.a("string");
  }

  // Required numeric field
  expect(portfolio).to.have.property("ts");
  expect(portfolio.ts).to.be.a("number");

  // Required array field
  expect(portfolio).to.have.property("project_ids");
  expect(portfolio.project_ids).to.be.an("array");

  // Required boolean fields
  expect(portfolio).to.have.property("edited");
  expect(portfolio.edited).to.be.a("boolean");

  expect(portfolio).to.have.property("published");
  expect(portfolio.published).to.be.a("boolean");
}

/**
 * Validates the structure of portfolio metrics response
 */
export function assertPortfolioMetrics(metrics: PortfolioMetrics) {
  expect(metrics).to.be.an("object");

  // Key financial metrics
  expect(metrics).to.have.property("enpv");
  expect(metrics.enpv).to.be.a("number");

  expect(metrics).to.have.property("npv");
  expect(metrics.npv).to.be.a("number");

  expect(metrics).to.have.property("eroi");
  expect(metrics.eroi).to.be.a("number");

  expect(metrics).to.have.property("roi");
  expect(metrics.roi).to.be.a("number");

  // Sales metrics
  expect(metrics).to.have.property("esales_2031");
  expect(metrics.esales_2031).to.be.a("number");

  expect(metrics).to.have.property("sales_2031");
  expect(metrics.sales_2031).to.be.a("number");

  // Cost metrics
  expect(metrics).to.have.property("remaining_dev_ecosts");
  expect(metrics.remaining_dev_ecosts).to.be.a("number");

  expect(metrics).to.have.property("remaining_dev_costs");
  expect(metrics.remaining_dev_costs).to.be.a("number");

  // Risk metrics
  expect(metrics).to.have.property("npv_outcome_mean");
  expect(metrics.npv_outcome_mean).to.be.a("number");

  expect(metrics).to.have.property("npv_outcome_var");
  expect(metrics.npv_outcome_var).to.be.a("number");

  expect(metrics).to.have.property("npv_outcome_stdev");
  expect(metrics.npv_outcome_stdev).to.be.a("number");
}

/**
 * Validates the structure of a portfolio projects response
 */
export function assertPortfolioProjectsResponse(
  response: PortfolioProjectCalls,
) {
  expect(response).to.be.an("object");
  expect(response).to.have.property("projects");
  expect(response.projects).to.be.an("array");

  if (response.projects.length > 0) {
    const project = response.projects[0];
    expect(project).to.have.property("project_id");
    expect(project.project_id).to.be.a("string");
    expect(project).to.have.property("Name");
    expect(project.Name).to.be.a("string");
  }

  // Budget tracking data is optional
  if (response.budget_tracking_data) {
    expect(response.budget_tracking_data).to.have.property("years");
    expect(response.budget_tracking_data.years).to.be.an("array");
    expect(response.budget_tracking_data).to.have.property("budgets");
    expect(response.budget_tracking_data.budgets).to.be.an("array");
  }
}

/**
 * Validates the structure of a portfolio forecast response
 */
export function assertPortfolioForecastResponse(response: PortfolioForecast) {
  expect(response).to.be.an("object");

  // Spider diagram values
  expect(response).to.have.property("spider_diagram_values");
  expect(response.spider_diagram_values).to.be.an("object");

  // Spider diagram range
  expect(response).to.have.property("spider_diagram_range");
  expect(response.spider_diagram_range).to.be.an("object");

  // Yearly forecasts
  expect(response).to.have.property("yearly_sales_forecast");
  expect(response.yearly_sales_forecast).to.have.property("years");
  expect(response.yearly_sales_forecast.years).to.be.an("array");
  expect(response.yearly_sales_forecast).to.have.property("values");
  expect(response.yearly_sales_forecast.values).to.be.an("array");

  expect(response).to.have.property("yearly_costs_forecast");
  expect(response.yearly_costs_forecast).to.have.property("years");
  expect(response.yearly_costs_forecast.years).to.be.an("array");

  // Value unlock data
  expect(response).to.have.property("value_unlock_data");
  expect(response.value_unlock_data).to.have.property("enpv");
  expect(response.value_unlock_data.enpv).to.be.an("array");
}

// Re-export types for use in tests
export type {
  Portfolio,
  PortfolioMetrics,
  PortfolioProjectCalls,
  PortfolioForecast,
};
