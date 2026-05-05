// Type definitions for JWT payload
export interface JwtPayload {
  exp?: number;
  iat?: number;
  sub?: string;
  name?: string;
  email?: string;
  [key: string]: unknown;
}

// Type definitions for Pareto Frontier visualizations
export interface PortfolioPoint {
  x: number;
  y: number;
  [key: string]: unknown;
}

export interface ParetoFrontier {
  points: PortfolioPoint[];
  [key: string]: unknown;
}

// Type definitions for Spider chart
export interface SpiderValues {
  [key: string]: number;
}
