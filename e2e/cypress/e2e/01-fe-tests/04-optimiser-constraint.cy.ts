const mockProjectIds = ["8665", "8666"];
const mockResult = {
  optimisation_settings: {
    project_ids: mockProjectIds,
    target: "enpv",
    year: null,
    mode: "maximise",
    constraints: [
      {
        required_project_ids: [],
      },
      {
        constraint_target: "risk_adj_epe",
        year: 2025,
        lte_or_gte: "between",
        threshold: [660, 1649],
      },
      {
        constraint_target: "risk_adj_epe",
        year: 2026,
        lte_or_gte: "between",
        threshold: [722, 1805],
      },
      {
        constraint_target: "risk_adj_epe",
        year: 2027,
        lte_or_gte: "between",
        threshold: [845, 2113],
      },
    ],
  },
  metrics: {
    cumulative_ptrs: null,
    npv: 234344.5495682428,
    enpv: 88278.48857109873,
    roi: 11.239585280794879,
    roi_denominator: 0,
    eroi: 7.598575334288839,
    eroi_denominator: 0,
    sales_2031: 29732.295192257538,
    esales_2031: 16641.543788113297,
    remaining_dev_costs: 34436.60865334604,
    remaining_dev_ecosts: 17895.48042674704,
    next_phase: null,
    next_phase_start: null,
    epe_to_next_phase: null,
    ipe_to_next_phase: null,
    epe_2025: 1777.4237415138668,
    ipe_2025: 1304.4340386761633,
    npv_outcome_mean: 88278.48857109873,
    npv_outcome_var: 245910483.00403875,
    npv_outcome_stdev: 15681.533184100295,
  },
  optimal_project_ids: ["8665", "8666"],
  string_representation: "This is a test run from Cypress",
};

import { formatNumber } from "../../../../frontend/lib/numbers";

describe("Constraint Testing Without Saving", () => {
  beforeEach(() => {
    cy.bootstrapPageVisit();
    cy.turnOffIntroWizard();
    cy.visit("/portfolio-simulator/optimiser");

    // Navigate to constraints tab
    const constraintTab = cy.findByRole("tab", {
      name: "Objective + Constraints",
    });
    constraintTab.click();
  });

  it("Should test multiple constraint scenarios without saving", () => {
    // Set up a single intercept for all optimization calls
    cy.intercept("POST", "**/optimisation/**", {
      statusCode: 200,
      body: mockResult,
    }).as("optimiserRun");

    // Count initial constraints
    cy.get('[data-testid="constraint-row"]').then(($initialRows) => {
      const initialCount = $initialRows.length;
      cy.log(`Initial constraint count: ${initialCount}`);

      // Test Scenario 1: Add a constraint and run optimizer
      cy.log("Testing Scenario 1: Adding basic constraint");

      // Add first constraint
      cy.findByRole("button", { name: /Add Constraint/i }).click();

      // Verify constraint was added
      cy.get('[data-testid="constraint-row"]').should(
        "have.length",
        initialCount + 1,
      );

      // Find the newly added constraint (last one) and configure it
      cy.get('[data-testid="constraint-row"]')
        .last()
        .within(() => {
          cy.get('[data-testid="constraint-target-select"]').click();
        });

      // Select the first available option (whatever it is)
      cy.get('[role="option"]').first().should("be.visible").click();

      // Select constraint mode - try "greater than or equal to" first
      cy.get('[data-testid="constraint-row"]')
        .last()
        .within(() => {
          cy.get('[data-testid="constraint-mode-select"]').click();
        });
      cy.get('[role="option"]')
        .contains("greater than or equal to")
        .should("be.visible")
        .click();

      // Add threshold value
      cy.get('[data-testid="constraint-row"]')
        .last()
        .within(() => {
          cy.get('[data-testid="threshold-min-input"]').type("50000");
        });

      cy.findByRole("button", { name: "Create Scenario" }).click();
      cy.wait("@optimiserRun", { timeout: 10000 });

      // Verify results appear without saving
      cy.findAllByRole("row").should("have.length.greaterThan", 1);
      cy.log("Scenario 1 completed successfully");

      // Test Scenario 2: Add another constraint with different mode
      cy.log("Testing Scenario 2: Adding another constraint");

      cy.findByRole("button", { name: /Add Constraint/i }).click();

      // Verify constraint was added
      cy.get('[data-testid="constraint-row"]').should(
        "have.length",
        initialCount + 2,
      );

      // Select any available constraint target for the new constraint
      cy.get('[data-testid="constraint-row"]')
        .last()
        .within(() => {
          cy.get('[data-testid="constraint-target-select"]').click();
        });
      cy.get('[role="option"]').eq(1).should("be.visible").click(); // Select second option if available

      // Select constraint mode
      cy.get('[data-testid="constraint-row"]')
        .last()
        .within(() => {
          cy.get('[data-testid="constraint-mode-select"]').click();
        });

      // Try to find "between" option, if not available use any option
      cy.get("body").then(($body) => {
        if ($body.find('[role="option"]:contains("between")').length > 0) {
          cy.get('[role="option"]').contains("between").click();

          // Add both min and max values for between constraint
          cy.get('[data-testid="constraint-row"]')
            .last()
            .within(() => {
              cy.get('[data-testid="threshold-min-input"]').type("5");
              cy.get('[data-testid="threshold-max-input"]').type("15");
            });
        } else {
          // Use first available option
          cy.get('[role="option"]').first().click();

          // Add single threshold value
          cy.get('[data-testid="constraint-row"]')
            .last()
            .within(() => {
              cy.get('[data-testid="threshold-min-input"]').type("10");
            });
        }
      });

      cy.findByRole("button", { name: "Create Scenario" }).click();
      cy.wait("@optimiserRun", { timeout: 10000 });

      cy.log("Scenario 2 completed successfully");

      // Test Scenario 3: Test constraint deletion
      cy.log("Testing Scenario 3: Testing constraint deletion");

      // Delete the last constraint we added
      cy.get('[data-testid="constraint-row"]')
        .last()
        .within(() => {
          cy.get('[data-testid="delete-constraint-button"]').click();
        });

      // Verify constraint was deleted
      cy.get('[data-testid="constraint-row"]').should(
        "have.length",
        initialCount + 1,
      );

      cy.findByRole("button", { name: "Create Scenario" }).click();
      cy.wait("@optimiserRun", { timeout: 10000 });

      cy.log("All constraint scenarios tested successfully without saving");
    });
  });

  it("Navigate to Optimise flow", () => {
    // const optimiserLink = cy.findByRole('link', { name: 'Optimiser' });
    // optimiserLink.should('have.attr', 'href', '/optimiser');
    // optimiserLink.click();

    const constraintTab = cy.findByRole("tab", {
      name: "Objective + Constraints",
    });
    constraintTab.click();

    cy.intercept("POST", "**/optimisation/**", {
      statusCode: 200,
      body: mockResult,
    }).as("interceptOptimiserRun");

    cy.findByRole("button", {
      name: "Create Scenario",
    }).click();

    cy.wait("@interceptOptimiserRun");
    const newMockName = "Test Optimiser Run";

    // Find all the rows
    const rows = cy.findAllByRole("row");
    rows.eq(1).within(() => {
      cy.findAllByRole("cell").eq(1).should("have.text", mockProjectIds.length);
      cy.findAllByRole("cell")
        .eq(2)
        .should("have.text", formatNumber(mockResult.metrics.eroi, 1));

      const nameInput = cy
        .findByRole("textbox", {
          name: "Portfolio Name",
        })
        .should("be.visible");

      nameInput.clear().type(newMockName);

      const saveButton = cy.findByRole("button", {
        name: "Save",
      });
      saveButton.should("be.visible");

      saveButton.click();
    });

    // Check for dialog to open 'save new portfolio' modal
    const confirmDialog = cy
      .findByRole("dialog", {
        name: "Save New Portfolio",
      })
      .should("be.visible");

    // Check for dialog to have textbox with newMockName
    confirmDialog
      .findByRole("textbox", {
        name: "Name",
      })
      .should("be.visible")
      .should("have.value", newMockName);

    // Check for dialog to have description from API Response
    cy.findByRole("textbox", {
      name: "Description",
    })
      .should("be.visible")
      .should("have.value", mockResult.string_representation);

    // Click the Save Button
    const dialogSaveButton = cy.findByRole("button", {
      name: "Save",
    });
    dialogSaveButton.should("be.visible");

    // Wait for intercept
    cy.intercept("POST", "/portfolios/save", {
      statusCode: 200,
      body: {
        portfolio_id: "12345",
      },
    }).as("interceptOptimiserSave");
    dialogSaveButton.click();

    cy.wait("@interceptOptimiserSave").then(({ request, response }) => {
      // check the request body
      expect(request.body).to.deep.equal({
        portfolio_name: newMockName,
        portfolio_description: mockResult.string_representation,
        project_ids: mockProjectIds,
      });
      expect(response?.statusCode).to.equal(200);
      expect(response?.body).to.have.property("portfolio_id");
    });
    // cy.get('Saved').should('be.visible');
  });
});
