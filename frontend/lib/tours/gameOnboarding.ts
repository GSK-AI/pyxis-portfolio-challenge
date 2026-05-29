import { Tour } from "nextstepjs";

const steps: Tour[] = [
  {
    tour: "startScreen",
    steps: [
      {
        icon: null,
        title: "Welcome to the Portfolio Challenge",
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
  {
    tour: "replayTour",
    steps: [
      {
        icon: null,
        title: "Welcome to Replay",
        content:
          "You're watching a recorded game between AI agents. Step through to see how the game unfolded year by year — investments made, drugs launched, and markets competed over.",
        side: "right",
        showControls: true,
        showSkip: true,
      },
      {
        icon: null,
        title: "Navigating the Replay",
        content:
          "Use the back and forward buttons — or your keyboard arrow keys — to step through the game. You can also jump directly to any step using the input field.",
        side: "bottom",
        selector: "#replay-step-navigator",
        showControls: true,
        showSkip: true,
      },
      {
        icon: null,
        title: "State vs Action View",
        content:
          "This is the key toggle. State view shows the state of the portfolio, market, CI and BD at the current game step. Action view shows which actions each agent took based on that observed state: which assets they chose to invest in and any BD bids placed. Switch between them to understand both the situation and the decisions made.",
        side: "bottom",
        selector: "#replay-view-toggle",
        showControls: true,
        showSkip: true,
      },
      {
        icon: null,
        title: "Agent Status & Ranking",
        content:
          "Each card shows an agent's current Cumulative Net Cash Flow (NCF). The leading agent is highlighted. Cards stay in their fixed positions — step through the game to see how NCF evolves and which agent pulls ahead.",
        side: "bottom",
        selector: "#replay-leaderboard",
        showControls: true,
        showSkip: true,
      },
      {
        icon: null,
        title: "Cash Flow Over Time",
        content:
          "Tracks each agent's NCF across all steps. The dashed vertical line marks the current step. Use this to spot when agents pulled ahead or fell behind.",
        side: "bottom",
        selector: "#replay-reward-chart",
        showControls: true,
        showSkip: true,
      },
      {
        icon: null,
        title: "Agent Portfolios",
        content:
          "One panel per agent showing their R&D pipeline. Colour highlights indicate new assets, BD acquisitions, and phase transitions. In Action view, each asset shows the investment decision taken that year.",
        side: "top",
        selector: "#replay-portfolio-grid",
        showControls: true,
        showSkip: true,
      },
      {
        icon: null,
        title: "Sales Market",
        content:
          "Indication-level competition at the current step. Shows market share, exclusivity status, and which agents have drugs on market.",
        side: "top",
        selector: "#replay-sales",
        showControls: true,
        showSkip: true,
      },
      {
        icon: null,
        title: "Competitive Intelligence",
        content:
          "The rolling alert window for this step — drug launches, BD deals, and observed pipeline transitions.",
        side: "top",
        selector: "#replay-alerts",
        showControls: true,
        showSkip: true,
      },
      {
        icon: null,
        title: "BD Market",
        content:
          "Shows the sealed-bid auctions that occurred at this step, including bids made by each agent and any winning bids.",
        side: "top",
        selector: "#replay-bd",
        showControls: true,
        showSkip: true,
      },
      {
        icon: null,
        title: "Start Exploring",
        content:
          "Step through the game and see how the AI made its decisions. Use the State/Action toggle to dig into both the choices and their outcomes.",
        side: "right",
        showControls: true,
        showSkip: false,
      },
    ],
  },
  {
    tour: "multiplayerTour",
    steps: [
      {
        icon: null,
        title: "Welcome to the Portfolio Challenge",
        content:
          "You are the portfolio manager of a pharmaceutical company competing against AI agents. Each year you choose which pipeline assets to fund. The player with the highest Cumulative Net Cash Flow (NCF) at the end of the game wins. Good luck!",
        side: "right",
        showControls: true,
        showSkip: true,
      },
      {
        icon: null,
        title: "Your Finances",
        content:
          "Available Capital is your budget for the year. The eNPV and eROI metrics summarise the expected value of your current selection. The capital chart shows your historical cash balance across the game so far.",
        side: "right",
        selector: "#multi-action-finances",
        showControls: true,
        showSkip: true,
      },
      {
        icon: null,
        title: "Your Pipeline",
        content:
          "This table shows your full R&D portfolio. Toggle each asset to invest or stop funding it. Assets progress through Phase 1 → 2 → 3 → Approval → Market. Each phase has a probability of success. Successfully launched drugs generate the revenue your company needs to keep running.",
        side: "top-left",
        selector: "#multi-action-assets",
        showControls: true,
        showSkip: true,
      },
      {
        icon: null,
        title: "Reading an Asset Row",
        content:
          "Each row is one asset currently in your R&D pipeline. The toggle on the left controls whether you fund it this year. Current Phase shows where it sits (Phase 1 → 2 → 3 → Approval). Cost This Year is what you'll pay to keep it funded. PTRS is the probability of successfully completing this phase. eNPV and eROI summarise the expected value and return — use these to decide which assets are worth the investment. Assets that successfully reach market move to the On Market tab.",
        side: "bottom",
        selector: "#assetRow0",
        showControls: true,
        showSkip: true,
      },
      {
        icon: null,
        title: "Asset Detail",
        content:
          "Click the info icon next to any asset to see its full breakdown: the Probability of Technical and Regulatory Success (PTRS) at each remaining phase, and the projected peak revenue if it reaches market. Use this to weigh up the risk and reward of each investment.",
        side: "right",
        selector: "#assetInfo0",
        showControls: true,
        showSkip: true,
      },
      {
        icon: null,
        title: "Table Views",
        content:
          "These tabs switch between three views of your portfolio. In Development is where you make your funding decisions each year. On Market shows drugs that have successfully launched and are generating revenue for your company. Expired/Failed shows assets that didn't make it through trials or whose patents have expired.",
        side: "bottom",
        selector: "#assetTabNav",
        showControls: true,
        showSkip: true,
      },
      {
        icon: null,
        title: "Cost & Revenue Charts",
        content:
          "The Cost chart shows the total spend for your current asset selection. The Revenue chart shows the budget you will receive next year from drugs already on the market. Use these to avoid overspending your available capital.",
        side: "bottom",
        selector: "#multi-action-charts",
        showControls: true,
        showSkip: true,
      },
      {
        icon: null,
        title: "Sales Market",
        content:
          "Once drugs reach market, your revenue depends on your market share. The first company to launch in an indication earns an exclusivity period — competitors earn nothing in that indication during this window. After exclusivity expires, revenue is split based on drug quality and time on market.",
        side: "top",
        selector: "#multi-action-sales",
        showControls: true,
        showSkip: true,
      },
      {
        icon: null,
        title: "Competitive Intelligence",
        content:
          "Monitor competitor activity here. Drug launches and BD acquisitions are always reported. Pipeline progression is only partially observable — there is a 20% chance of seeing a Phase 1→2 transition, 50% for Phase 2→3, and 70% for Phase 3→Approval. The panel shows a rolling window of the last 5 years of alerts.",
        side: "top",
        selector: "#multi-action-alerts",
        showControls: true,
        showSkip: true,
      },
      {
        icon: null,
        title: "BD Market",
        content:
          "When available, Business Development assets appear here for sealed-bid auction. All players bid simultaneously — the highest bidder wins the asset and pays their bid. If multiple players bid the same amount, the winner is chosen at random. BD assets let you acquire drugs already in development, skipping early trial phases.",
        side: "top",
        selector: "#multi-action-bd",
        showControls: true,
        showSkip: true,
      },
      {
        icon: null,
        title: "Advancing the Game",
        content:
          "Press Next Year to commit your investment decisions for the year. The timeline shows how far through the game you are. If your selected investments exceed your available capital you will go bankrupt — you can still watch the remaining game play out, but you are eliminated from contention.",
        side: "bottom-right",
        selector: "#multi-action-controls",
        showControls: true,
        showSkip: true,
      },
      {
        icon: null,
        title: "Live Leaderboard",
        content:
          "This is the active leaderboard. Rankings update each year based on Cumulative Net Cash Flow (NCF) — the total cash your company has accumulated over the game. The winner is whoever has the highest NCF at the end — not the highest eNPV. Watch the rankings to see how you're competing against the AI.",
        side: "left",
        selector: "#multi-action-opponents",
        showControls: true,
        showSkip: true,
      },
      {
        icon: null,
        title: "You're ready!",
        content:
          "That's everything you need to get started. Make smart investment decisions, keep an eye on the leaderboard, and try to beat the AI! You can replay this tour at any time using the Tour button.",
        side: "right",
        showControls: true,
        showSkip: false,
      },
    ],
  },
];

export default steps;
