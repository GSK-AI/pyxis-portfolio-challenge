import type { TrialPhaseName } from "./definitionsGameZ";

/**
 * Trial phases in order of progression
 */
export const TRIAL_PHASES: TrialPhaseName[] = ["Phase 1", "Phase 2", "Phase 3"];

/**
 * Helper function to get the index of a phase in the trial progression
 * @param phase The trial phase name
 * @param phaseOrder Array of phase names in progression order
 * @returns The index of the phase, or -1 if not found
 */
function getPhaseIndex(
  phase: TrialPhaseName,
  phaseOrder: TrialPhaseName[],
): number {
  return phaseOrder.indexOf(phase);
}

/**
 * Helper function to check if a phase transition represents progression (moving forward)
 * @param fromPhase The previous phase
 * @param toPhase The current phase
 * @param phaseOrder Array of phase names in progression order
 * @returns True if moving forward in the phase progression, false otherwise
 */
export function isPhaseProgression(
  fromPhase: TrialPhaseName,
  toPhase: TrialPhaseName,
  phaseOrder: TrialPhaseName[],
): boolean {
  const fromIndex = getPhaseIndex(fromPhase, phaseOrder);
  const toIndex = getPhaseIndex(toPhase, phaseOrder);
  return fromIndex !== -1 && toIndex !== -1 && toIndex > fromIndex;
}

/**
 * Helper function to check if a phase is the first phase
 * @param phase The trial phase name
 * @param phaseOrder Array of phase names in progression order (optional, defaults to TRIAL_PHASES)
 * @returns True if the phase is the first phase, false otherwise
 */
export function isFirstPhase(
  phase: TrialPhaseName | null,
  phaseOrder: TrialPhaseName[] = TRIAL_PHASES,
): boolean {
  if (!phase || phaseOrder.length === 0) return false;
  return getPhaseIndex(phase, phaseOrder) === 0;
}
