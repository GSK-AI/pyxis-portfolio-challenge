import upath
from sb3_contrib import MaskablePPO

from pyxis_portfolio_challenge.agents import PyxieAgent


def pyxie_new_agent():
    """
    Note: pyxie new agent is trained on the following parameters.

    If `max_num_assets` is not set to 15 in the eval env then
    you will get a shape mismatch.

    {
        "num_assets": 25,
        "max_num_assets": 50,
        "horizon": 100,
        "starting_cash": 1e8,
    }
    """
    agent = PyxieAgent(
        algorithm=MaskablePPO,
        model_path=upath.UPath(
            "/Users/tomcarter/repos/pyxis-portfolio-challenge/train_pyxie/experiments/exp_uncertainPtrs_ncfRew_25_Feb_2026_171533/25_Feb_2026_171533/best_model/best_model.zip"
        ),
        vecnorm_path=upath.UPath(
            "/Users/tomcarter/repos/pyxis-portfolio-challenge/train_pyxie/experiments/exp_uncertainPtrs_ncfRew_25_Feb_2026_171533/25_Feb_2026_171533/best_model/vecnormalize.pkl"
        ),
    )

    return agent


def pyxie_ta_specialization_treatment():
    """
    TA Specialization Treatment Agent (40 assets).

    Trained with uncertain_ptrs.enabled=True + TASpecializationBonus + max_total_experience=60 + max_expertise_boost=0.05.
    This agent should learn to specialize in therapeutic areas to gain
    better PTRS visibility and expertise boost.

    Trained for ~1.8M timesteps on 02 Mar 2026 with 40 assets / 8B starting cash.
    """
    model_path = upath.UPath(
        "/Users/tomcarter/repos/pyxis-portfolio-challenge/train_pyxie/experiments/"
        "exp_ta_specialization_treatment_02_Mar_2026_131940/02_Mar_2026_131940/best_model/best_model.zip"
    )
    vecnorm_path = upath.UPath(
        "/Users/tomcarter/repos/pyxis-portfolio-challenge/train_pyxie/experiments/"
        "exp_ta_specialization_treatment_02_Mar_2026_131940/02_Mar_2026_131940/best_model/vecnormalize.pkl"
    )

    agent = PyxieAgent(
        algorithm=MaskablePPO,
        model_path=model_path,
        vecnorm_path=vecnorm_path,
    )

    return agent


def pyxie_investment_levels():
    """
    Investment Levels Agent (12 assets, capacity constraints).

    Trained with investment_levels.enabled=True + uncertain_ptrs.enabled=True.
    Uses MultiDiscrete action space with 4 investment levels per asset.
    Medium mode: 1.5B cash, capacity 6, no warmup, horizon 100.

    Training: exp_investmentLevels_noWarmup_h100_05_Mar_2026_225714
    """
    model_path = upath.UPath(
        "/Users/tomcarter/repos/pyxis-portfolio-challenge/train_pyxie/experiments/"
        "exp_investmentLevels_noWarmup_h100_05_Mar_2026_225714/05_Mar_2026_225714/best_model/best_model.zip"
    )
    vecnorm_path = upath.UPath(
        "/Users/tomcarter/repos/pyxis-portfolio-challenge/train_pyxie/experiments/"
        "exp_investmentLevels_noWarmup_h100_05_Mar_2026_225714/05_Mar_2026_225714/best_model/vecnormalize.pkl"
    )

    agent = PyxieAgent(
        algorithm=MaskablePPO,
        model_path=model_path,
        vecnorm_path=vecnorm_path,
    )

    return agent


def pyxie_interim_trial_obs():
    """
    Distributional PTRS Agent (12 assets, tight capacity).

    Trained with distributional_ptrs.enabled=True + interim_trial_observations.enabled=True
    + investment_levels.enabled=True. Uses MultiDiscrete action space with 5 actions per asset
    (including STOP for early trial termination).

    Settings: 1.5B cash, capacity 4, warmup 100, horizon 200.

    Training: exp_distributional_ptrs_16_Mar_2026_160825
    """
    model_path = upath.UPath(
        "/Users/tomcarter/repos/pyxis-portfolio-challenge/train_pyxie/experiments/"
        "exp_distributional_ptrs_16_Mar_2026_160825/16_Mar_2026_160825/best_model/best_model.zip"
    )
    vecnorm_path = upath.UPath(
        "/Users/tomcarter/repos/pyxis-portfolio-challenge/train_pyxie/experiments/"
        "exp_distributional_ptrs_16_Mar_2026_160825/16_Mar_2026_160825/best_model/vecnormalize.pkl"
    )

    agent = PyxieAgent(
        algorithm=MaskablePPO,
        model_path=model_path,
        vecnorm_path=vecnorm_path,
    )

    # Clear learning rate schedule to make model picklable for multiprocessing
    if hasattr(agent.model, 'lr_schedule'):
        agent.model.lr_schedule = lambda _: 0.0001

    return agent


def pyxie_distributional_ptrs():
    """
    Distributional PTRS Agent (12 assets, tight capacity).

    Trained with distributional_ptrs.enabled=True + investment_levels.enabled=True.
    Uses MultiDiscrete action space with 5 actions per asset.
    interim_trial_observations is DISABLED (mutually exclusive with distributional_ptrs).

    Settings: 1.5B cash, capacity 4, warmup 100, horizon 200.

    Training: exp_distributional_ptrs_19_Mar_2026_131510
    """
    model_path = upath.UPath(
        "/Users/tomcarter/repos/pyxis-portfolio-challenge/experiments/"
        "exp_distributional_ptrs_19_Mar_2026_131510/19_Mar_2026_131510/best_model/best_model.zip"
    )
    vecnorm_path = upath.UPath(
        "/Users/tomcarter/repos/pyxis-portfolio-challenge/experiments/"
        "exp_distributional_ptrs_19_Mar_2026_131510/19_Mar_2026_131510/best_model/vecnormalize.pkl"
    )

    agent = PyxieAgent(
        algorithm=MaskablePPO,
        model_path=model_path,
        vecnorm_path=vecnorm_path,
    )

    # Clear learning rate schedule to make model picklable for multiprocessing
    # Set to a constant value (not a closure)
    agent.model.lr_schedule = 0.0001

    return agent


def pyxie_ta_specialization_control():
    """
    TA Specialization Control Agent (Ablation, 40 assets).

    Trained with uncertain_ptrs.enabled=False + TASpecializationBonus + max_total_experience=60 + max_expertise_boost=0.05.
    This agent receives specialization rewards but doesn't benefit from
    improved PTRS visibility or expertise boost. Used as ablation.

    Trained for ~1.4M timesteps on 02 Mar 2026 with 40 assets / 8B starting cash.
    """
    model_path = upath.UPath(
        "/Users/tomcarter/repos/pyxis-portfolio-challenge/train_pyxie/experiments/"
        "exp_ta_specialization_control_02_Mar_2026_132723/02_Mar_2026_132723/best_model/best_model.zip"
    )
    vecnorm_path = upath.UPath(
        "/Users/tomcarter/repos/pyxis-portfolio-challenge/train_pyxie/experiments/"
        "exp_ta_specialization_control_02_Mar_2026_132723/02_Mar_2026_132723/best_model/vecnormalize.pkl"
    )

    agent = PyxieAgent(
        algorithm=MaskablePPO,
        model_path=model_path,
        vecnorm_path=vecnorm_path,
    )

    return agent
