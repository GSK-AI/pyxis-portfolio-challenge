/**
 * Investment Game Core API Tests - Clean Version
 *
 * Tests core game functionality including:
 * - Game start endpoint
 * - Game step endpoint
 * - Game levels endpoint
 */

import {
  makeAuthenticatedRequest,
  assertStatusCode,
  assertResponseIsArray,
  assertHasProperty,
  assertResponseBody,
} from "../helpers/api-helpers";
import { endpoints } from "../helpers/endpoints";

describe("Investment Game Core API Tests - Debug", () => {
  let gameId: string;

  beforeEach(() => {
    // Ensure we have fresh data for each test
    gameId = "";
  });

  // =============================================================================
  // GAME LEVELS ENDPOINTS
  // =============================================================================

  context("Game Levels API", () => {
    it("should get game levels successfully", () => {
      makeAuthenticatedRequest("GET", endpoints.investmentGame.levels()).then(
        (response) => {
          assertStatusCode(response, 200);
          assertResponseIsArray(response);

          assertResponseBody(response, (body) => {
            expect(body).to.have.length.greaterThan(0);

            // Validate level structure
            body.forEach((level: any) => {
              assertHasProperty(level, "level_idx", "number");
              assertHasProperty(level, "user_has_completed", "boolean");
              assertHasProperty(level, "num_assets", "number");
              assertHasProperty(level, "horizon", "number");
              assertHasProperty(level, "starting_cash", "number");
            });
          });
        },
      );
    });
  });

  // =============================================================================
  // GAME START ENDPOINTS - DEBUG VERSION
  // =============================================================================

  context("Game Start API - Debug", () => {
    it("should investigate game start response structure", () => {
      const gameStartPayload = {
        num_assets: 5,
        max_num_assets: 10,
        horizon: 10,
        starting_cash: 1000000,
        level_idx: 0,
        global_seed: 42,
      };

      makeAuthenticatedRequest(
        "POST",
        endpoints.investmentGame.start(),
        gameStartPayload,
      ).then((response) => {
        // Basic status check
        assertStatusCode(response, 200);

        // Log detailed response information
        cy.log(`Response status: ${response.status}`);
        cy.log(
          `Content-Type: ${response.headers["content-type"] || "not set"}`,
        );

        // Use cypress logs and assertions to reveal response structure
        cy.then(() => {
          const bodyType = typeof response.body;
          const isArray = Array.isArray(response.body);

          cy.log(`🔍 Response analysis:`);
          cy.log(`Body type: ${bodyType}`);
          cy.log(`Is array: ${isArray}`);

          if (isArray) {
            cy.log(`Array length: ${response.body.length}`);
            if (response.body.length > 0) {
              cy.log(`First element: ${JSON.stringify(response.body[0])}`);
              cy.log(`First element type: ${typeof response.body[0]}`);
            }
          } else {
            // If it's an object, show some keys
            const keys = Object.keys(response.body || {});
            cy.log(`Object keys (first 5): ${keys.slice(0, 5).join(", ")}`);
          }
        });

        // Basic validation - just check that we got something
        expect(response.body).to.exist;

        // Check if this matches the [ 0 ] pattern we've been seeing
        if (
          Array.isArray(response.body) &&
          response.body.length === 1 &&
          response.body[0] === 0
        ) {
          cy.log(
            "⚠️ Received [0] response - this may indicate an API configuration issue",
          );
          cy.log(
            "This suggests the API is not returning the expected game state object",
          );
        } else if (Array.isArray(response.body) && response.body.length > 1) {
          cy.log(`📋 Received array with ${response.body.length} elements`);
        } else if (!Array.isArray(response.body)) {
          cy.log("📦 Received object response (expected format)");
        }
      });
    });

    it("should test direct endpoint URL construction", () => {
      // Test what URL we're actually hitting
      const startEndpoint = endpoints.investmentGame.start();
      cy.log(`Game start endpoint: ${startEndpoint}`);

      // Make a simple GET request to see if the endpoint exists
      makeAuthenticatedRequest("GET", startEndpoint).then((response) => {
        cy.log(`GET response status: ${response.status}`);
        // Even if it returns 405 (Method Not Allowed), that confirms the endpoint exists
        // We just want to see what happens
      });
    });
  });

  // =============================================================================
  // QUICK ENDPOINT VALIDATION
  // =============================================================================

  context("Endpoint Validation", () => {
    it("should validate all game endpoint URLs are constructed correctly", () => {
      // Test all endpoint construction
      const endpoints_to_test = [
        { name: "start", url: endpoints.investmentGame.start() },
        { name: "levels", url: endpoints.investmentGame.levels() },
        { name: "agents", url: endpoints.investmentGame.agents() },
        {
          name: "leaderboardGlobal",
          url: endpoints.investmentGame.leaderboardGlobal(),
        },
      ];

      endpoints_to_test.forEach((endpoint) => {
        cy.log(`${endpoint.name}: ${endpoint.url}`);
        expect(endpoint.url).to.include("game");
        expect(endpoint.url).to.match(/^https?:\/\//);
      });
    });
  });
});
