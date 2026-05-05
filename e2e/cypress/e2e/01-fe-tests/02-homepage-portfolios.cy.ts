describe("login the app", () => {
  beforeEach(() => {
    cy.bootstrapPageVisit();
    cy.visit("/portfolio-simulator");

    // Close the dialog
    cy.get('[role="dialog"]').should("be.visible");
    cy.findByRole("button", { name: "Close" }).should("be.visible").click();
  });

  it("Home page should load all the portfolios", () => {
    // Check if the portfolio library page is open
    cy.get("h1").contains("Portfolio Library").should("be.visible");

    // Query the portfolios
    cy.readFile("cypress/fixtures/session.json").then((session) => {
      cy.request({
        method: "GET",
        url: `${Cypress.env("backendEndpoint")}/portfolios`,
        headers: {
          Authorization: `Bearer ${session.id_token}`,
          "Content-Type": "application/json",
        },
      }).then((response) => {
        expect(response.status).to.eq(200);

        expect(response.body).to.be.an("array");
        const length = response.body.length;
        cy.log(`Total Portfolios found: ${length}`);
      });
    });

    // Check if the number of portfolios are rendered
  });
});
