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
export type TherapeuticArea = z.infer<typeof therapeuticAreaSchema>;

export const assetTypeSchema = z.enum(["internal", "BD"]);
export type AssetType = z.infer<typeof assetTypeSchema>;

export const assetStateSchema = z.enum([
  "Idle",
  "In Development",
  "On Market",
  "Expired",
  "Failed",
]);
export type AssetState = z.infer<typeof assetStateSchema>;

export const dataTypeSchema = z.enum(["cost", "revenue"]);
export type DataType = z.infer<typeof dataTypeSchema>;

export const actionTypeSchema = z.enum([
  "invest",
  "stop",
  "none",
  "minimal",
  "standard",
  "accelerated",
]);
export type ActionType = z.infer<typeof actionTypeSchema>;

export const investmentLevelSchema = z.enum([
  "none",
  "minimal",
  "standard",
  "accelerated",
]);
export type InvestmentLevel = z.infer<typeof investmentLevelSchema>;

export const trialPhaseNameSchema = z.string();
export type TrialPhaseName = z.infer<typeof trialPhaseNameSchema>;

export const interimResultSchema = z.enum(["positive", "negative"]);
export type InterimResult = z.infer<typeof interimResultSchema>;

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
});
export type TrialPhaseType = z.infer<typeof trialPhaseSchema>;

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
  enpv: z.number(),
  expected_costs: z.array(z.number()),
  expected_revenues: z.array(z.number()),
  eroi: z.number(),
  current_investment_level: investmentLevelSchema.optional(),
  available_actions: z.array(actionTypeSchema).optional(),
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
export type InvestmentLevelConfig = z.infer<typeof investmentLevelConfigSchema>;

export const investmentLevelsConfigSchema = z.object({
  levels: z.record(z.string(), investmentLevelConfigSchema),
  base_capacity: z.number(),
  overage_max_penalty: z.number(),
  overage_cost_max_penalty: z.number(),
});
export type InvestmentLevelsConfig = z.infer<
  typeof investmentLevelsConfigSchema
>;

export const gameStepSchema = z.object({
  id: z.string(),
  cash: z.number(),
  time: z.number(),
  horizon: z.number(),
  assets: z.record(z.string(), assetSchema),
  expired_assets: z.record(z.string(), assetSchema),
  realised_costs: z.array(z.number()),
  realised_revenues: z.array(z.number()),
  game_ended: z.boolean(),
  ended_reason: z.string().nullable(),
  capital_over_time: z.array(z.number()),
  enpv_over_time: z.array(z.number()),
  eroi_over_time: z.array(z.number()),
  ta_experience: z.record(z.string(), z.number()),
  experience_to_full_knowledge: z.number(),
  max_total_experience: z.number().nullable(),
  // R&D Capacity
  capacity_used: z.number(),
  capacity_base: z.number(),
  success_modifier: z.number(),
  cost_modifier: z.number(),
  // Feature flags
  ta_experience_enabled: z.boolean(),
  investment_levels_enabled: z.boolean(),
  interim_observations_enabled: z.boolean(),
  distributional_ptrs_enabled: z.boolean(),
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

export const transactionRecordSchema = z.object({
  time: z.number(),
  cost: z.number(),
  selection: z.array(z.string()),
  balance: z.number(),
});
export type TransactionRecord = z.infer<typeof transactionRecordSchema>;

export const gameLevelSchema = z.object({
  level_idx: z.number(),
  user_has_completed: z.boolean(),
  num_assets: z.number(),
  max_num_assets: z.number().optional(),
  horizon: z.number(),
  starting_cash: z.number(),
  global_seed: z.number().optional(),
});
export type GameLevel = z.infer<typeof gameLevelSchema>;

export const gameLevelsResponseSchema = z.array(gameLevelSchema);
export type GameLevelsResponse = z.infer<typeof gameLevelsResponseSchema>;

export const leaderboardEntrySchema = z.object({
  game_id: z.string(),
  user_id: z.string(),
  av_enpv: z.number(),
});
export type LeaderboardEntry = z.infer<typeof leaderboardEntrySchema>;

export const leaderboardResponseSchema = z.array(leaderboardEntrySchema);
export type LeaderboardResponse = z.infer<typeof leaderboardResponseSchema>;

export const agentSchema = z.object({
  name: z.string(),
  cost: z.number(),
});
export type Agent = z.infer<typeof agentSchema>;

export const agentsResponseSchema = z.array(agentSchema);
export type AgentsResponse = z.infer<typeof agentsResponseSchema>;

export const gameComparisonSchema = z.object({
  game_id: z.string(),
  av_enpv: z.record(z.string(), z.number()),
  final_enpv: z.record(z.string(), z.number()),
  final_eroi: z.record(z.string(), z.number()),
  final_capital: z.record(z.string(), z.number()),
  realised_eroi: z.record(z.string(), z.number()),
  enpv_over_time: z.record(z.string(), z.array(z.number())),
  eroi_over_time: z.record(z.string(), z.array(z.number())).optional(),
});
export type GameComparison = z.infer<typeof gameComparisonSchema>;

export const customSeedSchema = z.number();

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
});
export type BDAssetType = z.infer<typeof bdAssetSchema>;

export const alertSchema = z.object({
  step: z.number(),
  event_type: z.enum(["drug_release", "bd_deal", "pipeline_leak"]),
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
export type OpponentSummary = z.infer<typeof opponentSummarySchema>;

export const multiAgentGameStepSchema = z.object({
  game_id: z.string(),
  player_agent_name: z.string(),
  player_state: gameStepSchema,
  bd_assets: z.array(bdAssetSchema),
  bd_enabled: z.boolean(),
  bd_bid_prices: z.array(z.array(z.number())),
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
  bd_bids: z.array(z.number()),
});
export type MultiAgentStepRequest = z.infer<typeof multiAgentStepRequestSchema>;

// --- Playthrough Replay Schemas ---

export const agentActionRecordSchema = z.object({
  investment_decisions: z.record(z.string(), z.string()),
  bd_bids: z.array(z.number()),
  bd_assets_at_bid: z.array(bdAssetSchema),
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
export type StepRecord = z.infer<typeof stepRecordSchema>;

export const playthroughMetadataSchema = z.object({
  num_agents: z.number(),
  agent_ids: z.array(z.string()),
  agent_names: z.record(z.string(), z.string()).optional().default({}),
  horizon: z.number(),
  seed: z.number(),
  captured_at: z.string(),
});
export type PlaythroughMetadata = z.infer<typeof playthroughMetadataSchema>;

export const playthroughConfigSchema = z.object({
  bd_enabled: z.boolean(),
  bd_num_bid_levels: z.number(),
  bd_break_even_bid_level: z.number(),
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
});
export type PlaythroughConfig = z.infer<typeof playthroughConfigSchema>;

export const playthroughDataSchema = z.object({
  metadata: playthroughMetadataSchema,
  config: playthroughConfigSchema,
  initial_agent_states: z.record(z.string(), gameStepSchema),
  initial_shared_market: sharedMarketSnapshotSchema,
  steps: z.array(stepRecordSchema),
});
export type PlaythroughData = z.infer<typeof playthroughDataSchema>;
