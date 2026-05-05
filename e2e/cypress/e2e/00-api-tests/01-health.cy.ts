import {
  makeAuthenticatedRequest,
  assertStatusCode,
  assertHasProperty,
  logResponse,
} from "../helpers/api-helpers";
import { endpoints } from "../helpers/endpoints";

describe("Health Check API Tests", () => {
  describe("[GET] /health", () => {
    it("should return 200 status code with valid authentication", () => {
      makeAuthenticatedRequest("GET", endpoints.health()).then((response) => {
        assertStatusCode(response, 200);
      });
    });

    it("should return correct response structure", () => {
      makeAuthenticatedRequest("GET", endpoints.health()).then((response) => {
        assertStatusCode(response, 200);
        assertHasProperty(response.body, "status", "string");
      });
    });

    it('should return status as "ok"', () => {
      makeAuthenticatedRequest("GET", endpoints.health()).then((response) => {
        assertStatusCode(response, 200);
        expect(response.body.status).to.eq("ok");
        cy.log("✓ Health check passed - API is healthy");
      });
    });

    it("should have expected response time (performance check)", () => {
      makeAuthenticatedRequest("GET", endpoints.health()).then((response) => {
        assertStatusCode(response, 200);
        expect(response.duration).to.be.lessThan(5000); // Should respond within 5 seconds
        cy.log(`Response time: ${response.duration}ms`);
      });
    });

    it("should return consistent responses on multiple calls", () => {
      // Make multiple requests to ensure consistency
      for (let i = 0; i < 3; i++) {
        makeAuthenticatedRequest("GET", endpoints.health()).then((response) => {
          assertStatusCode(response, 200);
          expect(response.body.status).to.eq("ok");
        });
      }
    });
  });

  describe("[GET] / (root endpoint)", () => {
    it("should return welcome message", () => {
      makeAuthenticatedRequest("GET", endpoints.root()).then((response) => {
        assertStatusCode(response, 200);
        assertHasProperty(response.body, "message", "string");
        expect(response.body.message).to.eq("Hello World");
        cy.log("✓ Root endpoint accessible");
      });
    });
  });
});
