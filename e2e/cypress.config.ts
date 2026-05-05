import { defineConfig } from "cypress";
require("dotenv").config();

export default defineConfig({
  e2e: {
    setupNodeEvents(on, config) {
      on("task", {});
    },
    baseUrl: process.env.FRONTEND_URL,
    chromeWebSecurity: false,
    excludeSpecPattern: ["e2e/01-fe-tests/**.cy.ts"],
  },

  requestTimeout: 600000,
  responseTimeout: 600000,

  env: {
    backendEndpoint: process.env.BACKEND_URL,
    gameBackendEndpoint: process.env.GAME_BACKEND_URL,
    NEXTAUTH_SECRET: process.env.NEXTAUTH_SECRET,
  },

  component: {
    devServer: {
      framework: "next",
      bundler: "webpack",
    },
  },
});
