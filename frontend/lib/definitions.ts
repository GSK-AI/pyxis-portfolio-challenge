// Type definitions for JWT payload
export interface JwtPayload {
  exp?: number;
  iat?: number;
  sub?: string;
  name?: string;
  email?: string;
  [key: string]: unknown;
}
