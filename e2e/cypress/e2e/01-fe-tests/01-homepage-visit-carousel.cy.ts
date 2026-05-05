describe("login the app", () => {
  beforeEach(() => {
    cy.bootstrapPageVisit();
    cy.visit("/");
  });

  it("Home page should have a carousel and close", () => {
    // See if the dialog is open
    cy.get('[role="dialog"]').should("be.visible");

    // Click the close button
    cy.findByRole("button", { name: "Close" }).should("be.visible").click();

    // Check if the dialog is closed
  });
});
