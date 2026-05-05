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
export function getPhaseIndex(
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

/**
 * Helper function to check if a phase is beyond the first phase
 * @param phase The trial phase name
 * @param phaseOrder Array of phase names in progression order
 * @returns True if the phase is beyond the first phase, false otherwise
 */
export function isPostFirstPhase(
  phase: TrialPhaseName | null,
  phaseOrder: TrialPhaseName[],
): boolean {
  if (!phase || phaseOrder.length === 0) return false;
  const index = getPhaseIndex(phase, phaseOrder);
  return index > 0; // First phase is at index 0, so anything > 0 is beyond it
}

/**
 * Helper function to extract phase order from asset data
 * @param assets Array of assets or record of assets
 * @returns Array of unique phase names found in the assets, in no particular order
 */
export function extractPhasesFromAssets(
  assets:
    | Array<{ trials: Record<string, any> }>
    | Record<string, { trials: Record<string, any> }>,
): TrialPhaseName[] {
  const allPhases = new Set<TrialPhaseName>();

  const assetArray = Array.isArray(assets) ? assets : Object.values(assets);

  for (const asset of assetArray) {
    if (asset.trials) {
      Object.keys(asset.trials).forEach((phase) => {
        if (asset.trials[phase]) {
          // Only include phases that exist (not null/undefined)
          allPhases.add(phase as TrialPhaseName);
        }
      });
    }
  }

  return Array.from(allPhases);
}

/**
 * Helper function to determine logical phase order based on common naming patterns
 * This is a fallback when no explicit order is provided by the backend
 * @deprecated Use TRIAL_PHASES constant instead
 * @param phases Array of phase names
 * @returns Array of phases sorted in logical order
 */
export function inferPhaseOrder(phases: TrialPhaseName[]): TrialPhaseName[] {
  // Common phase ordering patterns
  const phaseOrderMap = new Map<string, number>([
    // Common prefixes
    ["pre", 0],
    ["preclinical", 0],
    ["discovery", -1],

    // Phase numbers
    ["phase 1", 10],
    ["phase i", 10],
    ["1", 10],
    ["phase 2", 20],
    ["phase ii", 20],
    ["2", 20],
    ["phase 3", 30],
    ["phase iii", 30],
    ["3", 30],
    ["phase 4", 40],
    ["phase iv", 40],
    ["4", 40],

    // Later stages
    ["registration", 100],
    ["approval", 100],
    ["regulatory", 100],
    ["launch", 200],
    ["market", 200],
    ["commercial", 200],
  ]);

  return phases.sort((a, b) => {
    const aLower = a.toLowerCase();
    const bLower = b.toLowerCase();

    // Find the best matching order value for each phase
    let aOrder = 1000; // Default high value for unknown phases
    let bOrder = 1000;

    for (const [key, value] of phaseOrderMap) {
      if (aLower.includes(key)) {
        aOrder = Math.min(aOrder, value);
      }
      if (bLower.includes(key)) {
        bOrder = Math.min(bOrder, value);
      }
    }

    // If both have the same order value, fall back to alphabetical
    if (aOrder === bOrder) {
      return a.localeCompare(b);
    }

    return aOrder - bOrder;
  });
}

/**
 * Legacy helper function for backward compatibility
 * @deprecated This function no longer works without a phase order. Use isPostFirstPhase instead.
 */
export function isPostPreClinicalPhase(phase: TrialPhaseName | null): boolean {
  // Since we can't know the phase order, we'll just check if it's not Pre-clinical
  // This is a best-guess fallback for legacy code
  return phase !== null && phase !== "Pre-clinical";
}
