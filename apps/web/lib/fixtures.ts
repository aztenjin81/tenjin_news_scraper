import type { Article } from "./api";

const MIN = 60_000;

export function fixtureArticles(slug: string, now: number = Date.now()): Article[] {
  switch (slug) {
    case "iran-us":
      return [
        {
          id: "a1",
          url: "https://www.tehrantimes.com/",
          title: "Iran summons UK envoy over MP's remarks on IRGC designation",
          outlet: "Tehran Times",
          source_kind: "state",
          source_label: "State media",
          fetched_at: new Date(now - 4 * MIN).toISOString(),
          published_at: new Date(now - 4 * MIN).toISOString(),
        },
        {
          id: "a2",
          url: "https://www.reuters.com/",
          title: "Treasury sanctions network supplying components to Iran's UAV program",
          outlet: "Reuters",
          source_kind: "wire",
          source_label: "Wire",
          fetched_at: new Date(now - 12 * MIN).toISOString(),
          published_at: new Date(now - 12 * MIN).toISOString(),
        },
        {
          id: "a3",
          url: "https://www.state.gov/",
          title:
            "State Department: 'No appetite for direct conflict, but options remain on the table'",
          outlet: "State Dept Press Briefing",
          source_kind: "primary",
          source_label: "Primary",
          fetched_at: new Date(now - 22 * MIN).toISOString(),
          published_at: new Date(now - 22 * MIN).toISOString(),
        },
        {
          id: "a4",
          url: "https://www.understandingwar.org/",
          title: "ISW: Iranian proxy posture in Iraq and Syria — May assessment",
          outlet: "Institute for the Study of War",
          source_kind: "analysis",
          source_label: "Analysis",
          fetched_at: new Date(now - 38 * MIN).toISOString(),
          published_at: new Date(now - 38 * MIN).toISOString(),
        },
        {
          id: "a5",
          url: "https://x.com/",
          title: "IRGC Navy commander posts photos of new fast-attack craft in Bandar Abbas",
          outlet: "X / @IRGC_Navy_Updates",
          source_kind: "social",
          source_label: "Social",
          fetched_at: new Date(now - 55 * MIN).toISOString(),
          published_at: new Date(now - 55 * MIN).toISOString(),
        },
        {
          id: "a6",
          url: "https://www.politico.eu/",
          title: "EU foreign ministers to discuss Iran sanctions package on Thursday",
          outlet: "Politico Europe",
          source_kind: "regional",
          source_label: "Regional",
          fetched_at: new Date(now - 70 * MIN).toISOString(),
          published_at: new Date(now - 70 * MIN).toISOString(),
        },
      ];
    case "israel-gaza":
      return [
        {
          id: "b1",
          url: "https://www.timesofisrael.com/",
          title: "IDF strikes Hezbollah weapons depot in eastern Lebanon, military says",
          outlet: "Times of Israel",
          source_kind: "regional",
          source_label: "Regional",
          fetched_at: new Date(now - 3 * MIN).toISOString(),
          published_at: new Date(now - 3 * MIN).toISOString(),
        },
        {
          id: "b2",
          url: "https://reliefweb.int/",
          title: "OCHA: Aid trucks crossing Rafah averaged 92/day last week",
          outlet: "UN OCHA ReliefWeb",
          source_kind: "primary",
          source_label: "Primary",
          fetched_at: new Date(now - 18 * MIN).toISOString(),
          published_at: new Date(now - 18 * MIN).toISOString(),
        },
        {
          id: "b3",
          url: "https://apnews.com/",
          title: "Hamas delegation arrives in Cairo for indirect talks",
          outlet: "AP",
          source_kind: "wire",
          source_label: "Wire",
          fetched_at: new Date(now - 44 * MIN).toISOString(),
          published_at: new Date(now - 44 * MIN).toISOString(),
        },
      ];
    case "houthis-red-sea":
      return [
        {
          id: "c1",
          url: "https://www.gov.uk/government/organisations/united-kingdom-maritime-trade-operations",
          title: "Bulk carrier reports near miss from drone 60nm SW of Hodeidah — UKMTO",
          outlet: "UKMTO",
          source_kind: "primary",
          source_label: "Primary",
          fetched_at: new Date(now - 2 * MIN).toISOString(),
          published_at: new Date(now - 2 * MIN).toISOString(),
          is_breaking: true,
        },
        {
          id: "c2",
          url: "https://www.centcom.mil/",
          title: "US Central Command: pre-emptive strike on launcher in Houthi-controlled territory",
          outlet: "USCENTCOM",
          source_kind: "primary",
          source_label: "Primary",
          fetched_at: new Date(now - 15 * MIN).toISOString(),
          published_at: new Date(now - 15 * MIN).toISOString(),
        },
        {
          id: "c3",
          url: "https://www.bloomberg.com/",
          title:
            "Maersk reroutes Asia–Europe flagship service around Cape of Good Hope through end of quarter",
          outlet: "Bloomberg",
          source_kind: "wire",
          source_label: "Wire",
          fetched_at: new Date(now - 40 * MIN).toISOString(),
          published_at: new Date(now - 40 * MIN).toISOString(),
        },
      ];
    default:
      return [];
  }
}
