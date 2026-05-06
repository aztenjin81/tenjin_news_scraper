export type SourceKind = "wire" | "regional" | "primary" | "social" | "analysis" | "state";

export const SOURCE_LABELS: Record<SourceKind, string> = {
  wire: "Wire",
  regional: "Regional",
  primary: "Primary",
  social: "Social",
  analysis: "Analysis",
  state: "State media",
};

export const SOURCE_EXAMPLES: Record<SourceKind, string> = {
  wire: "Reuters, AP, AFP, Bloomberg",
  regional: "Times of Israel, Tehran Times, Al Jazeera",
  primary: "IDF Spokesperson, US State Dept, UN OCHA",
  social: "X, Bluesky, Telegram channels",
  analysis: "ISW, CSIS, RUSI, Carnegie",
  state: "Press TV, RT, Xinhua, TASS",
};

export const SOURCE_KINDS: readonly SourceKind[] = [
  "wire",
  "regional",
  "primary",
  "social",
  "analysis",
  "state",
] as const;
