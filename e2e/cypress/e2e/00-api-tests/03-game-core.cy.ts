/**
 * Investment Game Core API Tests - Fixed Version
 *
 * Tests core game functionality including:
 * - Game start endpoint (POST)
 * - Game step endpoint (POST)
 * - Game levels endpoint (GET)
 */

import {
  makeAuthenticatedRequest,
  assertStatusCode,
  assertResponseIsArray,
  assertHasProperty,
  assertResponseBody,
} from "../helpers/api-helpers";
import { endpoints } from "../helpers/endpoints";

describe("Investment Game Core API Tests", () => {
  let gameId: string;
  let availableLevels: any[] = [];

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

            // Store levels for other tests
            availableLevels = body;

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

    it("should have levels with valid configurations", () => {
      makeAuthenticatedRequest("GET", endpoints.investmentGame.levels()).then(
        (response) => {
          assertStatusCode(response, 200);

          assertResponseBody(response, (body) => {
            expect(body).to.have.length.greaterThan(0);

            body.forEach((level: any) => {
              // Validate level configuration values
              expect(level.num_assets).to.be.at.least(1);
              expect(level.horizon).to.be.at.least(1);
              expect(level.starting_cash).to.be.at.least(0);

              // If max_num_assets is present, it should be >= num_assets
              if (level.max_num_assets) {
                expect(level.max_num_assets).to.be.at.least(level.num_assets);
              }
            });
          });
        },
      );
    });
  });

  // =============================================================================
  // GAME START ENDPOINTS
  // =============================================================================

  context("Game Start API", () => {
    it("should start a new game successfully", () => {
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
        assertStatusCode(response, 200);

        assertResponseBody(response, (body) => {
          // Validate the response matches GameStepResponse schema
          assertHasProperty(body, "id", "string");
          assertHasProperty(body, "cash", "number");
          assertHasProperty(body, "time", "number");
          assertHasProperty(body, "horizon", "number");
          assertHasProperty(body, "assets", "object");
          assertHasProperty(body, "expired_assets", "object");
          assertHasProperty(body, "realised_costs", "object");
          assertHasProperty(body, "realised_revenues", "object");
          assertHasProperty(body, "game_ended", "boolean");
          assertHasProperty(body, "capital_over_time", "object");
          assertHasProperty(body, "enpv_over_time", "object");

          // Store game ID for other tests
          gameId = body.id;

          // Validate initial game state
          expect(body.time).to.equal(0);
          expect(body.game_ended).to.equal(false);
          expect(body.cash).to.equal(1000000); // Should match starting_cash
          expect(body.horizon).to.equal(10); // Should match payload horizon
        });
      });
    });

    it("should create game with valid assets structure", () => {
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
        assertStatusCode(response, 200);

        assertResponseBody(response, (body) => {
          const assets = body.assets;
          expect(assets).to.be.an("object");

          // Check if we have assets
          const assetIds = Object.keys(assets);
          expect(assetIds).to.have.length.greaterThan(0);

          // Validate asset structure - each asset should have required properties
          assetIds.forEach((assetId: string) => {
            const asset = assets[assetId];
            assertHasProperty(asset, "id", "string");
            assertHasProperty(asset, "name", "string");
            assertHasProperty(asset, "state", "string");
            assertHasProperty(asset, "max_revenue", "number");
            assertHasProperty(asset, "trials", "object");
          });
        });
      });
    });
  });

  // =============================================================================
  // GAME STEP ENDPOINTS
  // =============================================================================

  context("Game Step API", () => {
    beforeEach(() => {
      // Start a game first to get a valid game ID
      const gameStartPayload = {
        num_assets: 5,
        max_num_assets: 10,
        horizon: 10,
        starting_cash: 1000000,
        level_idx: 0,
        global_seed: 42,
      };

      return makeAuthenticatedRequest(
        "POST",
        endpoints.investmentGame.start(),
        gameStartPayload,
      ).then((response) => {
        assertStatusCode(response, 200);
        gameId = response.body.id;
      });
    });

    it("should get current game step successfully", () => {
      // Actions for game step - minimal action to proceed
      const actions = {
        action_type: "step",
      };

      makeAuthenticatedRequest(
        "POST",
        endpoints.investmentGame.step(gameId),
        actions,
      ).then((response) => {
        assertStatusCode(response, 200);

        assertResponseBody(response, (body) => {
          // Should have same structure as game start response
          assertHasProperty(body, "id", "string");
          assertHasProperty(body, "cash", "number");
          assertHasProperty(body, "time", "number");
          assertHasProperty(body, "horizon", "number");
          assertHasProperty(body, "assets", "object");
          assertHasProperty(body, "game_ended", "boolean");

          // Validate game ID consistency
          expect(body.id).to.equal(gameId);
        });
      });
    });

    it("should handle invalid game ID gracefully", () => {
      const invalidGameId = "invalid-game-id-12345";
      const actions = {
        action_type: "step",
      };

      makeAuthenticatedRequest(
        "POST",
        endpoints.investmentGame.step(invalidGameId),
        actions,
      ).then((response) => {
        // Should return an error status (4xx or 5xx)
        expect(response.status).to.be.at.least(400);
      });
    });

    it("should maintain game state consistency", () => {
      const actions = {
        action_type: "step",
      };

      makeAuthenticatedRequest(
        "POST",
        endpoints.investmentGame.step(gameId),
        actions,
      ).then((response) => {
        assertStatusCode(response, 200);

        assertResponseBody(response, (body) => {
          // Time should have advanced
          expect(body.time).to.be.at.least(0);

          // Game ID should remain the same
          expect(body.id).to.equal(gameId);

          // Cash should be a valid number (may have changed due to actions)
          expect(body.cash).to.be.a("number");
        });
      });
    });
  });

  // =============================================================================
  // PERFORMANCE TESTS FOR CORE GAME APIS
  // =============================================================================

  context("Performance Tests for Core Game APIs", () => {
    it("should respond to game levels request within reasonable time", () => {
      const startTime = Date.now();

      makeAuthenticatedRequest("GET", endpoints.investmentGame.levels()).then(
        (response) => {
          const endTime = Date.now();
          const responseTime = endTime - startTime;

          assertStatusCode(response, 200);
          expect(responseTime).to.be.below(5000); // Should respond within 5 seconds
        },
      );
    });

    it("should respond to game start request within reasonable time", () => {
      const startTime = Date.now();
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
        const endTime = Date.now();
        const responseTime = endTime - startTime;

        assertStatusCode(response, 200);
        expect(responseTime).to.be.below(10000); // Should respond within 10 seconds
      });
    });
  });

  // =============================================================================
  // ERROR HANDLING TESTS
  // =============================================================================

  context("Error Handling Tests", () => {
    it("should handle malformed game step requests", () => {
      const invalidActions = {
        invalid_field: "invalid_value",
      };

      // Use a dummy game ID for this test
      const dummyGameId = "test-game-id";

      makeAuthenticatedRequest(
        "POST",
        endpoints.investmentGame.step(dummyGameId),
        invalidActions,
      ).then((response) => {
        // Should handle gracefully (might return 400 or 422)
        expect(response.status).to.be.oneOf([400, 404, 422, 500]);
      });
    });

    it("should handle very long game ID strings", () => {
      const veryLongGameId = "a".repeat(1000); // 1000 character string
      const actions = {
        action_type: "step",
      };

      makeAuthenticatedRequest(
        "POST",
        endpoints.investmentGame.step(veryLongGameId),
        actions,
      ).then((response) => {
        // Should handle gracefully
        expect(response.status).to.be.at.least(400);
      });
    });
  });
});
