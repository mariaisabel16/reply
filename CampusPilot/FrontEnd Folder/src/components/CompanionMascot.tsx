import { BRAND, BRAND_COLORS } from "../branding";
import "./CompanionMascot.css";

/**
 * Kleiner UI-Begleiter: TUM (Doktorhut, Blau/Weiß) + CampusPilot (Fliegerbrille, Pilotenschal, Cyan-Akzent).
 */
export function CompanionMascot() {
  return (
    <div
      className="companion"
      role="img"
      aria-label={`${BRAND.name} Begleiter`}
      title="TUM CampusPilot — ich begleite dich durch den Chat."
    >
      <div className="companion-halo" aria-hidden />
      <div className="companion-flash" aria-hidden />
      <svg
        className="companion-svg"
        viewBox="0 0 120 120"
        width="120"
        height="120"
        aria-hidden
        focusable="false"
      >
        <defs>
          <linearGradient id="companion-body" x1="14%" y1="0%" x2="86%" y2="100%">
            <stop offset="0%" stopColor={BRAND_COLORS.tumBlueDeep} />
            <stop offset="45%" stopColor={BRAND_COLORS.tumBlue} />
            <stop offset="100%" stopColor={BRAND_COLORS.pilotCyan} />
          </linearGradient>
          <linearGradient id="companion-cap-board" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor={BRAND_COLORS.tumBlueBright} />
            <stop offset="100%" stopColor={BRAND_COLORS.tumBlueDeep} />
          </linearGradient>
          <linearGradient id="companion-goggle" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#e8ecf2" />
            <stop offset="55%" stopColor="#9aa3b2" />
            <stop offset="100%" stopColor="#5c6575" />
          </linearGradient>
          <radialGradient id="companion-cheek" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgba(255,255,255,0.55)" />
            <stop offset="100%" stopColor="rgba(255,255,255,0)" />
          </radialGradient>
          <clipPath id="companion-scarf-clip">
            <rect x="20" y="76" width="80" height="36" rx="16" />
          </clipPath>
        </defs>

        <ellipse cx="60" cy="108" rx="34" ry="7" fill="rgba(0,0,0,0.35)" opacity="0.45" />

        <path
          d="M60 22c-22 0-38 16.5-38 36.8 0 14.2 7.8 26.4 19.4 32.4 2.6 1.3 5.5 2.1 8.6 2.4 3.1.3 6.3.1 9.3-.6 1.5-.3 3-.8 4.4-1.4 1.4-.6 2.7-1.3 3.9-2.1 11.6-6 19.4-18.2 19.4-32.4C98 38.5 82 22 60 22Z"
          fill="url(#companion-body)"
        />

        <path
          d="M34 52c4-10 14.5-17 26-17s22 7 26 17"
          fill="none"
          stroke="rgba(255,255,255,0.22)"
          strokeWidth="2.2"
          strokeLinecap="round"
        />

        <g className="companion-goggles" stroke="url(#companion-goggle)" fill="none" strokeWidth="1.6" opacity="0.92">
          <ellipse cx="42" cy="58" rx="12.5" ry="13" />
          <ellipse cx="78" cy="58" rx="12.5" ry="13" />
          <path d="M54.5 58h11" strokeLinecap="round" />
        </g>

        <ellipse cx="42" cy="58" rx="10" ry="11" fill="#0b1020" opacity="0.92" />
        <ellipse cx="78" cy="58" rx="10" ry="11" fill="#0b1020" opacity="0.92" />
        <ellipse cx="44" cy="55" rx="3.2" ry="3.6" fill="#ffffff" opacity="0.95" />
        <ellipse cx="80" cy="55" rx="3.2" ry="3.6" fill="#ffffff" opacity="0.95" />

        <path
          d="M48 76c6 5 18 5 24 0"
          fill="none"
          stroke="rgba(255,255,255,0.55)"
          strokeWidth="2.4"
          strokeLinecap="round"
        />

        <ellipse cx="36" cy="64" rx="9" ry="6" fill="url(#companion-cheek)" opacity="0.55" />
        <ellipse cx="84" cy="64" rx="9" ry="6" fill="url(#companion-cheek)" opacity="0.55" />

        <g className="companion-scarf" clipPath="url(#companion-scarf-clip)">
          <rect x="22" y="78" width="76" height="30" rx="8" fill={BRAND_COLORS.tumWhite} opacity="0.98" />
          <rect x="22" y="84" width="76" height="5" fill={BRAND_COLORS.tumBlue} opacity="0.95" />
          <rect x="22" y="93" width="76" height="5" fill={BRAND_COLORS.tumBlue} opacity="0.95" />
          <rect x="22" y="102" width="76" height="5" fill={BRAND_COLORS.tumBlue} opacity="0.95" />
        </g>

        <path
          d="M38 30c8-6 18-9 28-8 6 .6 11.5 2.8 16 6.2"
          fill="none"
          stroke="rgba(255,255,255,0.35)"
          strokeWidth="2"
          strokeLinecap="round"
        />

        <g className="companion-cap">
          <path
            d="M16 22h88L96 7H24L16 22Z"
            fill="url(#companion-cap-board)"
            stroke="rgba(255,255,255,0.22)"
            strokeWidth="1"
            strokeLinejoin="round"
          />
          <rect x="28" y="20" width="64" height="9" rx="3" fill={BRAND_COLORS.tumWhite} opacity="0.98" />
          <path d="M60 7V3" stroke={BRAND_COLORS.tumWhite} strokeWidth="1.8" strokeLinecap="round" />
          <circle cx="60" cy="1.8" r="2.8" fill={BRAND_COLORS.tumWhite} />
        </g>

        <g className="companion-sparkles" aria-hidden>
          <path d="M22 40l2.2 6.4 6.8 2-6.8 2L22 57l-2.2-6.6-6.6-2 6.6-2L22 40Z" fill="#ffffff" opacity="0.9" />
          <path d="M96 28l1.6 4.6 5 1.4-5 1.5L96 40l-1.6-4.7-4.8-1.4 4.8-1.5L96 28Z" fill="#ffffff" opacity="0.75" />
        </g>
      </svg>
    </div>
  );
}
