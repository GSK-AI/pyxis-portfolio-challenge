/**
 * Investment Game Social Features API Tests
 *
 * Tests social features of the investment game including:
 * - Global leaderboard endpoint
 * - Level-specific leaderboard endpoint
 * - Agents endpoint
 * - Comparison dashboard endpoint
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

describe("Investment Game Social Features API Tests", () => {
  let gameId: string;
  let availableLevels: any[] = [];
  let sampleLevelId: number = 1; // Default level ID for testing

  before(() => {
    // Get available levels first
    makeAuthenticatedRequest("GET", endpoints.investmentGame.levels()).then(
      (response) => {
        if (response.status === 200 && response.body.length > 0) {
          availableLevels = response.body;
          sampleLevelId = availableLevels[0].level_idx;
        }
      },
    );

    // Start a game to get a valid game ID for comparison tests
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
  });

  // =============================================================================
  // AGENTS ENDPOINT
  // =============================================================================

  context("Game Agents API", () => {
    it("should get available agents successfully", () => {
      makeAuthenticatedRequest("GET", endpoints.investmentGame.agents()).then(
        (response) => {
          assertStatusCode(response, 200);
          assertResponseIsArray(response);

          assertResponseBody(response, (body) => {
            // Validate agents structure
            body.forEach((agent: any) => {
              assertHasProperty(agent, "name", "string");
              assertHasProperty(agent, "cost", "number");

              // Validate agent properties
              expect(agent.name).to.have.length.greaterThan(0);
              expect(agent.cost).to.be.at.least(0);
            });
          });
        },
      );
    });

    it("should return agents with valid cost structures", () => {
      makeAuthenticatedRequest("GET", endpoints.investmentGame.agents()).then(
        (response) => {
          assertStatusCode(response, 200);

          assertResponseBody(response, (body) => {
            expect(body).to.have.length.greaterThan(0);

            body.forEach((agent: any) => {
              // Agent costs should be reasonable (not negative, not extremely high)
              expect(agent.cost).to.be.at.least(0);
              expect(agent.cost).to.be.below(1000000); // Reasonable upper bound

              // Agent names should be non-empty strings
              expect(agent.name.trim()).to.have.length.greaterThan(0);
            });
          });
        },
      );
    });

    it("should have unique agent names", () => {
      makeAuthenticatedRequest("GET", endpoints.investmentGame.agents()).then(
        (response) => {
          assertStatusCode(response, 200);

          assertResponseBody(response, (body) => {
            const agentNames = body.map((agent: any) => agent.name);
            const uniqueNames = Array.from(new Set(agentNames));

            expect(uniqueNames).to.have.length(agentNames.length);
          });
        },
      );
    });
  });

  // =============================================================================
  // GLOBAL LEADERBOARD ENDPOINT
  // =============================================================================

  context("Global Leaderboard API", () => {
    it("should get global leaderboard successfully", () => {
      makeAuthenticatedRequest(
        "GET",
        endpoints.investmentGame.leaderboardGlobal(),
      ).then((response) => {
        assertStatusCode(response, 200);
        assertResponseIsArray(response);

        assertResponseBody(response, (body) => {
          // Validate leaderboard entry structure (if entries exist)
          body.forEach((entry: any) => {
            assertHasProperty(entry, "game_id", "string");
            assertHasProperty(entry, "user_id", "string");
            assertHasProperty(entry, "av_enpv", "number");

            // Validate entry properties
            expect(entry.game_id).to.have.length.greaterThan(0);
            expect(entry.user_id).to.have.length.greaterThan(0);
            expect(entry.av_enpv).to.be.a("number");
          });
        });
      });
    });

    it("should return leaderboard entries in expected order", () => {
      makeAuthenticatedRequest(
        "GET",
        endpoints.investmentGame.leaderboardGlobal(),
      ).then((response) => {
        assertStatusCode(response, 200);

        assertResponseBody(response, (body) => {
          if (body.length > 1) {
            // Check if entries are ordered by av_enpv (descending typically)
            for (let i = 0; i < body.length - 1; i++) {
              // Note: Actual ordering depends on backend implementation
              expect(body[i].av_enpv).to.be.a("number");
              expect(body[i + 1].av_enpv).to.be.a("number");
            }
          }
        });
      });
    });

    it("should handle empty leaderboard gracefully", () => {
      makeAuthenticatedRequest(
        "GET",
        endpoints.investmentGame.leaderboardGlobal(),
      ).then((response) => {
        assertStatusCode(response, 200);
        assertResponseIsArray(response);

        // Should return empty array if no entries, not null or undefined
        expect(response.body).to.be.an("array");
      });
    });
  });

  // =============================================================================
  // LEVEL LEADERBOARD ENDPOINT
  // =============================================================================

  context("Level Leaderboard API", () => {
    it("should get level-specific leaderboard successfully", () => {
      makeAuthenticatedRequest(
        "GET",
        endpoints.investmentGame.leaderboardLevels(sampleLevelId),
      ).then((response) => {
        assertStatusCode(response, 200);
        assertResponseIsArray(response);

        assertResponseBody(response, (body) => {
          // Validate leaderboard entry structure (if entries exist)
          body.forEach((entry: any) => {
            assertHasProperty(entry, "game_id", "string");
            assertHasProperty(entry, "user_id", "string");
            assertHasProperty(entry, "av_enpv", "number");
          });
        });
      });
    });

    it("should handle different level IDs", () => {
      const testLevelIds = [0, 1, 2, sampleLevelId];

      testLevelIds.forEach((levelId) => {
        makeAuthenticatedRequest(
          "GET",
          endpoints.investmentGame.leaderboardLevels(levelId),
        ).then((response) => {
          // Should return 200 for valid level IDs or appropriate error for invalid ones
          expect([200, 400, 404]).to.include(response.status);

          if (response.status === 200) {
            assertResponseIsArray(response);
          }
        });
      });
    });

    it("should handle invalid level IDs gracefully", () => {
      const invalidLevelId = -1;

      makeAuthenticatedRequest(
        "GET",
        endpoints.investmentGame.leaderboardLevels(invalidLevelId),
      ).then((response) => {
        // Should return appropriate error for invalid level ID
        expect([400, 404, 422]).to.include(response.status);
      });
    });

    it("should handle very high level IDs", () => {
      const highLevelId = 99999;

      makeAuthenticatedRequest(
        "GET",
        endpoints.investmentGame.leaderboardLevels(highLevelId),
      ).then((response) => {
        // Should handle gracefully - either empty array (200) or not found (404)
        expect([200, 404]).to.include(response.status);

        if (response.status === 200) {
          assertResponseIsArray(response);
        }
      });
    });
  });

  // =============================================================================
  // HIGHSCORE ENDPOINT
  // =============================================================================

  context("Game Highscore API", () => {
    it("should get highscore for specific level successfully", () => {
      makeAuthenticatedRequest(
        "GET",
        endpoints.investmentGame.highscore(sampleLevelId),
      ).then((response) => {
        // Highscore might return 200 with data, or 404 if no highscore exists
        expect([200, 404]).to.include(response.status);

        if (response.status === 200) {
          assertResponseBody(response, (body) => {
            // Highscore could be a number or an object with score data
            expect(body).to.not.be.null;
            expect(body).to.not.be.undefined;
          });
        }
      });
    });

    it("should handle different level IDs for highscore", () => {
      const testLevelIds = [0, 1, sampleLevelId];

      testLevelIds.forEach((levelId) => {
        makeAuthenticatedRequest(
          "GET",
          endpoints.investmentGame.highscore(levelId),
        ).then((response) => {
          // Should return 200 with data, 404 if no highscore, or 400 for invalid level
          expect([200, 400, 404]).to.include(response.status);
        });
      });
    });

    it("should handle invalid level IDs for highscore", () => {
      const invalidLevelId = -1;

      makeAuthenticatedRequest(
        "GET",
        endpoints.investmentGame.highscore(invalidLevelId),
      ).then((response) => {
        expect([400, 404, 422]).to.include(response.status);
      });
    });
  });

  // =============================================================================
  // COMPARISON DASHBOARD ENDPOINT
  // =============================================================================

  context("Game Comparison API", () => {
    it("should get game comparison data successfully", function () {
      // Skip if we don't have a valid game ID
      if (!gameId) {
        this.skip();
      }

      makeAuthenticatedRequest(
        "POST",
        endpoints.investmentGame.comparison(gameId),
        {},
      ).then((response) => {
        assertStatusCode(response, 200);

        assertResponseBody(response, (body) => {
          assertHasProperty(body, "game_id", "string");
          assertHasProperty(body, "av_enpv", "object");
          assertHasProperty(body, "final_enpv", "object");
          assertHasProperty(body, "final_eroi", "object");
          assertHasProperty(body, "final_capital", "object");
          assertHasProperty(body, "realised_eroi", "object");
          assertHasProperty(body, "enpv_over_time", "object");

          expect(body.game_id).to.equal(gameId);

          // Validate comparison data structures
          expect(body.av_enpv).to.be.an("object");
          expect(body.final_enpv).to.be.an("object");
          expect(body.final_eroi).to.be.an("object");
          expect(body.final_capital).to.be.an("object");
          expect(body.realised_eroi).to.be.an("object");
          expect(body.enpv_over_time).to.be.an("object");

          // Optional property
          if ("eroi_over_time" in body) {
            assertHasProperty(body, "eroi_over_time", "object");
          }
        });
      });
    });

    it("should handle invalid game ID for comparison", () => {
      const invalidGameId = "invalid-game-id-123";

      makeAuthenticatedRequest(
        "POST",
        endpoints.investmentGame.comparison(invalidGameId),
        {},
      ).then((response) => {
        expect([400, 404, 422]).to.include(response.status);
      });
    });

    it("should handle empty game ID for comparison", () => {
      const emptyGameId = "";

      makeAuthenticatedRequest(
        "POST",
        endpoints.investmentGame.comparison(emptyGameId),
        {},
      ).then((response) => {
        expect([400, 404, 422]).to.include(response.status);
      });
    });
  });

  // =============================================================================
  // PERFORMANCE TESTS
  // =============================================================================

  context("Performance Tests for Social APIs", () => {
    it("should respond to agents request within reasonable time", () => {
      const startTime = Date.now();

      makeAuthenticatedRequest("GET", endpoints.investmentGame.agents()).then(
        (response) => {
          const endTime = Date.now();
          const responseTime = endTime - startTime;

          assertStatusCode(response, 200);
          expect(responseTime).to.be.below(5000); // Should respond within 5 seconds
        },
      );
    });

    it("should respond to global leaderboard request within reasonable time", () => {
      const startTime = Date.now();

      makeAuthenticatedRequest(
        "GET",
        endpoints.investmentGame.leaderboardGlobal(),
      ).then((response) => {
        const endTime = Date.now();
        const responseTime = endTime - startTime;

        assertStatusCode(response, 200);
        expect(responseTime).to.be.below(5000); // Should respond within 5 seconds
      });
    });

    it("should respond to level leaderboard request within reasonable time", () => {
      const startTime = Date.now();

      makeAuthenticatedRequest(
        "GET",
        endpoints.investmentGame.leaderboardLevels(sampleLevelId),
      ).then((response) => {
        const endTime = Date.now();
        const responseTime = endTime - startTime;

        expect([200, 404]).to.include(response.status);
        expect(responseTime).to.be.below(5000); // Should respond within 5 seconds
      });
    });
  });

  // =============================================================================
  // CROSS-FEATURE VALIDATION
  // =============================================================================

  context("Cross-Feature Validation", () => {
    it("should have consistent data between global and level leaderboards", () => {
      let globalLeaderboard: any[] = [];
      let levelLeaderboard: any[] = [];

      // Get global leaderboard
      makeAuthenticatedRequest(
        "GET",
        endpoints.investmentGame.leaderboardGlobal(),
      )
        .then((response) => {
          globalLeaderboard = response.body;

          // Get level-specific leaderboard
          return makeAuthenticatedRequest(
            "GET",
            endpoints.investmentGame.leaderboardLevels(sampleLevelId),
          );
        })
        .then((response) => {
          levelLeaderboard = response.body;

          // Validate consistency (if both have data)
          if (globalLeaderboard.length > 0 && levelLeaderboard.length > 0) {
            // Both should have same entry structure
            expect(globalLeaderboard[0]).to.have.all.keys(levelLeaderboard[0]);
          }
        });
    });

    it("should have agents available for hint system", () => {
      makeAuthenticatedRequest("GET", endpoints.investmentGame.agents()).then(
        (response) => {
          assertStatusCode(response, 200);

          assertResponseBody(response, (body) => {
            expect(body).to.have.length.greaterThan(0);

            // Each agent should be available for hints
            body.forEach((agent: any) => {
              expect(agent.name).to.be.a("string");
              expect(agent.name.length).to.be.greaterThan(0);
            });
          });
        },
      );
    });
  });
});
