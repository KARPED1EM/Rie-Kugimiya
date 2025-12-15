// @ts-check

/** Multi-emotion glow renderer */
export function applyEmotionTheme(emotionMap) {
  const container = document.querySelector(".app-container");
  if (!container) return;
  if (!emotionMap || typeof emotionMap !== "object") {
    clearEmotionTheme();
    return;
  }

  /** Base HSL palette */
  const palette = {
    neutral: { h: 0, s: 0, l: 70 },

    angry: { h: 4, s: 90, l: 50 },
    excited: { h: 22, s: 95, l: 54 },
    happy: { h: 52, s: 95, l: 58 },

    caring: { h: 145, s: 70, l: 48 },
    playful: { h: 95, s: 85, l: 52 },
    confused: { h: 182, s: 72, l: 46 },
    surprised: { h: 198, s: 88, l: 56 },

    sad: { h: 220, s: 78, l: 54 },
    serious: { h: 235, s: 58, l: 44 },

    anxious: { h: 275, s: 70, l: 52 },
    shy: { h: 305, s: 62, l: 60 },
    embarrassed: { h: 332, s: 86, l: 58 },
    affectionate: { h: 350, s: 90, l: 58 },

    tired: { h: 210, s: 22, l: 60 },
    bored: { h: 40, s: 18, l: 62 },
  };

  /** Intensity tuning */
  const intensity = {
    low:     { alpha: 0.10, dl: 20, ds: -46 },
    medium:  { alpha: 0.20, dl: 14, ds: -32 },
    high:    { alpha: 0.35, dl: 8,  ds: -16 },
    extreme: { alpha: 0.50, dl: -4, ds: 0 },
  };

  const colors = [];
  for (const [rawKey, rawVal] of Object.entries(emotionMap)) {
    const key = String(rawKey || "").toLowerCase();
    if (!key || key === "neutral") continue;
    const base = palette[key];
    if (!base) continue;
    const iv = intensity[String(rawVal || "").toLowerCase()] || intensity.medium;

    colors.push({
      key,
      h: base.h,
      s: clamp(base.s + iv.ds, 4, 92),
      l: clamp(base.l + iv.dl, 30, 84),
      a: clamp(iv.alpha, 0.06, 1),
    });
  }

  if (colors.length === 0) {
    clearEmotionTheme();
    return;
  }

  const ordered = orderColorsGently(colors);
  const gradient = buildGlowGradient(ordered);
  applyGradientWithTransition(container, gradient);
}

export function clearEmotionTheme() {
  const container = document.querySelector(".app-container");
  if (!container) return;
  container.style.setProperty("--emotion-opacity-1", "0");
  container.style.setProperty("--emotion-opacity-2", "0");
  container.classList.remove("emotion-enabled");
}

let activeLayer = 1;

/** Cross-fade layers */
function applyGradientWithTransition(container, gradient) {
  const nextLayer = activeLayer === 1 ? 2 : 1;
  container.style.setProperty(`--emotion-gradient-${nextLayer}`, gradient);
  container.style.setProperty("--emotion-opacity-1", nextLayer === 1 ? "1" : "0");
  container.style.setProperty("--emotion-opacity-2", nextLayer === 2 ? "1" : "0");
  container.classList.add("emotion-enabled");
  activeLayer = nextLayer;
}

/** Build gradient for full-page background with smooth color blending */
function buildGlowGradient(colors) {
  const stops = colors.map(
    (c) => `hsla(${c.h} ${c.s}% ${c.l}% / ${c.a})`
  );

  if (stops.length === 1) {
    const c = stops[0];
    // Single color: use radial gradient from center with elliptical shape
    return `radial-gradient(ellipse at 50% 50%, ${c} 0%, transparent 70%)`;
  }

  if (stops.length === 2) {
    // Two colors: diagonal gradient with smooth blending
    return `linear-gradient(135deg, ${stops[0]} 0%, ${stops[1]} 100%)`;
  }

  // Multiple colors: create smooth flowing gradient
  // Distribute colors evenly across the gradient
  const gradientStops = colors.map((_, i) => {
    const pos = (i * 100) / colors.length;
    return `${stops[i]} ${pos}%`;
  });
  
  // Complete the loop for seamless animation
  gradientStops.push(`${stops[0]} 100%`);

  // Use diagonal gradient for dynamic flow
  return `linear-gradient(135deg, ${gradientStops.join(", ")})`;
}

/** Gentle hue ordering */
function orderColorsGently(input) {
  const remaining = input.slice();
  remaining.sort((a, b) => a.a - b.a);

  const start = remaining.shift();
  if (!start) return [];
  const ordered = [start];

  while (remaining.length) {
    const last = ordered[ordered.length - 1];
    let bestIdx = 0;
    let bestD = Infinity;

    for (let i = 0; i < remaining.length; i++) {
      const d = colorDistance(last, remaining[i]);
      if (d < bestD) {
        bestD = d;
        bestIdx = i;
      }
    }
    ordered.push(remaining.splice(bestIdx, 1)[0]);
  }

  return ordered;
}

/** HSL distance */
function colorDistance(a, b) {
  const dhRaw = Math.abs(a.h - b.h);
  const dh = Math.min(dhRaw, 360 - dhRaw) / 180;
  const ds = Math.abs(a.s - b.s) / 100;
  const dl = Math.abs(a.l - b.l) / 100;
  return dh * 1.4 + ds * 0.7 + dl * 1.0;
}

function clamp(v, min, max) {
  return Math.max(min, Math.min(max, v));
}
