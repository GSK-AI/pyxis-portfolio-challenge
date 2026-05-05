import { Tour } from "nextstepjs";

const steps: Tour[] = [
  {
    tour: "startScreen",
    steps: [
      {
        icon: null,
        title: "Welcome to the Investment Game",
        content:
          "The purpose of this game is to provide a sandbox environment to safely test and compare different investment strategies. We hope you enjoy playing Portfolio Manager and we challenge you to try and beat our AI agents!",
        side: "right",
        showControls: true,
        showSkip: true,
      },
      {
        icon: null,
        title: "Game Levels",
        content:
          "There are three levels of increasingly difficult portfolios to manage. To unlock the next level, you must first play this one.",
        side: "right",
        selector: "#level0",
        showControls: true,
        showSkip: true,
      },
      {
        icon: null,
        title: "Start Game",
        content: "Press start to commence.",
        side: "right",
        selector: "#startGame",
        showControls: true,
        showSkip: true,
      },
    ],
  },
  {
    tour: "actionScreenOne",
    steps: [
      {
        icon: null,
        title: "Your Portfolio",
        content:
          "This is your company's portfolio. Your goal is to maintain a portfolio of the highest possible value throughout the game, measured by its eNPV (expected Net Present Value).",
        side: "right",
        showControls: true,
        showSkip: true,
      },
      {
        icon: null,
        title: "Stats and Plots",
        content:
          "You can use these metrics and plots to help guide your decisions. Click on the info buttons to find out more about what they show you.",
        side: "bottom",
        showControls: true,
        showSkip: true,
        selector: "#actionStat",
      },
      {
        icon: null,
        title: "Table: In Development",
        content:
          "This table shows your current R&D portfolio. You have a range of assets in phases 1-3 of clinical trials. The key column to keep an eye on is 'Cost This Year' which tells you how much the next year of development of each asset will cost you. You can find the total cost of your selected assets on the Cost plot above. Click on the info buttons to find out more about what each column shows you.",
        side: "top-left",
        showControls: true,
        showSkip: true,
        selector: "#assetDevelopment",
      },
      {
        icon: null,
        title: "Asset Information",
        content:
          "If you press on the info icon next to each asset, you can learn more about its expected costs and the budget you would receive should it make it to the market.",
        side: "right",
        showControls: true,
        showSkip: true,
        selector: `#assetInfo1`,
      },
      {
        icon: null,
        title: "",
        content: "Now press 'On Market' to see the drug assets on the market.",
        side: "right",
        showControls: true,
        showSkip: true,
        selector: "#assetMarket",
      },
    ],
  },
  {
    tour: "actionScreenOnMarket",
    steps: [
      {
        icon: null,
        title: "Table: On Market",
        content:
          "You may have drug assets on the market. On-market drugs generate the revenue needed for your company to keep running via Sales. However, not all Sales are available for you to reinvest. Some of the revenue needs to go to employees, laboratories, technology, etc. The 'Budget Next Year' column shows you the amount you will receive in capital to reinvest in next year.",
        side: "right",
        showControls: true,
        showSkip: true,
        selector: "#onMarketTable",
      },
      {
        icon: null,
        title: "",
        content: "Now press Expired/Failed.",
        side: "right",
        showControls: true,
        showSkip: true,
        selector: "#assetExpired",
      },
    ],
  },
  {
    tour: "actionScreenExpiredFailed",
    steps: [
      {
        icon: null,
        title: "Table: Expired/Failed",
        content:
          "If a drug asset fails or its patent expires, it will move into this section.",
        side: "right",
        showControls: true,
        showSkip: true,
        selector: "#expiredTable",
      },
      {
        icon: null,
        title: "Next Year",
        content:
          "The Next Year button advances one year in time. It won't let you proceed if you are trying to invest in assets that cost more than your current capital. When you have selected a valid portfolio, continue to see how it progresses into the future.",
        side: "left",
        showControls: true,
        showSkip: true,
        selector: "#nextYearButton",
      },
    ],
  },
  {
    tour: "actionScreenTwo",
    steps: [
      {
        icon: null,
        title: "First Year",
        content:
          "Well done! You have completed your first year as Portfolio Manager. If at any point you're unsure of what decision to take, you can pay a cost to receive a hint from one of our AI agents. They will show you what selection they would make on your portfolio, but it's up to you to action that suggestion, or not. Should you want to follow their suggestion, make sure your In Development toggles match the blue ones that represent the agent's selection. Click on the info buttons to learn more about how each agent thinks.",
        side: "left",
        showControls: true,
        showSkip: true,
        selector: "#agentsHint",
      },
      {
        icon: null,
        title: "FINAL",
        content: "Now try and make it to the end of the game. Good luck!",
        side: "left",
        showControls: true,
        showSkip: true,
        selector: "#nextYearButton",
      },
    ],
  },
  {
    tour: "finalScreen",
    steps: [
      {
        icon: null,
        title: "End of Game",
        content:
          "Well done for completing your first game! Here you can find a summary of your portfolio throughout your tenure, including how you did compared to our AI agents. Our agents have been trained to optimise eNPV. Did you beat either of them?",
        side: "right",
        showControls: true,
        showSkip: true,
      },
      {
        icon: null,
        title: "Leaderboard",
        content:
          "You get one chance per level to make it onto this eNPV leaderboard - so give it your best shot! You can repeat your games afterwards, but they won't count towards your final score. You are judged against other users and AI agents on the average eNPV of your portfolio throughout the whole game. Knapsack optimises a single year at a time, whereas Pyxie makes a strategy for the future. Which one performs better?",
        side: "right",
        showControls: true,
        showSkip: true,
        selector: "#comparisonLeaderboard",
      },
      {
        icon: null,
        title: "Next Level",
        content:
          "Now you can progress on to the next level or try this one again. You can play each level as many times as you want, but only your first attempt is shown on the leaderboard. Thank you for playing!",
        side: "right",
        showControls: true,
        showSkip: true,
        selector: "#gameOverScreen",
      },
    ],
  },
];

export default steps;
