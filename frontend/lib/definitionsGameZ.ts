import { z } from "zod";

export const gameStartSchema = z.object({
  num_assets: z.number(),
  max_num_assets: z.number().optional(),
  horizon: z.number(),
  starting_cash: z.number(),
  global_seed: z.number().optional(),
  level_idx: z.number().optional(),
});
export type GameStart = z.infer<typeof gameStartSchema>;

export const therapeuticAreaSchema = z.enum([
  "oncology",
  "vaccines and infectious disease",
  "respiratory and immunology",
]);

export const assetTypeSchema = z.enum(["internal", "BD"]);

export const assetStateSchema = z.enum([
  "Idle",
  "In Development",
  "On Market",
  "Expired",
  "Failed",
  // Agent voluntarily abandoned the asset (drop_action feature); distinct from
  // Failed (trial outcome) and Expired (patent lapse).
  "Dropped",
]);

export const dataTypeSchema = z.enum(["cost", "revenue"]);
export type DataType = z.infer<typeof dataTypeSchema>;

export const actionTypeSchema = z.enum([
  "invest",
  "stop",
  "none",
  "minimal",
  "standard",
  "accelerated",
  // Voluntary abandonment (drop_action feature, mutually exclusive with levels).
  "drop",
]);
export type ActionType = z.infer<typeof actionTypeSchema>;

export const investmentLevelSchema = z.enum([
  "none",
  "minimal",
  "standard",
  "accelerated",
]);

export const trialPhaseNameSchema = z.string();
export type TrialPhaseName = z.infer<typeof trialPhaseNameSchema>;

export const interimResultSchema = z.enum(["positive", "negative"]);

export const trialPhaseSchema = z.object({
  cost_remaining: z.number(),
  time_remaining: z.number(),
  ptrs: z.number(),
  interim_result: interimResultSchema.nullable().optional(),
  has_interim_observation: z.boolean().optional(),
  // Distributional PTRS fields
  ptrs_expected: z.number().optional(),
  ptrs_confidence: z.number().optional(),
  ptrs_range_low: z.number().optional(),
  ptrs_range_high: z.number().optional(),
  // PTRS readings (ptrs_readings feature): paid readings commissioned on this
  // trial so far, and the precision-weighted "effective readings" the observation
  // exposes. Optional: absent on pre-readings replay data.
  ptrs_sample_count: z.number().optional(),
  ptrs_effective_readings: z.number().optional(),
});

export const assetSchema = z.object({
  id: z.string(),
  name: z.string(),
  therapeutic_area: therapeuticAreaSchema,
  type: assetTypeSchema,
  indication: z.number(),
  indication_name: z.string(),
  description: z.string(),
  max_revenue: z.number(),
  time_until_max_revenue: z.number(),
  time_until_patent_expiry: z.number(),
  trials: z.record(trialPhaseNameSchema, trialPhaseSchema),
  state: assetStateSchema,
  pending_trial_phase: trialPhaseNameSchema.nullable().optional(),
  time_on_market: z.number(),
  cost_this_step: z.number(),
  cost_to_invest_this_step: z.number(),
  revenue_this_step: z.number(),
  enpv: z.number(), // full expected NPV (business value); not the score
  cash_enpv: z.number(), // cash-adjusted eNPV: value that reaches cash and scores
  expected_costs: z.array(z.number()),
  expected_revenues: z.array(z.number()),
  eroi: z.number(),
  current_investment_level: investmentLevelSchema.optional(),
  available_actions: z.array(actionTypeSchema).optional(),
  // Brand-equity marketing score and its decayed floor. Attached only to
  // live (on-market / in-dev) assets, so optional on expired/dropped buckets.
  brand_score: z.number().optional(),
  brand_score_floor: z.number().optional(),
  // Cash cost of a brand-equity spend on this drug this step (scales with drug
  // size). Attached only to live assets; 0 when marketing is off.
  be_cost: z.number().optional(),
  // Forward-looking projection of this drug's brand score after the next step,
  // for each spend decision (_if_spend pays the cost, _if_hold lets it decay
  // toward the floor). Lets the panel preview the impact of a push before the
  // user commits. Optional: absent on pre-marketing replay data.
  brand_score_if_spend: z.number().optional(),
  brand_score_if_hold: z.number().optional(),
  // PTRS readings (ptrs_readings feature): cumulative cash cost of commissioning
  // 1..N readings on this drug's current trial this step (index i = cost of i+1
  // readings). Empty/absent when the feature is off or the drug has no pending
  // trial (dead / on-market).
  ptrs_reading_costs: z.array(z.number()).optional(),
});
export type AssetSchemaType = z.infer<typeof assetSchema>;

// Investment levels configuration schemas
export const investmentLevelConfigSchema = z.object({
  cost_modifier: z.number(),
  speed_modifier: z.number(),
  success_modifier: z.number(),
  capacity_cost: z.number(),
  experience_modifier: z.number(),
});

export const investmentLevelsConfigSchema = z.object({
  levels: z.record(z.string(), investmentLevelConfigSchema),
  base_capacity: z.number(),
  overage_max_penalty: z.number(),
  overage_cost_max_penalty: z.number(),
});

export const gameStepSchema = z.object({
  id: z.string(),
  cash: z.number(),
  time: z.number(),
  horizon: z.number(),
  assets: z.record(z.string(), assetSchema),
  expired_assets: z.record(z.string(), assetSchema),
  // Assets the agent voluntarily abandoned (drop_action feature).
  dropped_assets: z.record(z.string(), assetSchema),
  realised_costs: z.array(z.number()),
  realised_revenues: z.array(z.number()),
  game_ended: z.boolean(),
  ended_reason: z.string().nullable(),
  capital_over_time: z.array(z.number()),
  enpv_over_time: z.array(z.number()),
  eroi_over_time: z.array(z.number()),
  // Fraction of gross sales retained as cash (the rest covers other business
  // costs). Used to show budget/capital figures as the cash you actually receive.
  reinvestment_percentage: z.number(),
  ta_experience: z.record(z.string(), z.number()),
  experience_to_full_knowledge: z.number(),
  max_total_experience: z.number().nullable(),
  // R&D Capacity
  capacity_used: z.number(),
  capacity_base: z.number(),
  success_modifier: z.number(),
  cost_modifier: z.number(),
  // Clinical sites: operational_sites host trials; sites_in_development is the
  // list of remaining build delays for sites still under construction.
  clinical_sites_enabled: z.boolean(),
  operational_sites: z.number(),
  sites_in_development: z.array(z.number()),
  free_sites: z.number(),
  sites_occupied: z.number(),
  // Cash cost of the next site (Fibonacci curve); 0 when the feature is off.
  next_site_purchase_cost: z.number(),
  // Feature flags
  ta_experience_enabled: z.boolean(),
  investment_levels_enabled: z.boolean(),
  interim_observations_enabled: z.boolean(),
  distributional_ptrs_enabled: z.boolean(),
  // Marketing feature: gates the demand-creation and brand-equity panels.
  marketing_enabled: z.boolean(),
  // PTRS readings feature: gates the per-asset readings panel and BD diligence
  // stepper. Per-asset cost curves live on each asset (ptrs_reading_costs).
  ptrs_readings_enabled: z.boolean(),
  // TA quality estimates (distributional PTRS feature)
  ta_quality: z.record(
    z.string(),
    z.object({
      estimate: z.number(),
      confidence: z.number(),
    }),
  ),
  // Investment levels configuration
  investment_levels_config: investmentLevelsConfigSchema.nullable(),
});
export type GameStepSchemaType = z.infer<typeof gameStepSchema>;

export const gameStepResponseSchema = gameStepSchema;

export type GameStepResponse = z.infer<typeof gameStepResponseSchema>;

export const hintResponseSchema = z.union([
  z.record(z.record(actionTypeSchema.nullable())), // { "AgentName": { "assetid1": "invest", "asset3": "standard" } }
  z.object({}), // Empty object case
]);

export type HintResponse = z.infer<typeof hintResponseSchema>;

export const agentSchema = z.object({
  name: z.string(),
  cost: z.number(),
});
export type Agent = z.infer<typeof agentSchema>;

export const agentsResponseSchema = z.array(agentSchema);

// --- Multi-Agent Schemas ---

export const opponentAgentSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
});
export type OpponentAgent = z.infer<typeof opponentAgentSchema>;

export const bdAssetSchema = z.object({
  asset_id: z.string(),
  name: z.string(),
  therapeutic_area: z.string(),
  indication: z.number(),
  indication_name: z.string(),
  max_revenue: z.number(),
  time_until_max_revenue: z.number(),
  time_until_patent_expiry: z.number(),
  trial_phase: z.string(),
  ptrs: z.number(),
  enpv: z.number(),
  cash_enpv: z.number(), // cash-adjusted eNPV; a fair-value anchor for a cash bid
  // PTRS readings (ptrs_readings feature): this player's private diligence on the
  // candidate — readings so far, the effective-readings signal, and the cost curve
  // for buying 1..N more this step. Optional/empty when the feature is off or the
  // candidate has no pending trial.
  ptrs_sample_count: z.number().optional(),
  ptrs_effective_readings: z.number().optional(),
  ptrs_reading_costs: z.array(z.number()).optional(),
});
export type BDAssetType = z.infer<typeof bdAssetSchema>;

export const alertSchema = z.object({
  step: z.number(),
  event_type: z.enum([
    "drug_release",
    "bd_deal",
    "pipeline_leak",
    "clinical_site_deal",
    // Marketing spend leaks (brand-equity and demand-creation).
    "be_spend",
    "dc_spend",
  ]),
  agent_id: z.string(),
  therapeutic_area: z.string(),
  indication: z.number(),
  indication_name: z.string(),
  details: z.record(z.unknown()),
});
export type AlertType = z.infer<typeof alertSchema>;

export const indicationMarketSchema = z.object({
  therapeutic_area: z.string(),
  indication: z.number(),
  indication_name: z.string(),
  first_mover_agent: z.string().nullable(),
  incumbent_agent: z.string().nullable(),
  exclusivity_remaining: z.number(),
  active_drugs: z.record(z.string(), z.number()),
  player_market_share: z.number(),
  market_shares: z.record(z.string(), z.number()).optional(),
  // Demand multiplier driven by demand-creation marketing spend (1.0 = base).
  demand_multiplier: z.number(),
  // Forward-looking projection of the demand multiplier after the next step, for
  // each spend decision (_if_spend pays the cost, _if_hold lets it decay toward
  // 1.0). Lets the panel preview the impact of a spend before the user commits.
  // Optional: absent on pre-marketing replay data.
  demand_multiplier_if_spend: z.number().optional(),
  demand_multiplier_if_hold: z.number().optional(),
});
export type IndicationMarket = z.infer<typeof indicationMarketSchema>;

export const opponentSummarySchema = z.object({
  agent_name: z.string(),
  display_name: z.string(),
  agent_type: z.string(),
  cash: z.number(),
  num_assets: z.number(),
  num_on_market: z.number(),
  num_in_development: z.number(),
  enpv: z.number(),
  cumulative_reward: z.number(),
  game_ended: z.boolean(),
  ended_reason: z.string().nullable(),
});

export const multiAgentGameStepSchema = z.object({
  game_id: z.string(),
  player_agent_name: z.string(),
  player_state: gameStepSchema,
  bd_assets: z.array(bdAssetSchema),
  bd_enabled: z.boolean(),
  // Whether a clinical site is up for the PvP auction this step (clinical_sites).
  site_auction_active: z.boolean(),
  alerts: z.array(alertSchema),
  indication_markets: z.array(indicationMarketSchema),
  opponents: z.array(opponentSummarySchema),
  time: z.number(),
  horizon: z.number(),
  player_cumulative_reward: z.number(),
  player_bankrupt: z.boolean(),
  game_ended: z.boolean(),
  ended_reason: z.string().nullable(),
  last_bd_acquisitions: z.record(z.string(), z.array(z.string())),
  // Flat cash cost of sizing one indication via demand creation this step
  // (marketing feature); same for every indication, 0 when marketing is off.
  dc_cost: z.number(),
});
export type MultiAgentGameStep = z.infer<typeof multiAgentGameStepSchema>;

export const multiAgentGameStartSchema = z.object({
  num_assets: z.number(),
  max_num_assets: z.number(),
  horizon: z.number(),
  starting_cash: z.number(),
  global_seed: z.number(),
  num_opponents: z.number(),
  opponent_agents: z.array(z.string()),
});
export type MultiAgentGameStart = z.infer<typeof multiAgentGameStartSchema>;

export const multiAgentStepRequestSchema = z.object({
  investment_actions: z.record(z.string(), actionTypeSchema.nullable()),
  // Per-BD-asset cash bids in GBP (0 = pass). An overbid can bankrupt the bidder.
  bd_bids: z.array(z.number()),
  // Clinical sites (clinical_sites feature): buy one new site this step
  // (upgrade) and/or bid cash in the PvP site auction (site_bid GBP, 0 = pass).
  // Always sent (false/0 when idle) so every enabled head is present each step.
  upgrade: z.boolean(),
  site_bid: z.number(),
  // Marketing (marketing feature): binary spend this step (1 = spend, absent =
  // skip). demand_creation is keyed by indication ("{therapeutic_area}:{indication}")
  // and brand_equity by asset id. Always sent (empty when idle) so every enabled
  // head is present each step.
  demand_creation: z.record(z.string(), z.number()),
  brand_equity: z.record(z.string(), z.number()),
  // PTRS readings (ptrs_readings feature): per-asset count of paid diligence
  // readings to commission this step, keyed by asset id (portfolio or BD
  // candidate; the engine routes by id). Always sent (empty when idle) so every
  // enabled head is present each step.
  ptrs_research: z.record(z.string(), z.number()),
});
export type MultiAgentStepRequest = z.infer<typeof multiAgentStepRequestSchema>;

// --- Playthrough Replay Schemas ---

export const agentActionRecordSchema = z.object({
  investment_decisions: z.record(z.string(), z.string()),
  // Per-BD-asset cash bids in GBP (0 = pass).
  bd_bids: z.array(z.number()),
  bd_assets_at_bid: z.array(bdAssetSchema),
  // PTRS research readings commissioned this step: per portfolio asset
  // (asset_id -> reading count, zero-count assets omitted) and per BD slot.
  ptrs_research: z.record(z.string(), z.number()),
  bd_ptrs_research: z.array(z.number()),
  // Marketing spend this step (only spent slots present, value == 1):
  // demand_creation keyed by indication key, brand_equity by asset id.
  demand_creation: z.record(z.string(), z.number()),
  brand_equity: z.record(z.string(), z.number()),
  // Clinical-site actions: bought a new site, and PvP site-auction bid in GBP.
  upgrade: z.boolean(),
  site_bid: z.number(),
});
export type AgentActionRecord = z.infer<typeof agentActionRecordSchema>;

export const bdAcquisitionSchema = z.object({
  name: z.string(),
  price: z.number(),
});
export type BDAcquisition = z.infer<typeof bdAcquisitionSchema>;

export const sharedMarketSnapshotSchema = z.object({
  bd_assets: z.array(bdAssetSchema),
  alerts: z.array(alertSchema),
  indication_markets: z.array(indicationMarketSchema),
  last_bd_acquisitions: z.record(z.string(), z.array(bdAcquisitionSchema)),
});
export type SharedMarketSnapshot = z.infer<typeof sharedMarketSnapshotSchema>;

export const stepRecordSchema = z.object({
  step: z.number(),
  actions: z.record(z.string(), agentActionRecordSchema),
  agent_states: z.record(z.string(), gameStepSchema),
  shared_market: sharedMarketSnapshotSchema,
  rewards: z.record(z.string(), z.number()),
  cumulative_rewards: z.record(z.string(), z.number()),
});

export const playthroughMetadataSchema = z.object({
  num_agents: z.number(),
  agent_ids: z.array(z.string()),
  agent_names: z.record(z.string(), z.string()).optional().default({}),
  horizon: z.number(),
  // Null when the playthrough was captured without an explicit seed.
  seed: z.number().nullable(),
  captured_at: z.string(),
});
export type PlaythroughMetadata = z.infer<typeof playthroughMetadataSchema>;

export const playthroughConfigSchema = z.object({
  bd_enabled: z.boolean(),
  bd_max_bid: z.number(),
  reinvestment_percentage: z.number(),
  investment_levels_enabled: z.boolean(),
  interim_observations_enabled: z.boolean(),
  distributional_ptrs_enabled: z.boolean(),
  ta_experience_enabled: z.boolean(),
  congestion_exponent: z.number(),
  congestion_ramp_steps: z.number(),
  congestion_incumbent_penalty: z.number(),
  rd_capacity_enabled: z.boolean(),
  rd_capacity_base: z.number(),
  // Feature flags for the marketing, clinical-site and PTRS-reading systems.
  marketing_enabled: z.boolean(),
  clinical_sites_enabled: z.boolean(),
  site_auction_enabled: z.boolean(),
  ptrs_readings_enabled: z.boolean(),
  drop_action_enabled: z.boolean(),
});

export const playthroughDataSchema = z.object({
  metadata: playthroughMetadataSchema,
  config: playthroughConfigSchema,
  initial_agent_states: z.record(z.string(), gameStepSchema),
  initial_shared_market: sharedMarketSnapshotSchema,
  steps: z.array(stepRecordSchema),
});
export type PlaythroughData = z.infer<typeof playthroughDataSchema>;
