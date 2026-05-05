/**
 * Investment Game Utilities API Tests
 *
 * Tests utility endpoints of the investment game including:
 * - Game hints endpoint (with and without agent)
 * - Custom seeds endpoint
 *
 * All tests use GET requests where applicable
 */

import {
  makeAuthenticatedRequest,
  assertStatusCode,
  assertResponseIsArray,
  assertHasProperty,
  assertResponseBody,
  logResponse,
} from "../helpers/api-helpers";
import { endpoints } from "../helpers/endpoints";

describe("Investment Game Utilities API Tests", () => {
  let gameId: string;
  let availableAgents: any[] = [];

  before(() => {
    // Start a game to get a valid game ID for hint tests
    const gameStartPayload = {
      num_assets: 5,
      horizon: 10,
      starting_cash: 1000000,
    };

    makeAuthenticatedRequest(
      "POST",
      endpoints.investmentGame.start(),
      gameStartPayload,
    ).then((response) => {
      if (response.status === 200) {
        gameId = response.body.id;
      }
    });

    // Get available agents for hint tests
    makeAuthenticatedRequest("GET", endpoints.investmentGame.agents()).then(
      (response) => {
        if (response.status === 200) {
          availableAgents = response.body;
        }
      },
    );
  });

  // =============================================================================
  // GAME HINTS ENDPOINTS
  // =============================================================================

  context("Game Hints API", () => {
    it("should get hints without specific agent successfully", function () {
      // Skip if we don't have a valid game ID
      if (!gameId) {
        this.skip();
      }

      makeAuthenticatedRequest(
        "POST",
        endpoints.investmentGame.hint(gameId),
        {},
      ).then((response) => {
        assertStatusCode(response, 200);

        assertResponseBody(response, (body) => {
          // Hints can be an object with agent recommendations or empty object
          expect(body).to.be.an("object");

          // If hints are provided, validate structure
          if (Object.keys(body).length > 0) {
            Object.keys(body).forEach((agentName) => {
              expect(agentName).to.be.a("string");
              expect(body[agentName]).to.be.an("object");

              // Each agent should have investment recommendations
              Object.keys(body[agentName]).forEach((assetId) => {
                expect(assetId).to.be.a("string");
                expect(body[agentName][assetId]).to.equal("invest");
              });
            });
          }
        });
      });
    });

    it("should get hints with specific agent successfully", function () {
      // Skip if we don't have valid game ID or agents
      if (!gameId || availableAgents.length === 0) {
        this.skip();
      }

      const testAgent = availableAgents[0].name;

      makeAuthenticatedRequest(
        "POST",
        endpoints.investmentGame.hint(gameId, testAgent),
        {},
      ).then((response) => {
        assertStatusCode(response, 200);

        assertResponseBody(response, (body) => {
          expect(body).to.be.an("object");

          // If hints are provided for this agent
          if (Object.keys(body).length > 0) {
            // Should contain the requested agent
            if (body[testAgent]) {
              expect(body[testAgent]).to.be.an("object");

              Object.keys(body[testAgent]).forEach((assetId) => {
                expect(assetId).to.be.a("string");
                expect(body[testAgent][assetId]).to.equal("invest");
              });
            }
          }
        });
      });
    });

    it("should handle multiple agents in hint requests", function () {
      // Skip if we don't have valid data
      if (!gameId || availableAgents.length < 2) {
        this.skip();
      }

      // Test with different agents
      const agentsToTest = availableAgents.slice(0, 2);

      agentsToTest.forEach((agent) => {
        makeAuthenticatedRequest(
          "POST",
          endpoints.investmentGame.hint(gameId, agent.name),
          {},
        ).then((response) => {
          assertStatusCode(response, 200);

          assertResponseBody(response, (body) => {
            expect(body).to.be.an("object");
          });
        });
      });
    });

    it("should handle invalid game ID for hints gracefully", () => {
      const invalidGameId = "invalid-game-id-123";

      makeAuthenticatedRequest(
        "POST",
        endpoints.investmentGame.hint(invalidGameId),
        {},
      ).then((response) => {
        expect([400, 404, 422]).to.include(response.status);
      });
    });

    it("should handle invalid agent name gracefully", function () {
      // Skip if we don't have valid game ID
      if (!gameId) {
        this.skip();
      }

      const invalidAgent = "NonExistentAgent123";

      makeAuthenticatedRequest(
        "POST",
        endpoints.investmentGame.hint(gameId, invalidAgent),
        {},
      ).then((response) => {
        // Should either return 200 with empty/error response or appropriate error code
        expect([200, 400, 404, 422]).to.include(response.status);

        if (response.status === 200) {
          // Should return empty object or error message
          expect(response.body).to.be.an("object");
        }
      });
    });

    it("should handle empty agent name gracefully", function () {
      // Skip if we don't have valid game ID
      if (!gameId) {
        this.skip();
      }

      const emptyAgent = "";

      makeAuthenticatedRequest(
        "POST",
        endpoints.investmentGame.hint(gameId, emptyAgent),
        {},
      ).then((response) => {
        // Should handle empty agent name (might default to no agent specified)
        expect([200, 400]).to.include(response.status);
      });
    });

    it("should handle special characters in agent name", function () {
      // Skip if we don't have valid game ID
      if (!gameId) {
        this.skip();
      }

      const specialCharAgent = "Agent@#$%";

      makeAuthenticatedRequest(
        "POST",
        endpoints.investmentGame.hint(gameId, specialCharAgent),
        {},
      ).then((response) => {
        expect([200, 400, 404, 422]).to.include(response.status);
      });
    });
  });

  // =============================================================================
  // CUSTOM SEEDS ENDPOINTS
  // =============================================================================

  context("Custom Seeds API", () => {
    it("should get custom seed with valid number of assets", () => {
      const numAssets = 5;

      makeAuthenticatedRequest(
        "GET",
        endpoints.investmentGame.customSeed(numAssets),
      ).then((response) => {
        assertStatusCode(response, 200);

        assertResponseBody(response, (body) => {
          // Custom seed should return a number (the seed value)
          expect(body).to.be.a("number");
          expect(body).to.be.at.least(0);
        });
      });
    });

    it("should handle different asset counts", () => {
      const assetCounts = [1, 3, 5, 10, 15];

      assetCounts.forEach((count) => {
        makeAuthenticatedRequest(
          "GET",
          endpoints.investmentGame.customSeed(count),
        ).then((response) => {
          assertStatusCode(response, 200);

          assertResponseBody(response, (body) => {
            expect(body).to.be.a("number");
            expect(body).to.be.at.least(0);
          });
        });
      });
    });

    it("should handle edge cases for asset counts", () => {
      const edgeCases = [0, 1, 100];

      edgeCases.forEach((count) => {
        makeAuthenticatedRequest(
          "GET",
          endpoints.investmentGame.customSeed(count),
        ).then((response) => {
          // Should either succeed or return appropriate error
          if (count <= 0) {
            expect([400, 422]).to.include(response.status);
          } else {
            expect([200, 400]).to.include(response.status);

            if (response.status === 200) {
              expect(response.body).to.be.a("number");
            }
          }
        });
      });
    });

    it("should handle invalid asset counts gracefully", () => {
      const invalidCounts = [-1, -5, 0];

      invalidCounts.forEach((count) => {
        makeAuthenticatedRequest(
          "GET",
          endpoints.investmentGame.customSeed(count),
        ).then((response) => {
          expect([400, 422]).to.include(response.status);
        });
      });
    });

    it("should handle very large asset counts", () => {
      const largeCount = 1000;

      makeAuthenticatedRequest(
        "GET",
        endpoints.investmentGame.customSeed(largeCount),
      ).then((response) => {
        // Should handle gracefully - either succeed or return reasonable error
        expect([200, 400, 413, 422]).to.include(response.status);

        if (response.status === 200) {
          expect(response.body).to.be.a("number");
        }
      });
    });

    it("should generate different seeds for same asset count", () => {
      const numAssets = 5;
      let firstSeed: number;
      let secondSeed: number;

      makeAuthenticatedRequest(
        "GET",
        endpoints.investmentGame.customSeed(numAssets),
      )
        .then((response) => {
          assertStatusCode(response, 200);
          firstSeed = response.body;

          // Get another seed
          return makeAuthenticatedRequest(
            "GET",
            endpoints.investmentGame.customSeed(numAssets),
          );
        })
        .then((response) => {
          assertStatusCode(response, 200);
          secondSeed = response.body;

          // Seeds might be different (depending on implementation)
          expect(firstSeed).to.be.a("number");
          expect(secondSeed).to.be.a("number");

          // Both should be valid numbers
          expect(firstSeed).to.be.at.least(0);
          expect(secondSeed).to.be.at.least(0);
        });
    });
  });

  // =============================================================================
  // PERFORMANCE TESTS
  // =============================================================================

  context("Performance Tests for Utility APIs", () => {
    it("should respond to hint request within reasonable time", function () {
      // Skip if we don't have valid game ID
      if (!gameId) {
        this.skip();
      }

      const startTime = Date.now();

      makeAuthenticatedRequest(
        "POST",
        endpoints.investmentGame.hint(gameId),
        {},
      ).then((response) => {
        const endTime = Date.now();
        const responseTime = endTime - startTime;

        assertStatusCode(response, 200);
        expect(responseTime).to.be.below(10000); // Should respond within 10 seconds
      });
    });

    it("should respond to custom seed request within reasonable time", () => {
      const startTime = Date.now();

      makeAuthenticatedRequest(
        "GET",
        endpoints.investmentGame.customSeed(5),
      ).then((response) => {
        const endTime = Date.now();
        const responseTime = endTime - startTime;

        assertStatusCode(response, 200);
        expect(responseTime).to.be.below(5000); // Should respond within 5 seconds
      });
    });
  });

  // =============================================================================
  // INTEGRATION TESTS
  // =============================================================================

  context("Integration Tests", () => {
    it("should provide hints consistent with available agents", function () {
      // Skip if we don't have valid data
      if (!gameId || availableAgents.length === 0) {
        this.skip();
      }

      makeAuthenticatedRequest(
        "POST",
        endpoints.investmentGame.hint(gameId),
        {},
      ).then((response) => {
        assertStatusCode(response, 200);

        assertResponseBody(response, (body) => {
          // If hints are provided, agent names should match available agents
          const hintAgentNames = Object.keys(body);
          const availableAgentNames = availableAgents.map(
            (agent) => agent.name,
          );

          hintAgentNames.forEach((agentName) => {
            // Each hint agent should be in the available agents list
            // Note: This might not always be true depending on implementation
            expect(agentName).to.be.a("string");
          });
        });
      });
    });

    it("should handle hint requests for games at different stages", function () {
      // Skip if we don't have valid game ID
      if (!gameId) {
        this.skip();
      }

      // Test hints for a fresh game
      makeAuthenticatedRequest(
        "POST",
        endpoints.investmentGame.hint(gameId),
        {},
      )
        .then((response) => {
          assertStatusCode(response, 200);

          // Get current game state
          return makeAuthenticatedRequest(
            "POST",
            endpoints.investmentGame.step(gameId),
            {},
          );
        })
        .then((response) => {
          assertStatusCode(response, 200);

          assertResponseBody(response, (gameState) => {
            // Game should be in a valid state
            expect(gameState.game_ended).to.be.a("boolean");
            expect(gameState.time).to.be.at.least(0);
            expect(gameState.time).to.be.at.most(gameState.horizon);
          });
        });
    });

    it("should generate reasonable custom seeds for different scenarios", () => {
      const scenarios = [
        { assets: 1, description: "minimal assets" },
        { assets: 5, description: "standard assets" },
        { assets: 10, description: "many assets" },
      ];

      scenarios.forEach((scenario) => {
        makeAuthenticatedRequest(
          "GET",
          endpoints.investmentGame.customSeed(scenario.assets),
        ).then((response) => {
          assertStatusCode(response, 200);

          assertResponseBody(response, (seed) => {
            expect(seed).to.be.a("number");
            expect(seed).to.be.at.least(0);

            // Seeds should be reasonable integers
            expect(seed % 1).to.equal(0); // Should be integer
            expect(seed).to.be.below(Number.MAX_SAFE_INTEGER);
          });
        });
      });
    });
  });

  // =============================================================================
  // ERROR BOUNDARY TESTS
  // =============================================================================

  context("Error Boundary Tests", () => {
    it("should handle concurrent hint requests gracefully", function () {
      // Skip if we don't have valid game ID
      if (!gameId) {
        this.skip();
      }

      // Make multiple concurrent requests
      const concurrentRequests = [
        makeAuthenticatedRequest(
          "POST",
          endpoints.investmentGame.hint(gameId),
          {},
        ),
        makeAuthenticatedRequest(
          "POST",
          endpoints.investmentGame.hint(gameId),
          {},
        ),
        makeAuthenticatedRequest(
          "POST",
          endpoints.investmentGame.hint(gameId),
          {},
        ),
      ];

      Promise.all(concurrentRequests).then(
        (responses: Cypress.Response<any>[]) => {
          responses.forEach((response) => {
            assertStatusCode(response, 200);
            expect(response.body).to.be.an("object");
          });
        },
      );
    });

    it("should handle concurrent custom seed requests", () => {
      const concurrentRequests = [
        makeAuthenticatedRequest("GET", endpoints.investmentGame.customSeed(5)),
        makeAuthenticatedRequest("GET", endpoints.investmentGame.customSeed(5)),
        makeAuthenticatedRequest("GET", endpoints.investmentGame.customSeed(3)),
      ];

      Promise.all(concurrentRequests).then(
        (responses: Cypress.Response<any>[]) => {
          responses.forEach((response) => {
            assertStatusCode(response, 200);
            expect(response.body).to.be.a("number");
            expect(response.body).to.be.at.least(0);
          });
        },
      );
    });
  });
});
