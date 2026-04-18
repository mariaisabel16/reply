/**
 * Öffentliche Produktmarke: TUM (Hochschule) + CampusPilot (Projektname).
 * Ordner heißen weiterhin `CampusPilot/…` im Repo.
 */
export const BRAND = {
  /** Kurzname für Header, Title, API */
  name: "TUM CampusPilot",
  /** Eine Zeile Untertitel */
  tagline: "Studienorganisation an der TU München",
} as const;

/**
 * Markenfarben für UI & Maskottchen.
 * Verbindliche TUM-Farbwerte: Corporate Design im myTUM-Portal.
 */
export const BRAND_COLORS = {
  tumBlue: "#0065BD",
  tumBlueDeep: "#004578",
  tumBlueBright: "#1f8ad1",
  tumWhite: "#ffffff",
  /** Digitaler Akzent; ergänzt TUM-Blau in Gradients */
  pilotCyan: "#0c7c9c",
} as const;
