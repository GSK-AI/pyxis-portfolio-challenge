"""Multi-agent game orchestrator wrapping N GameState instances."""

from __future__ import annotations

import logging
import random
import uuid
from typing import Literal

import upath
from pydantic import BaseModel, ConfigDict, PrivateAttr

from pyxis_portfolio_challenge.game.asset import AssetState
from pyxis_portfolio_challenge.game.asset_generators import JSONAssetGenerator
from pyxis_portfolio_challenge.game.constants import InvestmentLevel
from pyxis_portfolio_challenge.game.game_state import GameState
from pyxis_portfolio_challenge.game.shared_market_state import (
    THERAPEUTIC_AREAS,
    SharedMarketState,
)
from pyxis_portfolio_challenge.game.trial import TrialPhase

logger = logging.getLogger(__name__)


class MultiAgentGame(BaseModel):
    """
    Immutable orchestrator for multi-agent competitive investment game.

    Wraps N GameState instances (one per agent) and a SharedMarketState.
    All single-player game dynamics are delegated to GameState.step().
    This class only adds cross-agent interactions:
    - BD (Business Development) auction resolution
    - Market share competition (revenue splitting)
    - Event-driven pipeline leak alerts (competitive intelligence)
    - Drug release / expiry tracking across agents

    Immutable: step() returns a new MultiAgentGame instance.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    agent_states: dict[str, GameState]
    shared_market: SharedMarketState
    time: int
    horizon: int
    num_agents: int
    disable_market_share_competition: bool
    bd_max_slots: int
    pricing_elasticity: float

    _rng: random.Random = PrivateAttr()
    # Cached per-drug market shares from last step, keyed by agent.
    # Avoids recomputing in observation building.
    _cached_market_shares: dict[str, dict] = PrivateAttr(default_factory=dict)

    @classmethod
    def initialise(
        cls,
        num_agents: int,
        seed: int,
        starting_cash: float,
        horizon: int,
        equilibrium_num_assets: int,
        max_num_assets: int,
        asset_arrival_sensitivity_below: float,
        asset_arrival_sensitivity_above: float,
        reinvestment_percentage: float,
        assets_dir: upath.UPath,
        exclusivity_period: int,
        first_mover_bonus: float,
        disable_market_share_competition: bool,
        alert_history_length: int,
        reward_fn_config: dict,
        distributional_ptrs_config,
        ta_experience_config,
        uncertain_ptrs_config,
        investment_levels_config,
        interim_trial_observations_config,
        rd_capacity_config,
        indications_per_ta: int,
        indication_spread: float,
        indication_drift_speed: float,
        trial_cost_multiplier: float,
        approval_phase_config,
        # BD configuration
        bd_enabled: bool,
        bd_assets_dir: upath.UPath | None,
        bd_base_lambda: float,
        bd_leak_lambda_boost: float,
        bd_min_step: int,
        bd_num_bid_levels: int,
        bd_break_even_bid_level: int,
        bd_phase_weights: list[float] | None,
        bd_indication_activity_bias: float,
        bd_max_slots: int,
        # Leak configuration
        leak_phase_probabilities: list[float] | None,
        # Congestion penalty
        congestion_exponent: float,
        congestion_ramp_steps: int,
        congestion_incumbent_penalty: float,
        # Pricing elasticity
        pricing_elasticity: float,
    ) -> "MultiAgentGame":
        """
        Create initial multi-agent game with N GameState instances.

        Each agent gets its own GameState via GameState.initialise_new_game().
        """
        agent_names = [f"pharma_{i}" for i in range(num_agents)]
        rng = random.Random(seed)

        if bd_phase_weights is None:
            bd_phase_weights = [0.2, 0.4, 0.4]
        if leak_phase_probabilities is None:
            leak_phase_probabilities = [0.2, 0.5, 0.7]

        # Build indications_per_ta dict for asset generators
        indications_per_ta_dict = None
        indication_permutation = None
        if indications_per_ta > 0:
            indications_per_ta_dict = {
                ta: indications_per_ta for ta in THERAPEUTIC_AREAS
            }
            # Random permutation per TA so drift order != observed index
            indication_permutation = {}
            for ta in THERAPEUTIC_AREAS:
                perm = list(range(indications_per_ta))
                rng.shuffle(perm)
                indication_permutation[ta] = perm

        # Create per-agent GameState instances
        agent_states = {}
        for i, agent_name in enumerate(agent_names):
            agent_seed = seed + i
            game_state = GameState.initialise_new_game(
                asset_generator_cls=JSONAssetGenerator,
                num_assets=equilibrium_num_assets,
                max_num_assets=max_num_assets,
                cash=starting_cash,
                horizon=horizon,
                asset_arrival_sensitivity_below=asset_arrival_sensitivity_below,
                asset_arrival_sensitivity_above=asset_arrival_sensitivity_above,
                reinvestment_percentage=reinvestment_percentage,
                global_seed=agent_seed,
                assets_dir=assets_dir,
                ta_experience_config=ta_experience_config,
                uncertain_ptrs_config=uncertain_ptrs_config,
                investment_levels_config=investment_levels_config,
                interim_trial_observations_config=interim_trial_observations_config,
                distributional_ptrs_config=distributional_ptrs_config,
                rd_capacity_config=rd_capacity_config,
                indications_per_ta=indications_per_ta_dict,
                indication_spread=indication_spread,
                indication_drift_speed=indication_drift_speed,
                trial_cost_multiplier=trial_cost_multiplier,
                approval_phase_config=approval_phase_config,
            )
            if indication_permutation:
                game_state._asset_generator.set_indication_permutation(
                    indication_permutation
                )
            agent_states[agent_name] = game_state

        # Create shared market state
        shared_market = SharedMarketState.initialize(
            exclusivity_period=exclusivity_period,
            first_mover_bonus=first_mover_bonus,
            alert_history_length=alert_history_length,
            disable_market_share_competition=disable_market_share_competition,
            seed=seed,
            num_indications_per_ta=indications_per_ta,
            bd_enabled=bd_enabled,
            bd_base_lambda=bd_base_lambda,
            bd_leak_lambda_boost=bd_leak_lambda_boost,
            bd_min_step=bd_min_step,
            bd_num_bid_levels=bd_num_bid_levels,
            bd_break_even_bid_level=bd_break_even_bid_level,
            bd_phase_weights=bd_phase_weights,
            bd_indication_activity_bias=bd_indication_activity_bias,
            leak_phase_probabilities=leak_phase_probabilities,
            congestion_exponent=congestion_exponent,
            congestion_ramp_steps=congestion_ramp_steps,
            congestion_incumbent_penalty=congestion_incumbent_penalty,
        )

        # Create BD asset generator
        if bd_enabled and bd_assets_dir is not None:
            bd_seed = rng.randint(0, 2**31)
            ta_quality_modifiers = agent_states[agent_names[0]]._ta_quality_modifiers
            bd_generator = JSONAssetGenerator(
                bd_seed,
                bd_assets_dir,
                distributional_ptrs_config=distributional_ptrs_config,
                ta_quality_modifiers=ta_quality_modifiers,
                ta_experience_config=ta_experience_config,
                uncertain_ptrs_config=uncertain_ptrs_config,
                indications_per_ta=indications_per_ta_dict,
                indication_spread=indication_spread,
                indication_drift_speed=indication_drift_speed,
                trial_cost_multiplier=trial_cost_multiplier,
                approval_phase_config=approval_phase_config,
            )
            if indication_permutation:
                bd_generator.set_indication_permutation(indication_permutation)
            shared_market.set_bd_asset_generator(bd_generator)

        game = cls(
            agent_states=agent_states,
            shared_market=shared_market,
            time=0,
            horizon=horizon,
            num_agents=num_agents,
            disable_market_share_competition=disable_market_share_competition,
            bd_max_slots=bd_max_slots,
            pricing_elasticity=pricing_elasticity,
        )
        game._rng = rng
        return game

    @property
    def possible_agents(self) -> list[str]:
        """Get list of all agent names."""
        return list(self.agent_states.keys())

    @property
    def active_agents(self) -> list[str]:
        """Get list of non-bankrupt agents."""
        return [
            agent for agent, state in self.agent_states.items() if not state.game_ended
        ]

    def step(
        self,
        investor_actions: dict[
            str,
            dict[uuid.UUID, InvestmentLevel | Literal["invest"] | None],
        ],
        bd_bids: dict[str, list[int]] | None = None,
        pricing_actions: dict[str, dict[uuid.UUID, float]] | None = None,
    ) -> "MultiAgentGame":
        """
        Advance all agents by one step.

        Args:
            investor_actions: Per-agent investment decisions.
                {agent_id: {asset_uuid: InvestmentLevel}}
            bd_bids: Per-agent BD bid levels per slot.
                {agent_id: [slot_0_level, slot_1_level, ...]}
                0=pass, 1-N = fraction of eNPV.
            pricing_actions: Per-agent pricing multipliers for on-market drugs.
                {agent_id: {asset_uuid: price_multiplier}}
                If None, all drugs use 1.0x pricing.

        Returns:
            New MultiAgentGame with updated state.

        """
        from pyxis_portfolio_challenge.environment.market_mechanics import (
            calculate_agent_market_shares,
            resolve_bd_bid,
        )

        new_agent_states = dict(self.agent_states)
        # Mutate shared_market in place — the old MultiAgentGame reference
        # is only used post-step for agent_states (reward calc), not shared_market.
        # This avoids a costly deep copy (~4ms per step).
        new_shared_market = self.shared_market

        # Phase 0: Resolve BD Auctions (one per slot, highest bid wins each)
        if (
            bd_bids
            and new_shared_market.current_bd_assets
            and new_shared_market.bd_enabled
        ):
            num_levels = new_shared_market.bd_num_bid_levels
            break_even_level = new_shared_market.bd_break_even_bid_level
            any_agent_state = next(iter(new_agent_states.values()))
            reinv_pct = any_agent_state.reinvestment_percentage

            for slot_idx, bd_asset in enumerate(new_shared_market.current_bd_assets):
                # Extract per-slot bids from each agent
                slot_bids: dict[str, int] = {}
                for agent_id, agent_bid_list in bd_bids.items():
                    if slot_idx < len(agent_bid_list):
                        slot_bids[agent_id] = agent_bid_list[slot_idx]

                winner, price = resolve_bd_bid(
                    bids=slot_bids,
                    asset=bd_asset,
                    num_levels=num_levels,
                    break_even_level=break_even_level,
                    reinvestment_percentage=reinv_pct,
                    rng=self._rng,
                )

                if winner is not None:
                    state = new_agent_states[winner]
                    if state.game_ended:
                        continue
                    new_cash = state.cash - price
                    new_assets = dict(state.assets)
                    new_assets[bd_asset.id] = bd_asset
                    new_shared_market.register_bd_deal(winner, bd_asset, price=price)
                    logger.debug(
                        f"{winner} acquired BD asset {bd_asset.name} "
                        f"(slot {slot_idx}) for ${price:,.0f}"
                    )

                    updated_realised_costs = list(state.realised_costs)
                    if updated_realised_costs:
                        updated_realised_costs[-1] += price
                    else:
                        updated_realised_costs.append(price)

                    new_agent_states[winner] = GameState(
                        id=state.id,
                        cash=new_cash,
                        time=state.time,
                        horizon=state.horizon,
                        equilibrium_num_assets=state.equilibrium_num_assets,
                        max_num_assets=state.max_num_assets,
                        asset_arrival_sensitivity_below=state.asset_arrival_sensitivity_below,
                        asset_arrival_sensitivity_above=state.asset_arrival_sensitivity_above,
                        reinvestment_percentage=state.reinvestment_percentage,
                        initial_cash=state.initial_cash,
                        assets=new_assets,
                        failed_assets=dict(state.failed_assets),
                        expired_assets=dict(state.expired_assets),
                        realised_costs=updated_realised_costs,
                        realised_revenues=list(state.realised_revenues),
                        running_enpv=list(state.running_enpv),
                        running_eroi=list(state.running_eroi),
                        game_ended=new_cash < 0 or state.time >= state.horizon,
                        ended_reason=(
                            state.ended_reason
                            if state.ended_reason
                            else (
                                "horizon_reached"
                                if state.time >= state.horizon
                                else ("bankrupt" if new_cash < 0 else None)
                            )
                        ),
                        ta_experience=dict(state.ta_experience),
                        capacity_used=state.capacity_used,
                        capacity_base=state.capacity_base,
                        ta_quality_estimates=dict(state.ta_quality_estimates),
                        ta_quality_confidences=dict(state.ta_quality_confidences),
                    )
                    ns = new_agent_states[winner]
                    ns._asset_generator = state._asset_generator
                    ns._rng = state._rng
                    ns._global_seed = state._global_seed
                    ns._ta_experience_config = state._ta_experience_config
                    ns._uncertain_ptrs_config = state._uncertain_ptrs_config
                    ns._investment_levels_config = state._investment_levels_config
                    ns._interim_trial_observations_config = (
                        state._interim_trial_observations_config
                    )
                    ns._distributional_ptrs_config = state._distributional_ptrs_config
                    ns._rd_capacity_config = state._rd_capacity_config
                    ns._ta_quality_modifiers = state._ta_quality_modifiers.copy()

        # Clear BD assets after auctions
        new_shared_market.clear_bd_asset()

        # Phase 1-3: Step each agent's GameState
        # Detect phase transitions for event-driven leaks
        _PHASE_INDEX = {
            TrialPhase.PHASE_1: 0,
            TrialPhase.PHASE_2: 1,
            TrialPhase.PHASE_3: 2,
        }
        if hasattr(TrialPhase, "APPROVAL"):
            _PHASE_INDEX[TrialPhase.APPROVAL] = 3

        all_market_shares: dict[str, dict] = {}

        # Merge all agents' pricing multipliers into a single dict for market share calc
        all_pricing_multipliers: dict[uuid.UUID, float] | None = None
        if pricing_actions is not None:
            all_pricing_multipliers = {}
            for agent_pricing in pricing_actions.values():
                if agent_pricing:
                    all_pricing_multipliers.update(agent_pricing)

        step_num = self.time + 1
        active = [a for a in self.active_agents if not new_agent_states[a].game_ended]
        logger.info(f"Step {step_num}/{self.horizon} — active agents: {', '.join(active)}")

        for agent in self.active_agents:
            if new_agent_states[agent].game_ended:
                continue

            # Snapshot pre-step trial phases for leak detection
            pre_phases: dict[uuid.UUID, TrialPhase | None] = {}
            pre_states: dict[uuid.UUID, AssetState] = {}
            for asset_id, asset in new_agent_states[agent].assets.items():
                pre_states[asset_id] = asset.state
                pre_phases[asset_id] = asset.trial.phase if asset.trial else None

            # Calculate market shares for this agent
            market_shares = None
            if not self.disable_market_share_competition:
                market_shares = calculate_agent_market_shares(
                    agent,
                    new_shared_market,
                    new_agent_states,
                    self.time,
                    all_pricing_multipliers=all_pricing_multipliers,
                    pricing_elasticity=self.pricing_elasticity,
                )
                all_market_shares[agent] = market_shares or {}

            # Get this agent's actions and pricing multipliers
            actions = investor_actions.get(agent, {})
            agent_pricing = None
            if pricing_actions is not None:
                agent_pricing = pricing_actions.get(agent)

            # Step the GameState
            new_state = new_agent_states[agent].step(
                actions,
                market_shares=market_shares,
                pricing_multipliers=agent_pricing,
            )
            new_agent_states[agent] = new_state

            if new_state.game_ended and not self.agent_states[agent].game_ended:
                if new_state.bankrupt:
                    logger.info(
                        f"  {agent} bankrupt at step {step_num}: "
                        f"{new_state.ended_reason}"
                    )

            # Detect phase transitions and generate leaks
            for asset_id, new_asset in new_state.assets.items():
                old_phase = pre_phases.get(asset_id)
                old_state = pre_states.get(asset_id)
                if old_phase is None or old_state != AssetState.InDevelopment:
                    continue

                new_phase = new_asset.trial.phase if new_asset.trial else None
                new_asset_state = new_asset.state

                # Detect phase advancement
                if new_phase is not None and old_phase != new_phase:
                    # Phase changed while still in development
                    old_idx = _PHASE_INDEX.get(old_phase)
                    if old_idx is not None:
                        new_shared_market.generate_phase_transition_leak(
                            agent, new_asset, old_idx
                        )
                elif (
                    new_asset_state == AssetState.OnMarket
                    and old_state == AssetState.InDevelopment
                ):
                    # Asset went directly to market (final phase passed)
                    # This is detected by DRUG_RELEASE alert, no leak needed
                    pass

            # Register drug releases and remove expired drugs
            old_assets = self.agent_states[agent].assets
            for asset_id, new_asset in new_state.assets.items():
                if new_asset.state == AssetState.OnMarket:
                    old_asset = old_assets.get(asset_id)
                    if old_asset is None or old_asset.state != AssetState.OnMarket:
                        new_shared_market.register_drug_release(agent, new_asset)

            # Check for expired drugs
            for asset_id, old_asset in old_assets.items():
                if asset_id not in new_state.assets:
                    if old_asset.state == AssetState.OnMarket:
                        new_shared_market.remove_expired_drug(agent, asset_id)
                elif asset_id in new_state.expired_assets:
                    if old_asset.state == AssetState.OnMarket:
                        new_shared_market.remove_expired_drug(agent, asset_id)

        # Advance shared market time
        new_shared_market.advance_time()

        # Spawn BD asset for next step (uses recent leaks to boost λ)
        agent_portfolios = {
            agent: new_agent_states[agent].assets for agent in self.active_agents
        }
        new_shared_market.spawn_bd_asset(agent_portfolios, max_slots=self.bd_max_slots)

        # Recompute market shares post-step so the cache reflects the
        # current on-market drugs (pre-step shares, used for revenue, may
        # include drugs that expired during the step).
        post_step_shares: dict[str, dict] = {}
        if not self.disable_market_share_competition:
            for agent in self.active_agents:
                if new_agent_states[agent].game_ended:
                    continue
                post_step_shares[agent] = (
                    calculate_agent_market_shares(
                        agent,
                        new_shared_market,
                        new_agent_states,
                        self.time + 1,
                        all_pricing_multipliers=all_pricing_multipliers,
                        pricing_elasticity=self.pricing_elasticity,
                    )
                    or {}
                )

        # Log final summary when game reaches horizon
        if step_num >= self.horizon:
            logger.info("Game complete — final standings:")
            for agent, state in new_agent_states.items():
                status = "BANKRUPT" if state.bankrupt else f"cash={state.cash:,.0f}"
                logger.info(f"  {agent}: {status}, eNPV={state.enpv():,.0f}")

        new_game = MultiAgentGame(
            agent_states=new_agent_states,
            shared_market=new_shared_market,
            time=self.time + 1,
            horizon=self.horizon,
            num_agents=self.num_agents,
            disable_market_share_competition=self.disable_market_share_competition,
            bd_max_slots=self.bd_max_slots,
            pricing_elasticity=self.pricing_elasticity,
        )
        new_game._rng = self._rng
        new_game._cached_market_shares = post_step_shares
        return new_game
