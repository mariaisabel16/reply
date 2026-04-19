import { BRAND } from "../branding";
import { BrandMarkIcon } from "./BrandMarkIcon";
import "./CompanionMascot.css";

/** Kleiner Co-Pilot im Eck — gleiche Markenfigur wie im Header. */
export function CompanionMascot() {
  return (
    <div
      className="companion"
      role="img"
      aria-label={`${BRAND.name} Begleiter`}
      title="CampusPilot — dein Co-Pilot im Chat."
    >
      <div className="companion-halo" aria-hidden />
      <div className="companion-chromatic" aria-hidden />
      <div className="companion-flash" aria-hidden />
      <BrandMarkIcon variant="companion" className="companion-mark" />
    </div>
  );
}
