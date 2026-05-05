export const informationDictionary = {
  forecastPlots: {
    distributionBarChart: {
      npv: {
        title: "NPV Distribution",
        informationTitle: "NPV Distribution",
        informationDescription:
          "This plot shows the distribution of possible outcomes of NPV for this portfolio. It takes into account every possible combination of success/failure of each project at each phase, and the probability of each of these outcomes. The vertical line shows the average outcome (also known as the risk-adjusted NPV), and the shaded width shows the standard deviation- a measure of uncertainty. The wider the shaded region, the more uncertain the outcome, and therefore the riskier the portfolio.",
      },
      net_sales: {
        title: "Probability Distribution of Net Sales",
        informationTitle: "",
        informationDescription: "",
      },
      dev_costs: {
        title: "Probability Distribution of Dev Cost",
        informationTitle: "",
        informationDescription: "",
      },
    },
    areaPlot: {
      sales_forecast: {
        title: "Pipeline Sales Forecast",
      },
      costs_forecast: {
        title: "Total Development Costs Forecast",
      },
      sales_costs: {
        informationTitle: "Sales and Costs Forecasts",
        informationDescription:
          "These plots show the sales and costs forecasts for the portfolio for the next 30 years. The hard line represents the average or risk-adjusted sales/cost, and the shaded region shows the standard deviation- a measure of uncertainty. 95% of outcomes lie within this shaded region. If you click on a particular point, you can see the expanded distribution for that year below.",
      },
    },
    valueUnlockPlot: {
      title: "Value Unlock Plot",
      informationTitle: "Value Unlock Plot",
      informationDescription:
        "This plot shows how every successful event in sequence can ‘unlock’ a certain amount of eNPV. The bigger the jump, the more influential that project’s phase is on the overall portfolio eNPV. If you hover over the unlock, you can see the relevant project and phase. \nNote: Only inflection points captured within the Enrich valuation will be reflected. Dates correspond to last-governed timeline (where possible).",
    },
    bubblePlot: {
      informationTitle: "Scatter Plot",
      informationDescription:
        "This scatter plot shows some key metrics of your portfolio, stratified by project. The costs, sales, NPV and TA are all encoded into a single plot. If you hover over a point, you can see the details of that particular project.",
    },
    spiderPlot: {
      informationTitle: "Spider Diagram",
      informationDescription:
        "This spider graph shows some key metrics of your portfolio. The hard line represents the mean (or risk-adjusted) value for the costs, sales and NPV values. The shaded regions cover a range of values such that 95% of outcomes would lie within that range.  For example, 95% of outcomes of the selected portfolio will have NPV fall within the shaded region. The wider the shaded region, the more uncertain the outcome.",
    },
  },
  portfolioFrontier: {
    informationPopover: {
      title: "Efficiency Frontier",
      description:
        "This plot shows the true efficiency frontier. It demonstrates the maximum average NPV a portfolio could achieve for different ranges of standard deviation in NPV. The standard deviation is a measure of how uncertain the NPV outcome is, therefore encoding risk. The more risk one takes, the higher potential NPV. \nThe points plotted on the frontier are portfolios from your library. They are labelled by user, whether or not the portfolio has any ‘edits’ (edited PTRS values or custom projects), and whether or not it passes the ‘default constraints’ (EPE budget for the next three years, as shown in the optimiser).",
    },
  },
  optimiser: {
    objective: {
      informationTitle: "Objective Options",
      informationDescription:
        "You may define your own optimisation problem to solve. The possible targets include risk-adjusted/non-risk-adjusted NPV, ROI, Sales, Total Dev elopment Costs, EPE, etc. For the constraints, you may also set a lower or upper limit on the number of projects selected from each TA. There is an option to constrain the ‘standard deviation of the NPV’. This is a measure of uncertainty and risk. 95% of outcomes lie within a distance equal to the standard deviation from the eNPV. If you need help setting a limit on it, you can refer to the Efficiency Frontier or look at the NPV distribution of a particular portfolio as reference.",
    },
    constraints: {
      informationTitle: "Default Constraints in Optimiser",
      informationDescription:
        "EPE constraints (2025-27) have been pre-populated with current Plan figures. The projects listed within Pyxis contribute 70-80% of total gross EPE for each TA, therefore users should also take into account the expenditures outside of these projects. \n\nBeyond these default constraints, you may add your own, such as eNPV or the number of projects from each TA. Authorised users should also be aware of their respective 2031 sales commitments. If you require clarification, please contact Hemal Malde",
    },
  },
  aiGeneratedReports: {
    informationTitle: "AI Current Phase PTRS",
    informationDescription:
      "AI generated PTRS estimates are generated using LLM-based deep-research functionality which uses academic literature and historical data to create an estimated range for the PTRS value for each project. The AI generated reports accompanying the estimate provide further rationale for the ranges stated in the table. You should treat this range as an additional input point for consideration, but do not take it at face value.",
  },
} as const;
