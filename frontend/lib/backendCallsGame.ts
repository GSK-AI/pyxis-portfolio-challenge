import { z } from "zod";
import { getIdToken } from "./msal-auth";
import {
  GameStart,
  gameStepResponseSchema,
  hintResponseSchema,
  gameLevelsResponseSchema,
  leaderboardResponseSchema,
  leaderboardEntrySchema,
  agentsResponseSchema,
  gameComparisonSchema,
  opponentAgentSchema,
  multiAgentGameStepSchema,
  MultiAgentGameStart,
  MultiAgentStepRequest,
} from "./definitionsGameZ";

// Helper to get backend URL from config
let cachedBackendGameUrl: string | null = null;

async function getBackendGameUrl(): Promise<string> {
  if (cachedBackendGameUrl) return cachedBackendGameUrl;

  const response = await fetch("/api/config");
  if (!response.ok) throw new Error("Failed to fetch config");
  const config = await response.json();
  cachedBackendGameUrl = config.backendGameUrl;

  if (!cachedBackendGameUrl) {
    throw new Error("Backend game URL not configured");
  }

  return cachedBackendGameUrl;
}

// Helper to fetch with ID token
async function fetchWithIdToken(
  url: string,
  options?: RequestInit,
): Promise<Response> {
  const token = await getIdToken();

  if (!token) {
    throw new Error("No authentication token available");
  }

  const headers = {
    ...options?.headers,
    Authorization: `Bearer ${token}`,
  };

  return fetch(url, { ...options, headers });
}

// Helper to validate response with Zod schema
async function fetchAndValidate<T>(
  url: string,
  schema: z.ZodSchema<T>,
  options?: RequestInit,
): Promise<T> {
  const response = await fetchWithIdToken(url, options);
  const json = await response.json();

  if (!response.ok) {
    if ("message" in json) {
      throw new Error(json.message);
    }
    throw new Error(`${JSON.stringify(json)}`);
  }

  return schema.parse(json);
}

// Helper to create POST options
function jsonPost(body: unknown): RequestInit {
  return {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  };
}

// Endpoint builders
async function endpointGameStart(): Promise<string> {
  const baseUrl = await getBackendGameUrl();
  return `${baseUrl}/game/start`;
}

async function endpointGameStep(gameId: string): Promise<string> {
  const baseUrl = await getBackendGameUrl();
  return `${baseUrl}/game/${gameId}/step`;
}

async function endpointGameHint(
  gameId: string,
  agentName?: string,
): Promise<string> {
  const baseUrl = await getBackendGameUrl();
  const query = agentName ? `?agent_name=${encodeURIComponent(agentName)}` : "";
  return `${baseUrl}/game/${gameId}/hint${query}`;
}

async function endpointGameLevels(): Promise<string> {
  const baseUrl = await getBackendGameUrl();
  return `${baseUrl}/game/levels`;
}

async function endpointGameLeaderboardGlobal(): Promise<string> {
  const baseUrl = await getBackendGameUrl();
  return `${baseUrl}/game/leaderboard/global`;
}

async function endpointGameLeaderboardLevels(levelId: number): Promise<string> {
  const baseUrl = await getBackendGameUrl();
  return `${baseUrl}/game/leaderboard/${levelId}`;
}

async function endpointGameAgents(): Promise<string> {
  const baseUrl = await getBackendGameUrl();
  return `${baseUrl}/game/agents`;
}

async function endpointGameComparison(gameId: string): Promise<string> {
  const baseUrl = await getBackendGameUrl();
  return `${baseUrl}/game/${gameId}/comparison_dashboard`;
}

async function endpointGameHighscore(levelId: number): Promise<string> {
  const baseUrl = await getBackendGameUrl();
  return `${baseUrl}/game/level/${levelId}/highscore`;
}

export async function startGame(body: GameStart) {
  return await fetchAndValidate(
    await endpointGameStart(),
    gameStepResponseSchema,
    jsonPost(body),
  );
}

export async function stepGame(
  gameId: string,
  actions: Record<string, string>,
) {
  const response = await fetchWithIdToken(await endpointGameStep(gameId), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(actions),
  });
  const responseJson = await response.json();
  if (!response.ok) {
    if ("message" in responseJson) {
      throw new Error(responseJson.message);
    }
    throw new Error(`${JSON.stringify(responseJson)}`);
  }
  return responseJson;
}

export async function hintGame(gameId: string, agentName?: string) {
  return await fetchAndValidate(
    await endpointGameHint(gameId, agentName),
    hintResponseSchema,
    jsonPost({}),
  );
}

export async function getLevels() {
  return await fetchAndValidate(
    await endpointGameLevels(),
    gameLevelsResponseSchema,
  );
}

export async function getGlobalLeaderboard() {
  return await fetchAndValidate(
    await endpointGameLeaderboardGlobal(),
    leaderboardResponseSchema,
  );
}

export async function getLevelLeaderboard(levelId: number) {
  return await fetchAndValidate(
    await endpointGameLeaderboardLevels(levelId),
    leaderboardResponseSchema,
  );
}

export async function getAgents() {
  return await fetchAndValidate(
    await endpointGameAgents(),
    agentsResponseSchema,
  );
}

export async function getGameComparison(gameId: string) {
  return await fetchAndValidate(
    await endpointGameComparison(gameId),
    gameComparisonSchema,
    jsonPost({}),
  );
}

export async function getLevelHighScore(levelId: number) {
  return await fetchAndValidate(
    await endpointGameHighscore(levelId),
    leaderboardEntrySchema,
  );
}

// --- Multi-Agent API Functions ---

async function endpointMultiAgentOpponents(): Promise<string> {
  const baseUrl = await getBackendGameUrl();
  return `${baseUrl}/game/multi/opponents`;
}

async function endpointMultiAgentConfig(): Promise<string> {
  const baseUrl = await getBackendGameUrl();
  return `${baseUrl}/game/multi/config`;
}

async function endpointMultiAgentStart(): Promise<string> {
  const baseUrl = await getBackendGameUrl();
  return `${baseUrl}/game/multi/start`;
}

async function endpointMultiAgentStep(gameId: string): Promise<string> {
  const baseUrl = await getBackendGameUrl();
  return `${baseUrl}/game/multi/${gameId}/step`;
}

export async function getMultiAgentOpponents() {
  return await fetchAndValidate(
    await endpointMultiAgentOpponents(),
    z.array(opponentAgentSchema),
  );
}

export async function getMultiAgentConfig() {
  const baseUrl = await getBackendGameUrl();
  const response = await fetchWithIdToken(`${baseUrl}/game/multi/config`);
  if (!response.ok) throw new Error("Failed to fetch multi-agent config");
  return response.json();
}

export async function startMultiAgentGame(body: MultiAgentGameStart) {
  return await fetchAndValidate(
    await endpointMultiAgentStart(),
    multiAgentGameStepSchema,
    jsonPost(body),
  );
}

export async function stepMultiAgentGame(
  gameId: string,
  payload: MultiAgentStepRequest,
) {
  return await fetchAndValidate(
    await endpointMultiAgentStep(gameId),
    multiAgentGameStepSchema,
    jsonPost(payload),
  );
}

// Get game config defaults from backend
export async function getGameConfig(): Promise<GameStart> {
  const baseUrl = await getBackendGameUrl();
  const response = await fetchWithIdToken(`${baseUrl}/game/config`);
  if (!response.ok) {
    throw new Error("Failed to fetch game config");
  }
  const config = await response.json();
  return {
    num_assets: config.num_assets,
    max_num_assets: config.max_num_assets,
    horizon: config.horizon,
    starting_cash: config.starting_cash,
    global_seed: config.global_seed,
    level_idx: -1,
  };
}
