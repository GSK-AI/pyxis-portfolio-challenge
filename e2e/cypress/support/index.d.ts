// cypress/support/index.d.ts
/// <reference types="cypress" />

declare namespace Cypress {
  interface Chainable {
    /**
     * Custom command to visit a page using bootstrap logic.
     * @example cy.bootstrapPageVisit()
     */
    bootstrapPageVisit(): Chainable<void>;
    turnOffIntroWizard(): Chainable<void>;
  }
}
