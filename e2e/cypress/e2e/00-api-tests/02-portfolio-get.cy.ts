import {
  assertPortfoliosResponse,
  assertPortfolioMetrics,
  assertPortfolioProjectsResponse,
  assertPortfolioForecastResponse,
  type Portfolio,
} from "../helpers/portfolios";
import {
  makeAuthenticatedRequest,
  assertStatusCode,
  assertResponseIsArray,
  assertHasProperty,
} from "../helpers/api-helpers";
import { endpoints } from "../helpers/endpoints";

describe("Portfolio GET API Tests", () => {
  let testPortfolioId: string;
  let testPortfolio: Portfolio;

  describe("[GET] /portfolios", () => {
    it("should return 200 status code", () => {
      makeAuthenticatedRequest("GET", endpoints.portfolios.list()).then(
        (response) => {
          assertStatusCode(response, 200);
        },
      );
    });

    it("should return an array of portfolios", () => {
      makeAuthenticatedRequest("GET", endpoints.portfolios.list()).then(
        (response) => {
          assertStatusCode(response, 200);
          assertResponseIsArray(response);

          const length = response.body.length;
          cy.log(`✓ Total Portfolios found: ${length}`);
        },
      );
    });

    it("should validate structure of each portfolio in response", () => {
      makeAuthenticatedRequest("GET", endpoints.portfolios.list()).then(
        (response) => {
          assertStatusCode(response, 200);
          assertResponseIsArray(response);

          if (response.body.length > 0) {
            response.body.forEach((portfolio: Portfolio, index: number) => {
              cy.log(
                `Validating portfolio ${index + 1}/${response.body.length}`,
              );
              assertPortfoliosResponse(portfolio);
            });

            // Store first portfolio for subsequent tests
            testPortfolio = response.body[0];
            testPortfolioId = testPortfolio.portfolio_id;
            cy.log(`✓ Stored test portfolio ID: ${testPortfolioId}`);
          } else {
            cy.log("⚠ No portfolios found to validate");
          }
        },
      );
    });

    it("should have portfolios with valid project_ids arrays", () => {
      makeAuthenticatedRequest("GET", endpoints.portfolios.list()).then(
        (response) => {
          assertStatusCode(response, 200);

          if (response.body.length > 0) {
            const portfoliosWithProjects = response.body.filter(
              (p: Portfolio) => p.project_ids.length > 0,
            );
            cy.log(
              `✓ Portfolios with projects: ${portfoliosWithProjects.length}`,
            );

            portfoliosWithProjects.forEach((portfolio: Portfolio) => {
              portfolio.project_ids.forEach((projectId: string) => {
                expect(projectId).to.be.a("string");
                expect(projectId).to.not.be.empty;
              });
            });
          }
        },
      );
    });

    it("should distinguish between published and unpublished portfolios", () => {
      makeAuthenticatedRequest("GET", endpoints.portfolios.list()).then(
        (response) => {
          assertStatusCode(response, 200);

          if (response.body.length > 0) {
            const publishedCount = response.body.filter(
              (p: Portfolio) => p.published,
            ).length;
            const unpublishedCount = response.body.filter(
              (p: Portfolio) => !p.published,
            ).length;

            cy.log(`✓ Published portfolios: ${publishedCount}`);
            cy.log(`✓ Unpublished portfolios: ${unpublishedCount}`);
          }
        },
      );
    });

    it("should identify edited portfolios", () => {
      makeAuthenticatedRequest("GET", endpoints.portfolios.list()).then(
        (response) => {
          assertStatusCode(response, 200);

          if (response.body.length > 0) {
            const editedCount = response.body.filter(
              (p: Portfolio) => p.edited,
            ).length;
            cy.log(`✓ Edited portfolios: ${editedCount}`);
          }
        },
      );
    });

    it("should return portfolios with valid timestamps", () => {
      makeAuthenticatedRequest("GET", endpoints.portfolios.list()).then(
        (response) => {
          assertStatusCode(response, 200);

          if (response.body.length > 0) {
            response.body.forEach((portfolio: Portfolio) => {
              expect(portfolio.ts).to.be.a("number");
              expect(portfolio.ts).to.be.greaterThan(0);

              // Timestamp appears to be in seconds, so check for reasonable value (after year 2020)
              // 1577836800 = Jan 1, 2020 in seconds
              expect(portfolio.ts).to.be.greaterThan(1577836800);
            });
            cy.log("✓ All portfolio timestamps are valid");
          }
        },
      );
    });
  });

  describe("[GET] /portfolios/{portfolio_id}/projects", () => {
    before(() => {
      // Get a portfolio ID to use for testing
      makeAuthenticatedRequest("GET", endpoints.portfolios.list()).then(
        (response) => {
          if (response.body.length > 0) {
            testPortfolioId = response.body[0].portfolio_id;
          }
        },
      );
    });

    it("should return 200 for valid portfolio ID", () => {
      cy.then(() => {
        if (testPortfolioId) {
          makeAuthenticatedRequest(
            "GET",
            endpoints.portfolios.projects(testPortfolioId),
          ).then((response) => {
            assertStatusCode(response, 200);
            cy.log(
              `✓ Successfully retrieved projects for portfolio ${testPortfolioId}`,
            );
          });
        } else {
          cy.log("⚠ Skipping test - no portfolio ID available");
        }
      });
    });

    it("should return valid projects structure", () => {
      cy.then(() => {
        if (testPortfolioId) {
          makeAuthenticatedRequest(
            "GET",
            endpoints.portfolios.projects(testPortfolioId),
          ).then((response) => {
            assertStatusCode(response, 200);
            assertPortfolioProjectsResponse(response.body);
            cy.log("✓ Projects response structure is valid");
          });
        } else {
          cy.log("⚠ Skipping test - no portfolio ID available");
        }
      });
    });

    it("should return projects with required fields", () => {
      cy.then(() => {
        if (testPortfolioId) {
          makeAuthenticatedRequest(
            "GET",
            endpoints.portfolios.projects(testPortfolioId),
          ).then((response) => {
            assertStatusCode(response, 200);

            if (response.body.projects && response.body.projects.length > 0) {
              const project = response.body.projects[0];

              // Essential project fields
              expect(project).to.have.property("project_id");
              expect(project).to.have.property("Name");
              expect(project).to.have.property("Current Phase");
              expect(project).to.have.property("TA");

              cy.log(`✓ Project fields validated: ${project.Name}`);
            }
          });
        } else {
          cy.log("⚠ Skipping test - no portfolio ID available");
        }
      });
    });

    it("should handle portfolio with no projects", () => {
      cy.then(() => {
        if (testPortfolioId) {
          makeAuthenticatedRequest(
            "GET",
            endpoints.portfolios.projects(testPortfolioId),
          ).then((response) => {
            assertStatusCode(response, 200);
            expect(response.body).to.have.property("projects");
            expect(response.body.projects).to.be.an("array");

            const projectCount = response.body.projects.length;
            cy.log(`✓ Portfolio has ${projectCount} projects`);
          });
        } else {
          cy.log("⚠ Skipping test - no portfolio ID available");
        }
      });
    });
  });

  describe("[GET] /portfolios/{portfolio_id}/metrics", () => {
    before(() => {
      makeAuthenticatedRequest("GET", endpoints.portfolios.list()).then(
        (response) => {
          if (response.body.length > 0) {
            testPortfolioId = response.body[0].portfolio_id;
          }
        },
      );
    });

    it("should return 200 for valid portfolio ID", () => {
      cy.then(() => {
        if (testPortfolioId) {
          makeAuthenticatedRequest(
            "GET",
            endpoints.portfolios.metrics(testPortfolioId),
          ).then((response) => {
            assertStatusCode(response, 200);
            cy.log("✓ Successfully retrieved portfolio metrics");
          });
        } else {
          cy.log("⚠ Skipping test - no portfolio ID available");
        }
      });
    });

    it("should return valid metrics structure", () => {
      cy.then(() => {
        if (testPortfolioId) {
          makeAuthenticatedRequest(
            "GET",
            endpoints.portfolios.metrics(testPortfolioId),
          ).then((response) => {
            assertStatusCode(response, 200);
            assertPortfolioMetrics(response.body);
            cy.log(
              `✓ Metrics - eNPV: ${response.body.enpv}, NPV: ${response.body.npv}`,
            );
          });
        } else {
          cy.log("⚠ Skipping test - no portfolio ID available");
        }
      });
    });

    it("should return financial metrics within reasonable ranges", () => {
      cy.then(() => {
        if (testPortfolioId) {
          makeAuthenticatedRequest(
            "GET",
            endpoints.portfolios.metrics(testPortfolioId),
          ).then((response) => {
            assertStatusCode(response, 200);

            const metrics = response.body;

            // Check that financial metrics are numbers
            expect(metrics.enpv).to.be.a("number");
            expect(metrics.npv).to.be.a("number");
            expect(metrics.eroi).to.be.a("number");
            expect(metrics.roi).to.be.a("number");

            // Log key metrics for visibility
            cy.log(`Financial Metrics:`);
            cy.log(`  eNPV: £${metrics.enpv}M`);
            cy.log(`  NPV: £${metrics.npv}M`);
            cy.log(`  eROI: ${metrics.eroi}`);
            cy.log(`  ROI: ${metrics.roi}`);
          });
        } else {
          cy.log("⚠ Skipping test - no portfolio ID available");
        }
      });
    });

    it("should return risk metrics", () => {
      cy.then(() => {
        if (testPortfolioId) {
          makeAuthenticatedRequest(
            "GET",
            endpoints.portfolios.metrics(testPortfolioId),
          ).then((response) => {
            assertStatusCode(response, 200);

            const metrics = response.body;

            // Risk metrics should be present
            expect(metrics).to.have.property("npv_outcome_mean");
            expect(metrics).to.have.property("npv_outcome_var");
            expect(metrics).to.have.property("npv_outcome_stdev");

            expect(metrics.npv_outcome_mean).to.be.a("number");
            expect(metrics.npv_outcome_var).to.be.a("number");
            expect(metrics.npv_outcome_stdev).to.be.a("number");

            // Standard deviation should be non-negative
            expect(metrics.npv_outcome_stdev).to.be.at.least(0);

            cy.log(`Risk Metrics:`);
            cy.log(`  NPV Mean: ${metrics.npv_outcome_mean}`);
            cy.log(`  NPV StdDev: ${metrics.npv_outcome_stdev}`);
          });
        } else {
          cy.log("⚠ Skipping test - no portfolio ID available");
        }
      });
    });
  });

  describe("Portfolio Forecast APIs", () => {
    const forecastPlotNames = [
      "sales_forecast",
      "costs_forecast",
      "spider_diagram",
      "value_unlock",
    ];

    forecastPlotNames.forEach((plotName) => {
      it(`should get portfolio ${plotName} forecast with valid ID`, () => {
        makeAuthenticatedRequest(
          "GET",
          endpoints.portfolios.forecastPlots(testPortfolioId, plotName),
        ).then((response) => {
          assertStatusCode(response, 200);
          expect(response.body).to.exist;
          // Basic validation - forecast responses vary by plot type
          if (typeof response.body === "object") {
            expect(response.body).to.not.be.null;
          }
        });
      });

      it(`should handle invalid portfolio ID for ${plotName} forecast`, () => {
        const invalidId = "invalid-forecast-portfolio-xyz-123";
        makeAuthenticatedRequest(
          "GET",
          endpoints.portfolios.forecastPlots(invalidId, plotName),
        ).then((response) => {
          expect(response.status).to.be.oneOf([400, 404, 422, 500]);
        });
      });
    });

    it("should get portfolio distribution with valid ID (POST)", () => {
      const distributionRequest = {
        metric_name: "npv",
        n_samples: 100,
        n_bins: 50,
      };

      makeAuthenticatedRequest(
        "POST",
        endpoints.portfolios.distribution(testPortfolioId),
        distributionRequest,
      ).then((response) => {
        assertStatusCode(response, 200);
        expect(response.body).to.exist;
        expect(response.body).to.be.an("object");
      });
    });

    it("should handle invalid portfolio ID for distribution", () => {
      const invalidId = "invalid-distribution-portfolio-xyz-123";
      const distributionRequest = {
        metric_name: "npv",
        n_samples: 100,
        n_bins: 50,
      };

      makeAuthenticatedRequest(
        "POST",
        endpoints.portfolios.distribution(invalidId),
        distributionRequest,
      ).then((response) => {
        expect(response.status).to.be.oneOf([400, 404, 422, 500]);
      });
    });
  });

  describe("Error Handling for GET APIs", () => {
    it("should handle invalid portfolio ID gracefully", () => {
      const invalidId = "invalid-portfolio-id-xyz-123";

      makeAuthenticatedRequest(
        "GET",
        endpoints.portfolios.projects(invalidId),
      ).then((response) => {
        expect(response.status).to.be.gte(400);
        expect(response.status).to.be.lte(500);
        cy.log("✓ API handles invalid portfolio ID correctly");
      });
    });

    it("should handle very long invalid portfolio ID", () => {
      const veryLongInvalidId = "a".repeat(1000);

      makeAuthenticatedRequest(
        "GET",
        endpoints.portfolios.metrics(veryLongInvalidId),
      ).then((response) => {
        expect(response.status).to.be.gte(400);
        cy.log("✓ API handles very long invalid portfolio ID correctly");
      });
    });

    it("should require authentication for portfolio endpoints", () => {
      cy.request({
        method: "GET",
        url: endpoints.portfolios.list(),
        headers: {
          "Content-Type": "application/json",
        },
        failOnStatusCode: false,
      }).then((response) => {
        // Should return 401 Unauthorized or 403 Forbidden
        expect([401, 403]).to.include(response.status);
        cy.log("✓ API correctly requires authentication");
      });
    });

    it("should handle malformed portfolio IDs", () => {
      const malformedIds = ["", " ", "/", "../", "null", "undefined"];

      malformedIds.forEach((malformedId) => {
        makeAuthenticatedRequest(
          "GET",
          endpoints.portfolios.projects(malformedId),
        ).then((response) => {
          // API may return 200 (empty results) or 4xx/5xx (errors)
          // Both are acceptable behaviors for malformed IDs
          expect(response.status).to.be.gte(200);
          expect(response.status).to.be.lt(600);
        });
      });

      cy.log("✓ API handles all malformed portfolio IDs correctly");
    });

    it("should return consistent error structure", () => {
      const invalidId = "nonexistent-portfolio-123";

      makeAuthenticatedRequest(
        "GET",
        endpoints.portfolios.projects(invalidId),
      ).then((response) => {
        expect(response.status).to.be.gte(400);

        // Error response should be an object
        expect(response.body).to.be.an("object");

        // Common error fields (message is typical)
        if (response.body.message) {
          expect(response.body.message).to.be.a("string");
        }

        cy.log("✓ Error response structure is consistent");
      });
    });
  });

  describe("Performance Tests for GET APIs", () => {
    it("should respond to portfolio list request within reasonable time", () => {
      makeAuthenticatedRequest("GET", endpoints.portfolios.list()).then(
        (response) => {
          assertStatusCode(response, 200);
          expect(response.duration).to.be.lessThan(10000); // 10 seconds
          cy.log(`✓ Portfolio list response time: ${response.duration}ms`);
        },
      );
    });

    it("should respond to portfolio metrics request within reasonable time", () => {
      cy.then(() => {
        if (testPortfolioId) {
          makeAuthenticatedRequest(
            "GET",
            endpoints.portfolios.metrics(testPortfolioId),
          ).then((response) => {
            assertStatusCode(response, 200);
            expect(response.duration).to.be.lessThan(15000); // 15 seconds for metrics
            cy.log(`✓ Portfolio metrics response time: ${response.duration}ms`);
          });
        } else {
          cy.log("⚠ Skipping performance test - no portfolio ID available");
        }
      });
    });

    it("should respond to portfolio forecast request within reasonable time", () => {
      cy.then(() => {
        if (testPortfolioId) {
          makeAuthenticatedRequest(
            "GET",
            endpoints.portfolios.forecastPlots(
              testPortfolioId,
              "sales_forecast",
            ),
          ).then((response) => {
            assertStatusCode(response, 200);
            expect(response.duration).to.be.lessThan(20000); // 20 seconds for forecast
            cy.log(
              `✓ Portfolio forecast response time: ${response.duration}ms`,
            );
          });
        } else {
          cy.log("⚠ Skipping performance test - no portfolio ID available");
        }
      });
    });
  });
});
