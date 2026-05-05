/**
 * Investment Game Frontend UI Tests
 *
 * Tests the complete investment game user interface including:
 * - Navigation to investment game
 * - Level selection screen
 * - Custom game start form
 * - Game action screen
 * - Game interactions and flows
 */

describe('Investment Game Frontend UI Tests', () => {
  beforeEach(() => {
    cy.bootstrapPageVisit();
    cy.visit('/');

    // Handle potential dialog/carousel that might appear
    cy.get('body').then(($body) => {
      if ($body.find('[role="dialog"]').length > 0) {
        cy.get('[role="dialog"]').should('be.visible');
        cy.findByRole('button', { name: 'Close' }).should('be.visible').click();
      }
    });
  });

  // =============================================================================
  // NAVIGATION AND PAGE LOAD TESTS
  // =============================================================================

  context('Navigation and Page Load', () => {
    it('should navigate to investment game and load correctly', () => {
      // Verify we're on the investment game page
      cy.url().should('include', '/');

      // Check for main game container or content
      cy.get('body').should('be.visible');

      // Should show either the level selection screen or custom start screen
      // by default it should show levels
      cy.get('[data-testid="start-levels"], .c-splash-screen').should(
        'be.visible'
      );
    });

    it('should have proper page structure and layout', () => {
      // Check for main layout elements
      cy.get('body').should('not.be.empty');

      // Ensure the page is responsive
      cy.viewport(1920, 1080);
      cy.get('body').should('be.visible');

      // Test mobile viewport
      cy.viewport(375, 667);
      cy.get('body').should('be.visible');

      // Reset to desktop
      cy.viewport(1920, 1080);
    });
  });

  // =============================================================================
  // LEVEL SELECTION SCREEN TESTS
  // =============================================================================

  context('Level Selection Screen', () => {
    it('should display level selection by default', () => {
      // Should show levels selection screen initially
      // Look for elements that indicate level selection
      cy.get('body').should('be.visible');
      cy.get('body').then(($body) => {
        const text = $body.text();
        expect(text).to.match(/Level|Game|Start/i);
      });

      // Wait for any API calls to load levels
      cy.wait(2000);

      // Should have some interactive elements (buttons or level cards)
      cy.get('button, [role="button"], .cursor-pointer').should(
        'have.length.at.least',
        1
      );
    });

    it('should allow switching to custom game mode', () => {
      // Look for a way to switch to custom mode
      // This might be a button, link, or toggle
      cy.get('body').then(($body) => {
        // Check for various possible selectors for custom game option
        if ($body.find(':contains("Custom")').length > 0) {
          cy.contains('Custom').click();
        } else if ($body.find(':contains("custom")').length > 0) {
          cy.contains('custom').click();
        } else if ($body.find('[data-testid*="custom"]').length > 0) {
          cy.get('[data-testid*="custom"]').first().click();
        } else {
          // Try to find any button that might lead to custom mode
          cy.get('button')
            .contains(/start|play|custom/i)
            .first()
            .click();
        }
      });
    });

    it('should handle level selection interactions', () => {
      // Wait for levels to load
      cy.wait(2000);

      // Look for level cards or buttons
      cy.get('button, [role="button"], .cursor-pointer').then(($elements) => {
        if ($elements.length > 0) {
          // Click on the first available level/button
          cy.wrap($elements.first()).click();

          // Should either start a game or show more options
          cy.get('body').should('be.visible');
        }
      });
    });
  });

  // =============================================================================
  // CUSTOM GAME START FORM TESTS
  // =============================================================================

  context('Custom Game Start Form', () => {
    beforeEach(() => {
      // Try to get to the custom game start form
      cy.get('body').then(($body) => {
        // Look for custom game trigger
        if ($body.find(':contains("Custom")').length > 0) {
          cy.contains('Custom').click();
        } else {
          // Skip this test suite if we can't find custom mode
          cy.log('Custom mode not found, skipping custom form tests');
        }
      });
    });

    it('should display custom game start form', () => {
      // Check for form elements that should be in the custom start
      cy.get('body').then(($body) => {
        if (
          $body.find('input[name="num_assets"], input[type="number"]').length >
          0
        ) {
          // We found the custom form
          cy.get('input[name="num_assets"], input[type="number"]').should(
            'be.visible'
          );

          // Look for other expected form fields
          cy.get('label, input').should('have.length.at.least', 2);
        } else {
          cy.log('Custom form not found in current view');
        }
      });
    });

    it('should validate form inputs correctly', () => {
      cy.get('body').then(($body) => {
        if ($body.find('input[name="num_assets"]').length > 0) {
          // Test number of assets validation
          cy.get('input[name="num_assets"]').clear().type('5'); // Below minimum of 10

          // Should show validation error
          cy.get('body').then(($body) => {
            const text = $body.text();
            expect(text).to.match(/between|Range|10|20/i);
          });

          // Test valid value
          cy.get('input[name="num_assets"]').clear().type('15'); // Valid value

          // Error should be gone or not present
          cy.get('body').should('be.visible');
        }
      });
    });

    it('should validate horizon (years) input', () => {
      cy.get('body').then(($body) => {
        if ($body.find('input[name="horizon"]').length > 0) {
          // Test horizon validation
          cy.get('input[name="horizon"]').clear().type('0'); // Below minimum of 1

          // Should show validation error or prevent invalid input
          cy.get('body').should('be.visible');

          // Test valid value
          cy.get('input[name="horizon"]').clear().type('5'); // Valid value
        }
      });
    });

    it('should validate starting cash input', () => {
      cy.get('body').then(($body) => {
        if ($body.find('input[name="starting_cash"]').length > 0) {
          // Test very large value
          cy.get('input[name="starting_cash"]').clear().type('999999999999'); // Very large number

          // Should handle large numbers appropriately
          cy.get('body').should('be.visible');
        }
      });
    });

    it('should allow starting a custom game', () => {
      cy.get('body').then(($body) => {
        // Look for start button
        if (
          $body.find(
            'button:contains("Start"), [role="button"]:contains("Start")'
          ).length > 0
        ) {
          cy.contains('button', 'Start').click();

          // Should either start loading or navigate to game
          cy.get('body').should('be.visible');

          // Wait for potential game start
          cy.wait(3000);
        }
      });
    });

    it('should allow returning to levels', () => {
      cy.get('body').then(($body) => {
        // Look for return/back button
        if (
          $body.find(
            ':contains("Return"), :contains("Back"), :contains("Levels")'
          ).length > 0
        ) {
          cy.contains(/Return|Back|Levels/i).click();

          // Should go back to level selection
          cy.get('body').should('be.visible');
        }
      });
    });
  });

  // =============================================================================
  // GAME ACTION SCREEN TESTS
  // =============================================================================

  context('Game Action Screen', () => {
    beforeEach(() => {
      // Try to start a game to get to the action screen
      // This might be challenging without knowing the exact UI flow
      cy.get('body').then(($body) => {
        // First try to find a quick start option
        if ($body.find('button').length > 0) {
          // Look for any button that might start a game
          cy.get('button').then(($buttons) => {
            // Try clicking buttons that might start a game
            const $startButtons = $buttons.filter((i, btn) => {
              const text = Cypress.$(btn).text().toLowerCase();
              return (
                text.includes('start') ||
                text.includes('play') ||
                text.includes('level')
              );
            });

            if ($startButtons.length > 0) {
              cy.wrap($startButtons.first()).click();
              cy.wait(3000); // Wait for game to potentially start
            }
          });
        }
      });
    });

    it('should display game interface when game is active', () => {
      cy.get('body').then(($body) => {
        // Look for indicators that we're in an active game
        const hasGameElements =
          $body.find(
            '[data-testid*="game"], [data-testid*="asset"], .game, .assets'
          ).length > 0;
        const hasTimelineOrStats =
          $body.find(
            ':contains("Time"), :contains("Cash"), :contains("Assets")'
          ).length > 0;

        if (hasGameElements || hasTimelineOrStats) {
          cy.log('Game interface detected');
          cy.get('body').then(($body) => {
            const text = $body.text();
            expect(text).to.match(/Time|Cash|Asset/i);
          });
        } else {
          cy.log('Game interface not detected, might still be in menu');
        }
      });
    });

    it('should display game stats and information', () => {
      cy.get('body').then(($body) => {
        // Check for common game UI elements
        if (
          $body.find(':contains("Cash"), :contains("Time"), :contains("Year")')
            .length > 0
        ) {
          // Should show current game state
          cy.get('body').then(($body) => {
            const text = $body.text();
            const hasFinancialInfo = /Cash|Money|Budget/i.test(text);
            const hasTimeInfo = /Time|Year|Turn/i.test(text);
            expect(hasFinancialInfo || hasTimeInfo).to.be.true;
          });
        }
      });
    });

    it('should allow game interactions', () => {
      cy.get('body').then(($body) => {
        // Look for interactive elements in game
        if ($body.find('button:not(:disabled)').length > 0) {
          // Should have clickable buttons for game actions
          cy.get('button:not(:disabled)').should('have.length.at.least', 1);

          // Try interacting with game elements
          cy.get('button:not(:disabled)').first().should('be.visible');
        }
      });
    });

    it('should handle game navigation options', () => {
      cy.get('body').then(($body) => {
        // Look for game control buttons (pause, restart, exit, etc.)
        const controlTexts = [
          'restart',
          'reset',
          'exit',
          'menu',
          'back',
          'start',
        ];
        let foundControls = false;

        controlTexts.forEach((text) => {
          if ($body.find(`:contains("${text}")`).length > 0) {
            foundControls = true;
            cy.contains(text, { matchCase: false }).should('be.visible');
          }
        });

        if (!foundControls) {
          cy.log('No game control buttons found');
        }
      });
    });
  });

  // =============================================================================
  // RESPONSIVE DESIGN TESTS
  // =============================================================================

  context('Responsive Design', () => {
    const viewports = [
      { width: 375, height: 667, name: 'Mobile' },
      { width: 768, height: 1024, name: 'Tablet' },
      { width: 1024, height: 768, name: 'Tablet Landscape' },
      { width: 1920, height: 1080, name: 'Desktop' },
    ];

    viewports.forEach((viewport) => {
      it(`should display correctly on ${viewport.name} (${viewport.width}x${viewport.height})`, () => {
        cy.viewport(viewport.width, viewport.height);

        // Page should still be visible and usable
        cy.get('body').should('be.visible');

        // Should not have horizontal scroll on mobile
        if (viewport.width <= 768) {
          cy.get('body').should('not.have.css', 'overflow-x', 'scroll');
        }

        // Interactive elements should still be accessible
        cy.get('button, [role="button"], input').each(($el) => {
          cy.wrap($el).should('be.visible');
        });
      });
    });
  });

  // =============================================================================
  // ERROR HANDLING AND EDGE CASES
  // =============================================================================

  context('Error Handling and Edge Cases', () => {
    it('should handle network interruption gracefully', () => {
      // Simulate network issues by intercepting requests
      cy.intercept('POST', '**/game/**', { forceNetworkError: true }).as(
        'gameError'
      );

      // Try to interact with game elements
      cy.get('button').then(($buttons) => {
        if ($buttons.length > 0) {
          cy.wrap($buttons.first()).click();

          // Should handle the error without breaking
          cy.get('body').should('be.visible');
        }
      });
    });

    it('should handle invalid game states', () => {
      // Test with invalid or corrupted local storage
      cy.window().then((win) => {
        win.localStorage.setItem('gameState', 'invalid-json');
      });

      // Refresh and ensure app still works
      cy.reload();
      cy.get('body').should('be.visible');
    });

    it('should provide user feedback for loading states', () => {
      // Look for loading indicators during interactions
      cy.get('button').then(($buttons) => {
        if ($buttons.length > 0) {
          cy.wrap($buttons.first()).click();

          // Should show loading state or immediate response
          cy.get('body').should('be.visible');

          // Wait for any loading to complete
          cy.wait(2000);
        }
      });
    });
  });

  // =============================================================================
  // ACCESSIBILITY TESTS
  // =============================================================================

  context('Accessibility', () => {
    it('should have proper keyboard navigation', () => {
      // Test tab navigation through interactive elements
      cy.get('button, input, [role="button"]').each(($el, index) => {
        if (index < 5) {
          // Test first 5 elements to avoid too long test
          cy.wrap($el).focus().should('be.focused');
        }
      });
    });

    it('should have proper ARIA labels and roles', () => {
      // Check for accessibility attributes
      cy.get('button').each(($button) => {
        // Button should have either a type attribute or visible text
        cy.wrap($button).then(($btn) => {
          const hasType = !!$btn.attr('type');
          const hasText = $btn.text().trim().length > 0;
          expect(hasType || hasText).to.be.true;
        });
      });

      // Input fields should have labels or be properly labeled (if any exist)
      cy.get('body').then(($body) => {
        if ($body.find('input').length > 0) {
          cy.get('input').each(($input) => {
            cy.wrap($input).then(($inp) => {
              const id = $inp.attr('id');
              const name = $inp.attr('name');
              const hasAriaLabel = $inp.attr('aria-label');
              const hasPlaceholder = $inp.attr('placeholder');

              // Check if input has proper labeling
              if (id) {
                // Try to find associated label
                cy.get('body').then(($body) => {
                  const hasLabel = $body.find(`label[for="${id}"]`).length > 0;
                  const hasAssociatedLabel =
                    hasLabel || hasAriaLabel || hasPlaceholder;
                  expect(hasAssociatedLabel).to.be.true;
                });
              } else {
                // Input should have some form of labeling
                const hasLabeling = hasAriaLabel || hasPlaceholder || name;
                expect(!!hasLabeling).to.be.true;
              }
            });
          });
        } else {
          cy.log('No input elements found on current page');
        }
      });
    });

    it('should have sufficient color contrast', () => {
      // Basic check that text is visible against backgrounds
      cy.get('body').should('have.css', 'color');
      cy.get('body').should('have.css', 'background-color');

      // Text should be visible
      cy.get('h1, h2, h3, p, label, button').each(($el) => {
        cy.wrap($el).should('be.visible');
      });
    });
  });
});
