# Resources

<details initial-open="true">

<summary>Responsible Use Guidelines</summary>

The Pyxis Portfolio Simulator Research Environment uses exclusively synthetic data, which in no way represents real GSK or non-GSK drug assets. This is so anyone can get a chance to use Pyxis, try their hand at portfolio management and explore the AI technologies we are developing for portfolio management.

With that in mind, please follow these Responsible Use Guidelines:

**Interpretation and Decision-Making:** The Pyxis Portfolio Simulator Research Environment is for educational purposes only and its outputs should not be used in any decision making.

**Simulation Accuracy:** While great care has been taken to ensure that our synthetic data is representative of real-world drug assets, it is possible that discrepancies may arise which can be reflected in model behaviour. Keep that in mind when drawing conclusions from Pyxis.

**Model Assumptions:** Apart from obvious the limitations due to using synthetic data, we have also made simplifying modelling assumptions may impact the accuracy of predictions:

- When you create a portfolio, the aggregated costs, sales, and valuations are based on the selected projects only. All costs from excluded projects are immediately removed from the forecast. In reality, often these costs are committed and can’t be clawed back, how much is incurred depends on specific contracts.
- In real life, the values for costs, sales, etc. are estimates. For this version of Pyxis we don’t consider the uncertainty in these but just take them at face value. All probabilistic outputs are based on the uncertainty of success/failure outcomes of different projects at each phase, but not on the uncertainty of their financial data.
- The optimiser in The Portfolio Simulator is a linear optimiser so any non-linear functions are optimised via approximations. For version Pyxis v1.0.0, this only affects ROI. Please see the Investment Game for agents that use non-linear optimisation, however constrained to optimising eNPV only.

</details>

<details>

<summary>
How to Use The Portfolio Simulator
</summary>

To get to know the Portfolio Simulator, you can take a virtual tour through the tool!

[start-tour](start-tour)

If you have questions about how to use Pyxis that are not addressed in the tour, please get in touch via [GSK-GCP-RD-AIML-Economics@gsk.com](mailto:GSK-GCP-RD-AIML-Economics@gsk.com).

</details>

<details>

<summary>
FAQ
</summary>

**Where does the data come from?** Data is randomly generated and is not representative of real drug assets.

**Can we request new features to be added?** Yes, all feedback and feature requests are welcome. Please fill in the [Feature Request Form](https://forms.cloud.microsoft/Pages/ResponsePage.aspx?id=_yqYY2z7IkyXO3DkrPtj5udvY_7mb0NDmCsCyDSAdRZUMENPV1Y2MDRXTFFYUFI2NUxDRU5ZMldSRC4u) if you would like us to improve an existing feature or add a new feature.

**What are the key limitations of the tool I need to be aware of?** The data in Pyxis is synthetic and therefore the outputs should not be used to guide real-world decision making. Beyond data limitations, we have also made simplifying modelling assumptions may impact the accuracy of predictions:

- When you create a portfolio, the aggregated costs, sales, and valuations are based on the selected projects only. All costs from excluded projects are immediately removed from the forecast. In reality, often these costs are committed and can’t be clawed back, how much is incurred depends on specific contracts.
- In real life, the values for costs, sales, etc. are estimates. For this version of Pyxis we don’t consider the uncertainty in these but just take them at face value. All probabilistic outputs are based on the uncertainty of success/failure outcomes of different projects at each phase, but not on the uncertainty of their financial data.
- The optimiser in The Portfolio Simulator is a linear optimiser so any non-linear functions are optimised via approximations. For version Pyxis v1.0.0, this only affects ROI. Please see the Investment Game for agents that use non-linear optimisation, however constrained to optimising eNPV only.

**I have noticed a bug in the app. How can I report it?** If you have noticed a bug in the app, we apologise for the inconvenience. Please use the [Bug Reporting Form](https://forms.cloud.microsoft/Pages/ResponsePage.aspx?id=_yqYY2z7IkyXO3DkrPtj5udvY_7mb0NDmCsCyDSAdRZUQUZOVkQ1MjBNQVdNOVBJNFhUVEJCUjQ5Ny4u) to report it and our team will address it in the shortest possible timeframe.

**What does publishing a portfolio do?** Publishing a portfolio makes it visible to other users with appropriate access controls.

**Who can see my published portfolio?** All other internal GSK users can see your published portfolios.

**If I delete or unpublish a published portfolio, will it be removed from other users’ libraries?** Yes. Deleting or unpublishing a portfolio will remove it from other users’ libraries.

**I am not sure what a particular plot represents. Where can I find more information?** Each plot has an info button next to it providing extra information about what it represents. If you have further questions, please contact the Pyxis team by [GSK-GCP-RD-AIML-Economics@gsk.com](mailto:GSK-GCP-RD-AIML-Economics@gsk.com).

**Can I include risk aversion as an input in the Optimiser?**  Yes, you can encode a measure of risk in the optimiser via the standard deviation of NPV. This value represents the uncertainty in the outcome of NPV of a portfolio. 95% of outcomes lie within this value’s distance from the eNPV. If you need help selecting a limit on the standard deviation of NPV, please explore the Efficiency Frontier and the NPV distribution plots of different portfolios. These will give you an idea of what values represent more or less risk.

In future versions of Pyxis, we will explore more ways of encoding risk. If you have any suggestions for how we might improve this feature, please use the [Feature Request Form](https://forms.cloud.microsoft/Pages/ResponsePage.aspx?id=_yqYY2z7IkyXO3DkrPtj5udvY_7mb0NDmCsCyDSAdRZUMENPV1Y2MDRXTFFYUFI2NUxDRU5ZMldSRC4u) to let us know.

**What are custom projects?** Custom projects allow you to add a new project to your portfolio based on a “bucket valuation” methodology, using simplifying assumptions of cost phasing and sales curves. The default values are randomly generated and are not meaningful. All presets can be customised to create a project of your own.

**What are the pre-populated BD Deals?**  These are fictional BD deals, not based on any real data. For future use with appropriate access levels, these can be replaced with real BD deals so this functionality shows how you might be able to add such a deal into your portfolio.

</details>

<details>

<summary>Support</summary>

Further support can be found by emailing [GSK-GCP-RD-AIML-Economics@gsk.com](mailto:GSK-GCP-RD-AIML-Economics@gsk.com).

</details>
