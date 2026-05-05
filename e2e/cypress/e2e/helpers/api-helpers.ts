/**
 * Helper functions for API testing
 */

export interface SessionData {
  id_token: string;
}

/**
 * Makes an authenticated API request using a full URL
 */
export function makeAuthenticatedRequest(
  method: "GET" | "POST" | "PUT" | "DELETE",
  url: string,
  body?: any,
) {
  return cy
    .readFile("cypress/fixtures/session.json")
    .then((session: SessionData) => {
      const requestOptions: Partial<Cypress.RequestOptions> = {
        method,
        url,
        headers: {
          Authorization: `Bearer ${session.id_token}`,
          "Content-Type": "application/json",
        },
        failOnStatusCode: false,
      };

      if (body) {
        requestOptions.body = body;
      }

      return cy.request(requestOptions);
    });
}

/**
 * Validates that a response has the expected status code
 */
export function assertStatusCode(
  response: Cypress.Response<any>,
  expectedStatus: number,
) {
  expect(response.status).to.eq(expectedStatus);
}

/**
 * Validates common response properties
 */
export function assertResponseIsArray(response: Cypress.Response<any>) {
  expect(response.body).to.be.an("array");
}

/**
 * Validates response contains a specific property
 */
export function assertHasProperty(obj: any, property: string, type?: string) {
  expect(obj).to.have.property(property);
  if (type) {
    expect(obj[property]).to.be.a(type);
  }
}

/**
 * Validates response body structure
 */
export function assertResponseBody(
  response: Cypress.Response<any>,
  assertions: (body: any) => void,
) {
  assertions(response.body);
}

/**
 * Logs response details for debugging
 */
export function logResponse(response: Cypress.Response<any>, message?: string) {
  if (message) {
    cy.log(message);
  }
  cy.log(`Status: ${response.status}`);
  cy.log(`Body: ${JSON.stringify(response.body)}`);
}
