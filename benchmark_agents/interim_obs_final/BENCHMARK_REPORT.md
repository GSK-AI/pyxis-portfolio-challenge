# Interim Trial Observations Benchmark Report

**Date:** 2026-03-11
**Benchmark Directory:** `benchmark_agents/interim_obs_final/`

## Executive Summary

This benchmark evaluates three agents on a pharmaceutical investment environment with **tight capacity constraints**, **investment levels**, and **interim trial observations** that enable early stopping (STOP action).

| Agent | Mean Reward | Bankruptcy Rate | Avg STOP/Episode |
|-------|-------------|-----------------|------------------|
| **Pyxie (RL)** | **+2.60B** | **12%** | 39.2 |
| Knapsack | -269M | 60% | 0 |
| Random | -1.49B | 90% | 10.0 |

**Key Finding:** Pyxie significantly outperforms the greedy knapsack heuristic by learning sophisticated capacity management - not just avoiding bankruptcy, but optimizing investment levels and using STOP strategically.

---

## Environment Configuration

### Core Parameters

```yaml
equilibrium_num_assets: 10
max_num_assets: 12
starting_cash: 1.5e9  # 1.5 billion
horizon: 100
reinvestment_percentage: 0.10
```

### Investment Levels (MultiDiscrete Action Space)

The agent chooses one of 5 actions per asset:

| Level | Cost Modifier | Speed | Success Modifier | Capacity Cost |
|-------|---------------|-------|------------------|---------------|
| NONE (0) | 0.0 | 0.0 | 1.0 | 0 |
| MINIMAL (1) | 0.5 | 0.5x | 0.85 | **1** |
| STANDARD (2) | 1.0 | 1.0x | 1.0 | **2** |
| ACCELERATED (3) | 2.0 | 2.0x | 1.10 | **4** |
| STOP (4) | - | - | - | Frees capacity |

### Capacity Constraints (Critical)

```yaml
capacity:
  base_capacity: 4  # Very tight!
  overage_max_penalty: 0.50      # Success rates drop up to 50%
  overage_cost_max_penalty: 0.60 # Costs increase up to 60%
```

**Implication:** With base_capacity=4, an agent can run:
- 4 MINIMAL assets (4 x 1 = 4 capacity), OR
- 2 STANDARD assets (2 x 2 = 4 capacity), OR
- 1 ACCELERATED asset (1 x 4 = 4 capacity)

Exceeding capacity triggers **severe penalties** on ALL active trials.

### Interim Trial Observations

```yaml
interim_trial_observations:
  enabled: true
  latent_quality_concentration: 10.0
  initial_noise_scale: 0.3
```

Assets in development receive noisy signals about trial quality. The STOP action allows terminating unpromising trials early to free capacity.

### Uncertain PTRS

```yaml
uncertain_ptrs:
  enabled: true
  ta_noise_config:
    oncology: 0.45
    respiratory and immunology: 0.38
    vaccines and infectious disease: 0.30
```

True success probabilities (PTRS) are hidden behind noise. Experience in a therapeutic area reduces uncertainty.

---

## Configuration Files

### Evaluation Configuration (config.yaml)

**File:** `pyxis_portfolio_challenge/config.yaml`

```yaml
# this config serves as a place to fix the train and eval environment parameters for the published game
# Gym environment initialization parameters - 40 assets for complexity test
equilibrium_num_assets: 10
max_num_assets: 12
asset_arrival_sensitivity_below: 2.0
asset_arrival_sensitivity_above: 2.0
starting_cash: 1.5e9  # Moderate constraint - allows some exploration
horizon: 100
reinvestment_percentage: 0.10
shuffle_order: false
mask_first_order_assets: true
mask_negative_enpv_assets: false
auto_center_rewards: false
auto_center_calibration_steps: 10_000
flatten_obs: true
warmup_on_reset_steps: 0
warmup_on_reset_policy: do_nothing
reward_fn:
  _target_: pyxis_portfolio_challenge.environment.reward.NetCashFlowReward

# Training parameters
training_data_dir: /Users/tomcarter/repos/pyxis-portfolio-challenge/rl-environment-assets/gpt5_09feb2026_highPtrs/training

# Evaluation parameters
evaluation_data_dir: /Users/tomcarter/repos/pyxis-portfolio-challenge/rl-environment-assets/gpt5_09feb2026_highPtrs/evaluation
eval_initial_seed: 891024889
num_eval_episodes: 100
evaluation_metrics:
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerEvaluationCumulativeReward
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerEvaluationBankruptcyRate
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerEpisodeCumulativeReward
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerEpisodeRealisedRoi
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerEpisodeFinalEroi
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerEpisodeFinalEnpv
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerEpisodeNumSteps
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepReward
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepCash
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepRevenue
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepCost
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepNetCashFlow
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepCumulativeNetCashFlow
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepCumulativeReward
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepEnpv
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepEroi
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepNumAssetsIdleState
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepNumAssetsInDevelopmentState
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepNumAssetsOnMarketState
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepNumAssetsFailedState
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepNumAssetsExpiredState
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepFractionOfPossibleInvestments
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepFractionOfPossibleInvestmentsPosEnpv
  # Uncertain PTRS metrics (for tracking TA specialization)
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepTAExperienceOncology
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepTAExperienceRespiratoryImmunology
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepTAExperienceVaccines
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepMeanPTRSError
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepMeanExpertiseBoost
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepNumAssetsOncology
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepNumAssetsRespiratoryImmunology
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepNumAssetsVaccines
  # Investment levels metrics (for monitoring capacity and level distribution)
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepCapacityUsed
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepCapacityRatio
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepGlobalSuccessModifier
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepGlobalCostModifier
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepNumAssetsMinimalLevel
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepNumAssetsStandardLevel
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepNumAssetsAcceleratedLevel
  # Interim trial observations metrics (for monitoring early stopping decisions)
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepMeanInterimSignal
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepMeanTrialProgress
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepMinInterimSignal
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerEpisodeNumStopActions
  - _target_: pyxis_portfolio_challenge.environment.metrics.PerStepNumStopActions


# Pyxie agent parameters
pyxie_model_root_path: az://saved-gym-agent

# Uncertain PTRS feature
uncertain_ptrs:
  enabled: true  # Master toggle for uncertain PTRS feature

  # TA-specific base noise levels (very high - makes expertise critical)
  ta_noise_config:
    oncology: 0.45
    respiratory and immunology: 0.38
    vaccines and infectious disease: 0.30

  # Phase noise multipliers (later phases are noisier)
  phase_noise_multipliers:
    phase_1: 1.0
    phase_2: 1.5
    phase_3: 2.0

  # Experience system - aggressive decay to force specialization
  experience_to_full_knowledge: 30.0   # Very high bar for full knowledge
  max_expertise_boost: 0.05            # 5% PTRS boost for specialists
  experience_to_max_boost: 40.0
  experience_decay_rate: 0.98          # 8% decay - after 25 steps only 12% remains
  max_total_experience: 60.0           # Hard cap on total experience (2x full knowledge)
                                       # Forces trade-off: specialist gets 100% in 1 TA,
                                       # generalist gets ~33% in each of 3 TAs

  # Phase experience weights - low so spreading thin doesn't work
  phase_experience_weights:
    phase_1: 0.5
    phase_2: 1.0
    phase_3: 1.5

  # Asset arrival bias - small bias toward experienced TAs
  asset_arrival_temperature: 0.1  # Small bias, rewards mild specialization

# Investment levels feature - variable investment intensity with capacity constraints
investment_levels:
  enabled: true  # Master toggle for investment levels feature

  # Investment level definitions
  # Each level affects: cost, speed, success probability, capacity usage, and experience gain
  levels:
    none:  # Not investing (for idle assets or pausing)
      cost_modifier: 0.0
      speed_modifier: 0.0
      success_modifier: 1.0
      capacity_cost: 0
      experience_modifier: 0.0
    minimal:  # Much slower and cheaper, better learning
      cost_modifier: 0.5
      speed_modifier: 0.5  # 2x slower
      success_modifier: 0.85
      capacity_cost: 1
      experience_modifier: 2.0
    standard:  # Normal development pace
      cost_modifier: 1.0
      speed_modifier: 1.0
      success_modifier: 1.0
      capacity_cost: 2
      experience_modifier: 1.0
    accelerated:  # Much faster but very expensive, minimal learning
      cost_modifier: 2.0
      speed_modifier: 2.0  # 2x faster
      success_modifier: 1.10
      capacity_cost: 4
      experience_modifier: 0.25

  # R&D Capacity system - moderate constraint on total investment intensity
  capacity:
    base_capacity: 4  # Tight - allows 2 standard or 4 minimal assets
    # Overage penalties: when capacity_used > base_capacity
    # success_modifier = 1.0 - (overage_ratio * overage_max_penalty)
    # cost_modifier = 1.0 + (overage_ratio * overage_cost_max_penalty)
    # where overage_ratio = (used - base) / base
    overage_max_penalty: 0.50  # At 2x capacity, success rates drop 50%
    overage_cost_max_penalty: 0.60  # At 2x capacity, costs increase 60%
    overage_scaling: linear  # "linear" or "quadratic"

# Interim trial observations feature - noisy signals during trials enable early stopping
interim_trial_observations:
  enabled: true  # Master toggle for interim trial observations
  latent_quality_concentration: 10.0  # Beta distribution concentration (higher = tighter around PTRS)
  initial_noise_scale: 0.3  # Initial noise in interim signals (decreases as trial progresses)
```

### Training Configuration (interim_trial_observations_config.yaml)

**File:** `train_pyxie/conf/interim_trial_observations_config.yaml`

```yaml
hydra:
  run:
    dir: ${experiment_dir}

experiment_name: exp_interimTrialObs_tightCapacity_${now:%d_%b_%Y_%H%M%S}
experiments_folder_name: experiments
experiments_folder_path: ${experiments_folder_name}
experiment_dir: ${experiments_folder_path}/${experiment_name}/${now:%d_%b_%Y_%H%M%S}

# =============================================================================
# Gym environment parameters
# =============================================================================
equilibrium_num_assets: 10
max_num_assets: 12
asset_arrival_sensitivity_below: 2.0
asset_arrival_sensitivity_above: 2.0
starting_cash: 1500000000
horizon: 200
reinvestment_percentage: 0.10
shuffle_order: false
auto_center_rewards: false
auto_center_calibration_steps: 10_000
mask_first_order_assets: true
mask_negative_enpv_assets: false
flatten_obs: true
warmup_on_reset_steps: 100
warmup_on_reset_policy: do_nothing

reward_fn:
  _target_: pyxis_portfolio_challenge.environment.reward.NetCashFlowReward

# Uncertain PTRS feature
uncertain_ptrs:
  enabled: true
  ta_noise_config:
    oncology: 0.45
    respiratory and immunology: 0.38
    vaccines and infectious disease: 0.30
  phase_noise_multipliers:
    phase_1: 1.0
    phase_2: 1.5
    phase_3: 2.0
  experience_to_full_knowledge: 30.0
  max_expertise_boost: 0.05
  experience_to_max_boost: 40.0
  experience_decay_rate: 0.98
  max_total_experience: 60.0
  phase_experience_weights:
    phase_1: 0.5
    phase_2: 1.0
    phase_3: 1.5
  asset_arrival_temperature: 0.1

# Investment levels feature with TIGHT capacity constraints
investment_levels:
  enabled: true
  levels:
    none:
      cost_modifier: 0.0
      speed_modifier: 0.0
      success_modifier: 1.0
      capacity_cost: 0
      experience_modifier: 0.0
    minimal:
      cost_modifier: 0.5
      speed_modifier: 0.5
      success_modifier: 0.85
      capacity_cost: 1
      experience_modifier: 2.0
    standard:
      cost_modifier: 1.0
      speed_modifier: 1.0
      success_modifier: 1.0
      capacity_cost: 2
      experience_modifier: 1.0
    accelerated:
      cost_modifier: 2.0
      speed_modifier: 2.0
      success_modifier: 1.10
      capacity_cost: 4
      experience_modifier: 0.25
  capacity:
    base_capacity: 4  # Tight! Only 2 standard trials or 4 minimal
    overage_max_penalty: 0.50
    overage_cost_max_penalty: 0.60
    overage_scaling: linear

# Interim trial observations feature - enables early stopping
interim_trial_observations:
  enabled: true
  latent_quality_concentration: 10.0  # Higher = tighter distribution around PTRS
  initial_noise_scale: 0.3  # Noise decreases as trial progresses

# =============================================================================
# Training parameters
# =============================================================================
training_data_dir: /Users/tomcarter/repos/pyxis-portfolio-challenge/rl-environment-assets/gpt5_09feb2026_highPtrs/training
evaluation_data_dir: /Users/tomcarter/repos/pyxis-portfolio-challenge/rl-environment-assets/gpt5_09feb2026_highPtrs/evaluation
n_envs: 50
norm_obs: true
norm_reward: true
total_timesteps: 10000000
tb_log_name: ${experiment_name}
model_save_path: ${experiment_dir}/final_model.zip
vecnorm_save_path: ${experiment_dir}/final_vecnormalize.pkl

# =============================================================================
# Evaluation callback
# =============================================================================
eval:
  _target_: sb3_contrib.common.maskable.callbacks.MaskableEvalCallback
  eval_freq: 1000
  best_model_save_path: ./${experiment_dir}/best_model
  log_path: ./${experiment_dir}/logs
  n_eval_episodes: 500
  deterministic: true
  render: false

# =============================================================================
# Checkpoint callback
# =============================================================================
checkpoint:
  _target_: stable_baselines3.common.callbacks.CheckpointCallback
  save_freq: 50000
  save_path: ./${experiment_dir}/checkpoints
  save_vecnormalize: true

# =============================================================================
# Model (MaskablePPO)
# =============================================================================
model:
  _target_: sb3_contrib.MaskablePPO
  policy: MlpPolicy
  verbose: 1
  tensorboard_log: ${experiments_folder_path}/tensorboard/
  gamma: 0.995
  ent_coef: 0.15
  clip_range: 0.1
  n_steps: 2048
  batch_size: 1024
  n_epochs: 4
  target_kl: 0.01
  gae_lambda: 0.95
  policy_kwargs:
    net_arch: [256, 128]

# Learning rate schedule (linear decay)
learning_rate_start: 1e-4
learning_rate_end: 1e-5
```

---

## Detailed Results

### Overall Performance (100 Episodes)

| Metric | Random | Knapsack | Pyxie |
|--------|--------|----------|-------|
| Mean Reward | -1.49B | -269M | **+2.60B** |
| Std Dev | 275M | 2.17B | 2.53B |
| Min | -1.93B | -1.86B | -1.59B |
| Max | 526M | 7.83B | 11.5B |
| Median | -1.52B | -1.51B | **+2.70B** |
| Bankruptcy Rate | 90% | 60% | **12%** |

### Survival-Conditional Analysis

Among episodes that **did not go bankrupt**:

| Metric | Knapsack Survivors (n=40) | Pyxie Survivors (n=88) |
|--------|---------------------------|------------------------|
| Mean Reward | +1.69B | **+3.16B** |
| Std Dev | 2.30B | 2.16B |

### Statistical Significance Tests

| Test | Comparison | Difference | t-statistic | p-value | Significant? |
|------|------------|------------|-------------|---------|--------------|
| All episodes (t-test) | Pyxie vs Knapsack | **+2.86B** | 8.56 | p < 0.000001 | **YES** (p<0.01) |
| Survivors only (t-test) | Pyxie vs Knapsack | **+1.47B** | 3.47 | p = 0.0007 | **YES** (p<0.01) |
| Mann-Whitney U (non-parametric) | Pyxie > Knapsack | - | U=8214 | p < 0.000001 | **YES** |

**Effect Size:** Cohen's d = **1.22** (large effect, threshold >0.8)

**Key Insight:** Pyxie outperforms Knapsack by **+1.47B even among surviving episodes**. This is NOT just about avoiding bankruptcy - it's a genuine strategic advantage with a large effect size.

---

## Why Knapsack Fails

### 1. Constant Capacity Overage

| Metric | Knapsack | Pyxie |
|--------|----------|-------|
| Avg Capacity Used | **4.74** | 2.59 |
| Base Capacity | 4 | 4 |
| Over Capacity? | **YES (+19%)** | No |

Knapsack uses only STANDARD level investments (capacity cost = 2 each). With 2-3 assets in development, it consistently exceeds the base capacity of 4.

### 2. Severe Overage Penalties

When capacity exceeds 4, ALL active trials suffer:

- **Success Rate Penalty:** Up to 50% reduction (GlobalSuccessModifier drops to ~0.5)
- **Cost Penalty:** Up to 60% increase (GlobalCostModifier rises to ~1.6)

The plots show Knapsack's GlobalSuccessModifier frequently dropping to 0.4-0.6, while Pyxie maintains ~1.0.

### 3. No STOP Action Usage

Knapsack never uses the STOP action (0 per episode). It cannot:
- Free capacity from unpromising trials
- React to negative interim signals
- Escape the capacity overage trap

### 4. Investment Level Blindness

Knapsack always chooses STANDARD level (capacity cost = 2). It doesn't consider:
- Using MINIMAL (capacity cost = 1) to fit more assets
- The capacity vs. speed tradeoff
- Overall portfolio capacity constraints

---

## Why Pyxie Succeeds

### 1. Intelligent Capacity Management

| Investment Level | Knapsack | Pyxie |
|------------------|----------|-------|
| MINIMAL (cap=1) | 0% | **38%** |
| STANDARD (cap=2) | 100% | **61%** |
| ACCELERATED (cap=4) | 0% | 1% |

Pyxie learned to use MINIMAL investments for lower-priority assets, keeping total capacity usage at 2.59 (well under the limit of 4).

### 2. Strategic STOP Usage

- **Average STOP actions per episode:** 40.1
- **Purpose:** Free capacity from unpromising trials

Interestingly, STOP count does not correlate with episode reward (r=-0.024). This suggests:
- STOP is used for **capacity management**, not reward maximization
- The VALUE comes from what you do with the freed capacity
- It's about **when** you STOP, not **how many** times

### 3. No Overage Penalties

By staying under capacity:
- GlobalSuccessModifier stays at ~1.0 (no penalty)
- GlobalCostModifier stays at ~1.0 (no penalty)
- Trials succeed at their base rates
- Costs remain predictable

### 4. Higher Survival Rate

| Agent | Survival Rate |
|-------|---------------|
| Pyxie | **88%** |
| Knapsack | 40% |
| Random | 7% |

Higher survival means more opportunities to generate revenue from successful drugs.

---

## Decision Patterns That Enable Success

### Pyxie's Learned Strategy

1. **Conservative Capacity Usage**
   - Target: ~2.6 capacity (65% of limit)
   - Buffer for new high-value opportunities

2. **Mixed Investment Levels**
   - MINIMAL for speculative/lower-eNPV assets
   - STANDARD for high-confidence assets
   - Rarely ACCELERATED (not worth the capacity cost)

3. **Proactive STOP Decisions**
   - Monitor interim signals during trials
   - STOP unpromising trials before they complete
   - Prioritize freeing capacity over sunk cost fallacy

4. **Avoiding Overage Traps**
   - Never let capacity usage exceed base limit
   - Accept slower development over penalty-ridden fast development

### What Knapsack Gets Wrong

1. **Greedy Single-Asset Optimization**
   - Maximizes delta-eNPV per asset
   - Ignores portfolio-level capacity constraints

2. **No Action Space Awareness**
   - Only uses STANDARD level
   - Doesn't know MINIMAL or STOP exist

3. **No Penalty Modeling**
   - Doesn't understand overage consequences
   - Keeps investing despite declining success rates

---

## Environment Fairness Analysis

**Question:** Is the environment "fair" or does Pyxie just learn to avoid bankruptcy?

**Answer:** The environment IS fair. Evidence:

1. **Pyxie outperforms Knapsack even among survivors** (+1.15B, p=0.0078)
2. **Overage penalties affect non-bankrupt episodes** - Knapsack's survivors have lower returns due to success/cost penalties
3. **Multiple decision dimensions:**
   - Which assets to invest in (eNPV ranking)
   - What level to invest at (capacity tradeoff)
   - When to STOP (interim signal interpretation)
   - How to balance portfolio capacity

The greedy heuristic fails not just due to bankruptcy risk, but because it doesn't understand the multi-dimensional optimization required.

---

## Kelly Criterion Agent Analysis

### Overview

We implemented a Kelly Criterion agent to test whether classical position-sizing theory could compete with learned RL behavior. Kelly Criterion maximizes geometric growth rate by sizing bets according to edge and odds.

### Kelly Implementation

The agent maps Kelly fraction to investment levels:

```python
def _kelly_to_level(self, kelly: float) -> int:
    if kelly < 0:
        return 0  # NONE - negative expected value
    elif kelly < 0.15:
        return 1  # MINIMAL - low edge
    elif kelly < 0.40:
        return 2  # STANDARD - moderate edge
    else:
        return 3  # ACCELERATED - high edge
```

Kelly fraction calculation:
```
f* = (p * b - q) / b
where:
  p = PTRS (probability of success)
  q = 1 - p
  b = eNPV / cost - 1 (odds)
```

Fractional Kelly variants:
- **Full Kelly**: 100% of recommended bet size
- **Half-Kelly**: 50% of recommended bet size
- **Quarter-Kelly**: 25% of recommended bet size (most conservative)

STOP logic: Terminate trials when interim signal < 0.3 threshold.

### Kelly Benchmark Results

| Agent | Mean Reward | Bankruptcy Rate | Avg STOP/Episode |
|-------|-------------|-----------------|------------------|
| **Pyxie (RL)** | **+2.60B** | **12%** | 39.2 |
| Kelly Quarter | +0.10B | 22% | 10.8 |
| Knapsack | -0.27B | 60% | 0 |
| Kelly Half | -0.49B | 48% | 6.7 |
| Kelly Full | -1.03B | 61% | 14.6 |

### Investment Level Distribution

| Agent | MINIMAL | STANDARD | ACCELERATED | Total STOP |
|-------|---------|----------|-------------|------------|
| Kelly Quarter | 49% | 51% | 0% | 1,085 |
| Kelly Half | 13% | 69% | 18% | 674 |
| Kelly Full | 75% | 15% | 10% | 1,459 |
| Pyxie | 38% | 61% | 1% | ~3,900 |

### Statistical Significance

| Comparison | Difference | p-value | Significant? |
|------------|------------|---------|--------------|
| Kelly Quarter vs Knapsack | +0.37B | 0.18 | No |
| Kelly Quarter vs Pyxie | -2.50B | <0.000001 | **Yes** |

### Key Insights

1. **Conservative Kelly is the best heuristic** - Quarter-Kelly achieves lowest bankruptcy rate (22%) among non-RL agents by avoiding over-betting.

2. **More aggressive Kelly = worse performance** - Full Kelly over-bets and performs worse than Knapsack (61% vs 60% bankruptcy).

3. **Kelly Quarter never uses ACCELERATED** - The 0.25 multiplier means even high-edge assets get downgraded to STANDARD or MINIMAL.

4. **Kelly Full paradoxically uses 75% MINIMAL** - Hits capacity limits quickly, so downgrades to fit more assets.

5. **All Kelly agents use fewer STOPs than Pyxie** - ~700-1500 vs Pyxie's ~3900. Simple threshold-based STOP vs learned optimal timing.

### Why Kelly Falls Short

| Kelly Strength | Limitation in This Environment |
|----------------|-------------------------------|
| Position sizing based on edge | Doesn't understand capacity constraints |
| Avoids negative EV bets | Capacity is the binding constraint, not EV |
| Conservative variants reduce ruin | Still doesn't know WHEN to STOP optimally |
| Uses STOP action | Simple threshold vs learned policy |

**Core Problem:** Kelly optimizes bet sizing assuming unlimited betting capacity. This environment's key constraint is capacity (base=4), not bankroll. Kelly doesn't natively model "you can only run N concurrent trials regardless of bet size."

### Conclusion

Kelly Criterion provides a better heuristic than greedy Knapsack by being more conservative, but cannot match learned RL behavior. The 2.5B gap to Pyxie demonstrates the value of learning environment-specific policies vs applying general financial theory.

---

## Potential for Further Improvement

### Evidence for Improvement Potential

Analysis of Pyxie's performance reveals weak but positive correlations suggesting room for a more sophisticated model:

| Signal | Correlation | Reward Gap |
|--------|-------------|------------|
| Interim signal quality | r=0.151 | High signal episodes: +3.43B vs Low: +2.18B (**+1.25B gap**) |
| Capacity utilization | r=0.140 | Aggressive: +3.36B vs Conservative: +1.93B (**+1.43B gap**) |

### Variance Analysis

Among 88 surviving episodes:

| Metric | Value |
|--------|-------|
| Reward mean | +2.84B |
| Reward std | 2.17B |
| Reward range | -1.24B to +8.84B |
| STOP actions mean | 43.1 |
| STOP actions std | 3.0 |
| Top 10 episodes mean | +7.25B |
| Bottom 10 episodes mean | -0.29B |
| Gap (top vs bottom 10) | **7.54B** |

**Key insight:** STOP usage is highly consistent (std=3) but outcomes vary hugely (std=2.17B). This suggests most variance is environmental (asset quality), but there's potential to better adapt to circumstances.

### Potential Improvement Approaches

| Approach | Rationale |
|----------|-----------|
| **Recurrent/Transformer architecture** | Track interim signal evolution over time; current MLP [256, 128] can't see temporal patterns in signals |
| **Distributional RL (C51, QR-DQN)** | Model outcome variance explicitly for risk-aware decisions |
| **Adaptive capacity strategy** | Be more aggressive when assets look promising; Pyxie uses only 65% of capacity on average |
| **Better STOP timing** | Use interim signal trajectories to predict which trials to cut early |
| **Curriculum learning** | Train on progressively tighter capacity constraints |
| **Attention over assets** | Learn which asset features matter most for investment decisions |

### Why Pyxie Might Be Too Conservative

1. **Capacity utilization**: Averages 2.59 out of 4.0 (65%). Episodes with higher utilization correlate with better returns.
2. **STOP rigidity**: Takes ~43 STOP actions regardless of episode circumstances. A smarter model might adapt.
3. **Interim signal interpretation**: Weak correlation (0.151) suggests signals have predictive value not fully exploited.

### Realistic Expectations

**Estimated improvement potential: +0.5B to +1.0B** (incremental, not transformative)

**Why not more?**
- Most variance is environmental (asset quality luck), not policy-driven
- Pyxie already learned the key insight (capacity management + STOP + mixed investment levels)
- The problem structure may have near-optimal simple solutions
- 12% bankruptcy rate is already low

**Estimated ceiling: ~3.5-4.0B** (currently 2.84B for survivors) based on:
- High-capacity, high-signal episodes already achieve this level
- Environmental variance limits what any policy can achieve
- Top 10 episodes average 7.25B, but this includes lucky asset draws

### Conclusion

A more complex model (recurrent architecture, distributional RL) could likely squeeze out incremental gains through:
1. Better utilization of interim signals
2. Slightly more aggressive capacity management
3. Adaptive STOP timing based on episode circumstances

However, dramatic outperformance is unlikely given that Pyxie has already learned the core strategy. The biggest remaining variance is in asset quality, which no policy can control.

---

## Plots Reference

All plots are saved in `plots/` subdirectory:

- `PerEvaluationMetrics_*.png` - Summary comparison table
- `PerStepCumulativeReward_*.png` - Reward trajectories over time
- `PerStepCapacityUsed_*.png` - Capacity usage patterns
- `PerStepGlobalSuccessModifier_*.png` - Overage penalty visualization
- `PerStepGlobalCostModifier_*.png` - Cost penalty visualization
- `PerStepNumStopActions_*.png` - STOP action usage over time
- `PerEpisodeNumStopActions_*.png` - STOP action distribution
- `PerStepMeanInterimSignal_*.png` - Interim signal observations

---

## Key Training Hyperparameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Algorithm | MaskablePPO | Handles action masking for invalid actions |
| Policy | MlpPolicy [256, 128] | Two hidden layers |
| Total Timesteps | 10M | ~200k episodes at horizon 50 avg |
| Parallel Envs | 50 | For faster sampling |
| Gamma | 0.995 | High discount factor for long-horizon |
| Entropy Coef | 0.15 | Encourages exploration |
| Clip Range | 0.1 | Conservative policy updates |
| Learning Rate | 1e-4 → 1e-5 | Linear decay |
| Warmup Steps | 100 | Do-nothing warmup before agent acts |
| Training Horizon | 200 | Longer than eval (100) for robustness |

### Training vs Evaluation Differences

| Parameter | Training | Evaluation |
|-----------|----------|------------|
| Horizon | 200 | 100 |
| Warmup Steps | 100 | 0 |
| Observation Norm | Yes (VecNormalize) | Yes (loaded from training) |
| Reward Norm | Yes | No |

---

## Model Details

**Pyxie Agent:**
- Algorithm: MaskablePPO (Stable-Baselines3)
- Training: `exp_interimTrialObs_tightCapacity_11_Mar_2026_104207`
- Action Space: MultiDiscrete (5 actions per asset)
- Observation: Flattened vector including interim signals and capacity info
- Network: MLP with [256, 128] hidden layers

**Knapsack Agent:**
- Heuristic: 0/1 Knapsack DP on delta-eNPV
- Always uses STANDARD investment level
- No STOP action support
- No capacity awareness

**Random Agent:**
- Uniform random selection from valid actions
- Respects action masks
- Uses all investment levels including STOP
