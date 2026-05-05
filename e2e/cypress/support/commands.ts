const WIDTH = 1920;
const HEIGHT = 1090;

Cypress.Commands.add("bootstrapPageVisit", () => {
  cy.fixture("session.json").then((session) => {
    const token = session.id_token;
    try {
      window.localStorage.setItem("pyxis-testing-token", token);
    } catch (err) {
      console.error(err);
    }
  });
  cy.viewport(WIDTH, HEIGHT);
});

Cypress.Commands.add("turnOffIntroWizard", () => {
  window.localStorage.setItem("do-not-show-again", "true");
});
