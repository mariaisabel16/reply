import { BRAND_COLORS } from "../branding";
import "./BrandMarkIcon.css";

export type BrandMarkVariant = "header" | "companion";

type Props = {
  variant?: BrandMarkVariant;
  className?: string;
};

/**
 * TUM-Farben + Pilot-Theme: Kapitänsmütze, Aviator-Brille, Schal, kleine Propeller-Andeutung.
 */
export function BrandMarkIcon({ variant = "header", className }: Props) {
  const animated = variant === "companion";
  const rootClass = [
    "brand-mark",
    animated ? "brand-mark--animated" : "brand-mark--static",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <svg
      className={rootClass}
      viewBox="0 0 120 120"
      width="120"
      height="120"
      aria-hidden
      focusable="false"
    >
      <defs>
        <linearGradient id="bm-body" x1="10%" y1="0%" x2="90%" y2="100%">
          <stop offset="0%" stopColor={BRAND_COLORS.tumBlueDeep} />
          <stop offset="42%" stopColor={BRAND_COLORS.tumBlue} />
          <stop offset="100%" stopColor={BRAND_COLORS.pilotCyan} />
        </linearGradient>
        <linearGradient id="bm-cap-crown" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor={BRAND_COLORS.tumBlueBright} />
          <stop offset="100%" stopColor={BRAND_COLORS.tumBlueDeep} />
        </linearGradient>
        <linearGradient id="bm-goggle-metal" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#e8ecf2" />
          <stop offset="50%" stopColor="#8f98a8" />
          <stop offset="100%" stopColor="#4a5363" />
        </linearGradient>
        <radialGradient id="bm-lens" cx="35%" cy="30%" r="70%">
          <stop offset="0%" stopColor="rgba(190, 235, 255, 0.75)" />
          <stop offset="55%" stopColor="rgba(70, 140, 190, 0.45)" />
          <stop offset="100%" stopColor="rgba(20, 60, 100, 0.55)" />
        </radialGradient>
        <clipPath id="bm-scarf-clip">
          <rect x="16" y="72" width="88" height="44" rx="20" />
        </clipPath>
      </defs>

      <ellipse cx="60" cy="108" rx="36" ry="8" fill="rgba(0,0,0,0.42)" opacity="0.5" />

      <path
        className="brand-mark__body"
        d="M60 18c-24 0-42 18-42 40.2 0 15.5 8.6 28.8 21.6 35.2 2.8 1.4 6 2.3 9.4 2.6 3.4.3 6.8 0 10-.7 1.6-.3 3.2-.9 4.7-1.5 1.5-.7 3-1.5 4.3-2.4 13-6.4 21.6-19.7 21.6-35.2C102 36 84 18 60 18Z"
        fill="url(#bm-body)"
        stroke="#0b0f18"
        strokeWidth="3.2"
        strokeLinejoin="round"
      />

      <path
        d="M60 68v32"
        stroke="rgba(0,0,0,0.35)"
        strokeWidth="2.4"
        strokeLinecap="round"
        opacity="0.55"
      />

      <rect x="22" y="66" width="14" height="5" rx="1.5" fill="#e8c54d" stroke="#0b0f18" strokeWidth="1.4" opacity="0.95" />
      <rect x="84" y="66" width="14" height="5" rx="1.5" fill="#e8c54d" stroke="#0b0f18" strokeWidth="1.4" opacity="0.95" />

      <g clipPath="url(#bm-scarf-clip)" className="brand-mark__scarf">
        <rect x="18" y="76" width="84" height="36" rx="10" fill={BRAND_COLORS.tumWhite} />
        <g stroke={BRAND_COLORS.tumBlue} strokeWidth="5" strokeLinecap="round" opacity="0.92">
          <line x1="-8" y1="82" x2="128" y2="62" />
          <line x1="-8" y1="94" x2="128" y2="74" />
          <line x1="-8" y1="106" x2="128" y2="86" />
        </g>
      </g>

      <ellipse cx="34" cy="66" rx="9" ry="6" fill="#ff4d8d" opacity="0.18" />
      <ellipse cx="86" cy="66" rx="9" ry="6" fill="#ff4d8d" opacity="0.18" />

      <path
        className="brand-mark__mouth"
        d="M44 80c6 9 26 9 32 0"
        fill="none"
        stroke="#0b0f18"
        strokeWidth="3"
        strokeLinecap="round"
      />

      <g className="brand-mark__goggles">
        <ellipse cx="41" cy="58" rx="14" ry="14" fill="url(#bm-lens)" stroke="#0b0f18" strokeWidth="2" />
        <ellipse cx="79" cy="58" rx="14" ry="14" fill="url(#bm-lens)" stroke="#0b0f18" strokeWidth="2" />
        <ellipse cx="43" cy="60" rx="4" ry="4.8" fill="#0b0f18" opacity="0.9" />
        <ellipse cx="81" cy="59" rx="4" ry="4.8" fill="#0b0f18" opacity="0.9" />
        <ellipse cx="44.2" cy="58.6" rx="1.3" ry="1.5" fill="#fff" opacity="0.92" />
        <ellipse cx="82.4" cy="57.6" rx="1.3" ry="1.5" fill="#fff" opacity="0.92" />
        <ellipse cx="41" cy="58" rx="15.5" ry="15.5" fill="none" stroke="url(#bm-goggle-metal)" strokeWidth="2.6" />
        <ellipse cx="79" cy="58" rx="15.5" ry="15.5" fill="none" stroke="url(#bm-goggle-metal)" strokeWidth="2.6" />
        <path
          d="M56 58h8"
          stroke="url(#bm-goggle-metal)"
          strokeWidth="3.2"
          strokeLinecap="round"
        />
      </g>

      <g className="brand-mark__cap">
        <path
          d="M32 6 Q60 -4 88 6 L86 20 H34 Z"
          fill="url(#bm-cap-crown)"
          stroke="#0b0f18"
          strokeWidth="2.6"
          strokeLinejoin="round"
        />
        <path
          d="M52 8 L60 4 L68 8"
          fill="none"
          stroke="#e8c54d"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity="0.95"
        />
        <rect x="30" y="18" width="60" height="10" rx="2" fill="#121826" stroke="#0b0f18" strokeWidth="2" />
        <rect x="34" y="20.5" width="52" height="4.5" rx="1" fill="#e8c54d" opacity="0.95" />
        <path
          d="M22 26 Q60 44 98 26 L96 31 Q60 50 24 31 Z"
          fill="#0f141f"
          stroke="#0b0f18"
          strokeWidth="2.2"
          strokeLinejoin="round"
        />
        <path
          d="M38 30 Q60 42 82 30"
          fill="none"
          stroke="rgba(255,255,255,0.22)"
          strokeWidth="1.6"
          strokeLinecap="round"
        />
      </g>

      <g className="brand-mark__prop" stroke="#0b0f18" strokeWidth="1.5" strokeLinecap="round">
        <circle cx="102" cy="18" r="3.4" fill="#4a5363" strokeWidth="1.2" />
        <line x1="102" y1="18" x2="102" y2="31" />
        <line x1="102" y1="18" x2="93" y2="24.5" />
        <line x1="102" y1="18" x2="111" y2="24.5" />
      </g>
    </svg>
  );
}
