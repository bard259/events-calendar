// ─── Design tokens ─────────────────────────────────────────────────────────
// Bloomberg-terminal-inspired: deep navy base, crisp whites, vivid category
// accents. One consistent accent blue for interactive elements.

export const colors = {
  // backgrounds
  bg:           '#080e1a',   // deepest
  surface:      '#0e1724',   // card / cell
  surfaceRaised:'#152030',   // modal / raised panel
  surfaceHover: '#1a2840',   // hover state
  border:       '#1e2f47',
  borderAccent: '#2a4060',

  // text
  text:         '#e2eaf6',
  textSecondary:'#8fa3bf',
  textMuted:    '#4a6080',

  // interactive
  accent:       '#3d8ef8',   // links, selected, active
  accentDim:    '#1a3d70',

  // special
  today:        '#f5c842',
  todayText:    '#080e1a',

  // source type pills
  api:          '#22c55e',
  scraper:      '#a78bfa',
  synthetic:    '#64748b',
};

// Per-category: used for left-border stripes, dots, and filter chips
export const categoryColors = {
  1: '#38bdf8',  // Macro — sky blue
  2: '#818cf8',  // Central Bank — indigo
  3: '#34d399',  // Corporate Financial — emerald
  4: '#f472b6',  // Strategic — pink
  5: '#fb923c',  // Operational — orange
  6: '#f87171',  // Regulatory — red
  7: '#fbbf24',  // Industry — amber
  8: '#22d3ee',  // Geopolitical — cyan
  9: '#a855f7',  // AI & Compute — violet
};

export const categoryIcons = {
  1: '📊', 2: '🏦', 3: '💹', 4: '🚀',
  5: '🛸', 6: '⚖️',  7: '⚡', 8: '🌐',
  9: '🧠',
};

export const importanceConfig = {
  high:   { color: '#f87171', label: 'HIGH',   dot: '●' },
  medium: { color: '#fbbf24', label: 'MED',    dot: '●' },
  low:    { color: '#4a6080', label: 'LOW',    dot: '○' },
};

export const directionConfig = {
  1:  { color: '#34d399', symbol: '▲', label: 'Positive' },
  '-1': { color: '#f87171', symbol: '▼', label: 'Negative' },
  0:  { color: '#fbbf24', symbol: '◆', label: 'Watch'    },
};

export const confidenceColor = {
  high:   '#34d399',
  medium: '#fbbf24',
  low:    '#4a6080',
};
