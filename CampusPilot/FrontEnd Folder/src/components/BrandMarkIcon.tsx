import { BRAND_COLORS } from "../branding";
import "./BrandMarkIcon.css";

export type BrandMarkVariant = "header" | "companion";

type Props = {
  variant?: BrandMarkVariant;
  className?: string;
};

/**
 * Minimal front-facing pilot mark: TUM blues, captain cap, aviator frame — symmetric, cockpit-inspired.
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
        <linearGradient id="bm-helmet" x1="18%" y1="0%" x2="82%" y2="100%">
          <stop offset="0%" stopColor={BRAND_COLORS.tumBlueBright} />
          <stop offset="45%" stopColor={BRAND_COLORS.tumBlue} />
          <stop offset="100%" stopColor={BRAND_COLORS.tumBlueDeep} />
        </linearGradient>
        <linearGradient id="bm-cap" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#1a2a42" />
          <stop offset="100%" stopColor="#0c1524" />
        </linearGradient>
        <linearGradient id="bm-lens" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="rgba(200, 240, 255, 0.55)" />
          <stop offset="100%" stopColor="rgba(40, 90, 140, 0.45)" />
        </linearGradient>
      </defs>

      <ellipse cx="60" cy="108" rx="26" ry="5" fill="rgba(15, 23, 42, 0.14)" />

      <ellipse
        className="brand-mark__body"
        cx="60"
        cy="64"
        rx="28"
        ry="32"
        fill="url(#bm-helmet)"
        stroke="#0f172a"
        strokeWidth="2.2"
      />

      <path
        className="brand-mark__mouth"
        d="M50 76 Q60 82 70 76"
        fill="none"
        stroke="#0f172a"
        strokeWidth="1.8"
        strokeLinecap="round"
        opacity="0.42"
      />

      <g className="brand-mark__goggles">
        <ellipse cx="44" cy="58" rx="12.5" ry="11" fill="url(#bm-lens)" stroke="#0f172a" strokeWidth="2" />
        <ellipse cx="76" cy="58" rx="12.5" ry="11" fill="url(#bm-lens)" stroke="#0f172a" strokeWidth="2" />
        <rect x="56" y="54" width="8" height="3.2" rx="1" fill="#1e293b" />
        <circle cx="45.5" cy="56" r="1.6" fill="#fff" opacity="0.75" />
        <circle cx="77.5" cy="56" r="1.6" fill="#fff" opacity="0.75" />
      </g>

      <g className="brand-mark__cap">
        <path
          d="M32 40 L88 40 L84 26 Q60 9 36 26 Z"
          fill="url(#bm-cap)"
          stroke="#0f172a"
          strokeWidth="2"
          strokeLinejoin="round"
        />
        <path
          d="M38 34 Q60 22 82 34"
          fill="none"
          stroke="#c9a227"
          strokeWidth="2"
          strokeLinecap="round"
          opacity="0.92"
        />
        <rect x="36" y="37" width="48" height="4.5" rx="1" fill="#c9a227" opacity="0.95" />
        <path
          d="M22 40 Q60 52 98 40 L96 45 Q60 58 24 45 Z"
          fill="#0a1018"
          stroke="#0f172a"
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
      </g>

      <g className="brand-mark__emblem" transform="translate(60 21)">
        <path
          d="M0 -3.5 L-7 3.5 M0 -3.5 L7 3.5 M-5 2 H5"
          fill="none"
          stroke="#e2e8f0"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity="0.88"
        />
      </g>

      <g className="brand-mark__scarf">
        <rect
          x="28"
          y="84"
          width="64"
          height="22"
          rx="11"
          fill={BRAND_COLORS.tumWhite}
          stroke="#0f172a"
          strokeWidth="1.6"
        />
        <line
          x1="30"
          y1="95"
          x2="90"
          y2="95"
          stroke={BRAND_COLORS.tumBlue}
          strokeWidth="2.8"
          strokeLinecap="round"
          opacity="0.88"
        />
      </g>
    </svg>
  );
}
