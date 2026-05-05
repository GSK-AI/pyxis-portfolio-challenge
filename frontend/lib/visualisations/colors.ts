export const modalityColors = {
  Biological: "#76ACD2",
  Chemical: "#F8B69B",
  Vaccine: "#89D0BA",
} as {
  [_: string]: string;
};

export const taColors = {
  "Respiratory and Immunology": "#E7D99F",
  RI: "#E7D99F",
  Oncology: "#DA97C0",
  "Vaccines and Infectious Disease": "#89D0BA",
  "Vx&ID": "#89D0BA",
} as {
  [_: string]: string;
};

export const phaseColors = {
  Preclinical: "#E0E0E0",
  "Phase 1": "#D5CAEE",
  "Phase 2": "#9E9AC7",
  "Phase 3": "#54278F",
  Registration: "#2E0854",
} as {
  [_: string]: string;
};

export const defaultLegendColor = "#f2f2f2";

export const portfolioTag = {
  primary: "#1ca8c0",
  secondary: "#fe7800",
  both: "#606060",
} as {
  [_: string]: string;
};

export function getPhaseColor(phase: string) {
  const phases = Object.keys(phaseColors);
  const findPhase = phases.find((_) => phase.includes(_));

  if (findPhase) {
    return phaseColors[findPhase];
  }

  return phaseColors[phase] ?? defaultLegendColor;
}
