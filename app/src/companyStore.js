// Company-card lookups + a tiny module-level opener so any EventCard can open the
// company modal without prop-drilling a handler through every view.
import cards from '../assets/company_cards.json';

export const COMPANY_CARDS = cards;

export function tickerForEvent(ev) {
  if (ev.company_ticker) return ev.company_ticker;
  const hi = (ev.stock_impacts || []).find(
    i => String(i.confidence || '').toLowerCase().includes('high'));
  return hi ? hi.ticker : null;
}

export function companyForEvent(ev) {
  const t = tickerForEvent(ev);
  return t && COMPANY_CARDS[t] ? COMPANY_CARDS[t] : null;
}

let _opener = null;
export function registerCompanyOpener(fn) { _opener = fn; }
export function openCompany(ticker) { if (ticker && _opener) _opener(ticker); }
