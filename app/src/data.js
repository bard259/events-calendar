// Loads the pipeline export and provides date-indexed lookups.
import raw from '../assets/events.json';

export const MONTH = raw.month; // "2026-06"
export const CATEGORIES = raw.categories; // [{id,name}]
export const ALL_EVENTS = raw.events;

// Map: "YYYY-MM-DD" -> [events]
export function groupByDate(events) {
  const map = {};
  for (const ev of events) {
    (map[ev.event_date] ||= []).push(ev);
  }
  // sort each day's events: importance then category
  const rank = { high: 0, medium: 1, low: 2 };
  for (const k of Object.keys(map)) {
    map[k].sort(
      (a, b) =>
        (rank[a.importance] ?? 1) - (rank[b.importance] ?? 1) ||
        a.category_id - b.category_id
    );
  }
  return map;
}

export function categoryName(id) {
  const c = CATEGORIES.find((c) => c.id === id);
  return c ? c.name : 'Unknown';
}

// Parse "2026-06" -> {year, month0} (month0 = 0-indexed)
export function parseMonth(m) {
  const [y, mm] = m.split('-').map(Number);
  return { year: y, month0: mm - 1 };
}

// Sorted list of distinct "YYYY-MM" months that actually have events.
export const MONTHS = [...new Set(ALL_EVENTS.map((e) => e.event_date.slice(0, 7)))].sort();

// Full date range covered by the data (for week/day navigation clamping).
const _dates = ALL_EVENTS.map((e) => e.event_date).sort();
export const RANGE_START = _dates[0] || `${MONTH}-01`;
export const RANGE_END   = _dates[_dates.length - 1] || `${MONTH}-30`;

// Events sorted by when they were collected (newest first) — powers the "Latest" page.
export function latestEvents() {
  return [...ALL_EVENTS].sort((a, b) =>
    String(b.collected_at || '').localeCompare(String(a.collected_at || '')));
}

// The most recent collection date ("YYYY-MM-DD") present in the data.
export const LAST_COLLECTED = ALL_EVENTS.reduce(
  (mx, e) => (e.collected_at && e.collected_at > mx ? e.collected_at : mx), ''
).slice(0, 10);

// Case-insensitive search across title, entity, description, category and tickers.
export function searchEvents(query) {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  return ALL_EVENTS.filter((e) => {
    const tickers = (e.stock_impacts || []).map((i) => i.ticker).join(' ');
    const hay = `${e.title} ${e.entity} ${e.description} ${e.category} ${tickers}`.toLowerCase();
    return hay.includes(q);
  }).sort((a, b) => a.event_date.localeCompare(b.event_date));
}
