import React from 'react';
import { View, Text, Pressable, StyleSheet, Linking } from 'react-native';
import { colors, categoryColors, categoryIcons, importanceConfig } from './theme';
import { categoryName } from './data';
import { openCompany } from './companyStore';

function timeLabel(ev) {
  if (!ev.event_datetime) return null;
  const d = new Date(ev.event_datetime);
  return isNaN(d) ? null : d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
}

function dateLabel(ev) {
  if (!ev.event_date) return null;
  return new Date(ev.event_date + 'T00:00:00').toLocaleDateString(undefined, {
    weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
  });
}

// Tidy a raw event title for display: drop the "(announced in SEC filing)"-style
// provenance cruft and title-case an ALL-CAPS company prefix ("CALERES INC:" → "Caleres Inc:").
const _tc = w => (w ? w[0].toUpperCase() + w.slice(1).toLowerCase() : w);
function cleanTitle(ev) {
  let t = (ev.title || '').replace(/\s*\((?:announced in SEC filing|mined[^)]*|via[^)]*)\)/ig, '').trim();
  t = t.replace(/^([A-Z0-9&.,'’\- ]{3,}?):/, (m, p1) => p1.split(/\s+/).map(_tc).join(' ') + ':');
  return t;
}

// Friendly, non-technical names for internal source slugs.
const SOURCE_NAMES = {
  'nfin/Nasdaq': 'Nasdaq', 'nfin_earnings_calendar': 'Nasdaq',
  'sec_edgar': 'SEC EDGAR', 'sec_edgar_fts': 'SEC EDGAR', 'sec_edgar_ipo': 'SEC EDGAR',
  'launch_library_2': 'Launch Library', 'bls_schedule_scrape': 'BLS', 'bea_schedule_scrape': 'BEA',
  'official_event_pages': 'Official site', 'eia_calendar_scrape': 'EIA',
  'google_news_ai': 'Google News', 'google_news_strategic': 'Google News',
  'google_news_geopolitical': 'Google News', 'google_news_industry': 'Google News',
};
const friendlySource = ev => SOURCE_NAMES[ev.pub_source] || ev.pub_source || SOURCE_NAMES[ev.source] || ev.source || '';
const isApiUrl = u => /\/\/api\.|\/v1\/|\.json(\?|$)/i.test(u || '');

const SETUP_GOLD = '#f5b301';

// Score → color: High-asymmetry (≥70) bold gold, Notable (≥45) gold, Low muted.
export function setupColor(score) {
  return score >= 45 ? SETUP_GOLD : colors.textMuted;
}

export function setupSummary(s) {
  const bits = [];
  if (s.short_pct != null) bits.push(`${Math.round(s.short_pct)}% short`);
  if (s.activists && s.activists.length) bits.push(s.activists.length > 1 ? 'activists' : 'activist');
  if (s.analyst_trend === 'rising') bits.push('PT↑');
  return bits.join(' · ');
}

// Compact ⚡ badge — only shown for Notable+ setups (score ≥ 45).
export function SetupBadge({ setup }) {
  if (!setup || setup.score < 45) return null;
  return (
    <View style={[styles.setupBadge, { borderColor: SETUP_GOLD }]}>
      <Text style={[styles.setupBadgeText, { color: SETUP_GOLD }]}>⚡ SETUP {setup.score}</Text>
    </View>
  );
}

function confidenceTone(confidence) {
  const c = String(confidence || '').toLowerCase();
  if (c.includes('high')) return '#34d399';
  if (c.includes('medium')) return '#fbbf24';
  if (c.includes('low')) return '#8fa3bf';
  return colors.accent;
}

// 📊 Earnings-preview decision block (shown in the day-detail only).
export function EarningsPreviewBlock({ preview }) {
  if (!preview) return null;
  const A = colors.accent;
  const confidence = preview.confidence || 'Review';
  const significance = preview.significance || preview.implied_move || '';
  const decision = preview.decision || preview.lean;
  return (
    <View style={[styles.previewBlock, { borderColor: A + '55' }]}>
      <Text style={[styles.previewHeader, { color: A }]}>
        📊 EVENT CALL{preview.ticker ? ` · ${preview.ticker}` : ''}
      </Text>
      {preview.as_of ? <Text style={styles.previewAsOf}>{preview.as_of}</Text> : null}

      <View style={styles.previewDecision}>
        <Text style={styles.previewDecisionLabel}>Recommended decision</Text>
        <Text style={styles.previewDecisionText}>{decision}</Text>
      </View>

      <View style={styles.previewStats}>
        <View style={styles.previewStat}>
          <Text style={styles.previewStatLabel}>Confidence</Text>
          <Text style={[styles.previewStatValue, { color: confidenceTone(confidence) }]}>
            {confidence}
          </Text>
        </View>
        {significance ? (
          <View style={styles.previewStat}>
            <Text style={styles.previewStatLabel}>Significance</Text>
            <Text style={styles.previewStatValue}>{significance}</Text>
          </View>
        ) : null}
      </View>

      {(preview.implied_move || preview.avg_move) ? (
        <Text style={styles.previewMove}>
          Expected move {preview.implied_move || 'not clear yet'}
          {preview.avg_move ? `  ·  usual move ${preview.avg_move}` : ''}
        </Text>
      ) : null}

      {preview.lookahead_days != null ? (
        <View style={styles.alphaRow}>
          <Text style={styles.alphaText}>
            📈 Post-earnings increase likelihood: <Text style={styles.alphaStrong}>{preview.increase_likelihood || '—'}</Text>
            {preview.pop_score != null ? ` (${preview.pop_score}/100)` : ''}
          </Text>
          <Text style={styles.alphaText}>
            ⏱ Suggested look-ahead: <Text style={styles.alphaStrong}>~{preview.lookahead_days} trading days before</Text>
          </Text>
        </View>
      ) : null}

      {(preview.bar || []).length ? (
        <>
          <Text style={styles.previewLabel}>WHAT WOULD LOOK GOOD</Text>
          {preview.bar.map((b, i) => <Text key={i} style={styles.previewBullet}>• {b}</Text>)}
        </>
      ) : null}
      {(preview.watch || []).length ? (
        <>
          <Text style={styles.previewLabel}>WHAT TO WATCH</Text>
          {preview.watch.map((w, i) => <Text key={i} style={styles.previewBullet}>• {w}</Text>)}
        </>
      ) : null}
      {preview.bull ? <Text style={styles.previewBull}>Good-case: {preview.bull}</Text> : null}
      {preview.bear ? <Text style={styles.previewBear}>Risk: {preview.bear}</Text> : null}
      {preview.contrast ? <Text style={styles.previewContrast}>{preview.contrast}</Text> : null}

      {(preview.sources || []).length ? (
        <View style={styles.setupSources}>
          {preview.sources.map((u, i) => (
            <Pressable key={i} onPress={() => Linking.openURL(u)}>
              <Text style={styles.setupSrcLink}>source {i + 1} ↗</Text>
            </Pressable>
          ))}
        </View>
      ) : null}
      <Text style={styles.previewDisc}>Decision support, not financial advice. Refresh before trading.</Text>
    </View>
  );
}

export function SourcePill({ sourceType }) {
  const bg = { api: '#0d2d1a', scraper: '#1a1040', synthetic: '#151e2a' };
  const fg = { api: colors.api, scraper: colors.scraper, synthetic: colors.synthetic };
  return (
    <View style={[styles.pill, {
      backgroundColor: bg[sourceType] || '#151e2a',
      borderColor: fg[sourceType] || colors.border,
    }]}>
      <Text style={[styles.pillText, { color: fg[sourceType] || colors.textMuted }]}>
        {sourceType}
      </Text>
    </View>
  );
}

export function EventCard({ ev, showDate = false, detail = false }) {
  const catColor = categoryColors[ev.category_id] || colors.accent;
  const imp = importanceConfig[ev.importance] || importanceConfig.low;
  const t = timeLabel(ev);
  const d = showDate ? dateLabel(ev) : null;

  return (
    <View style={styles.card}>
      <View style={[styles.catStripe, { backgroundColor: catColor }]} />
      <View style={styles.cardInner}>
        <View style={styles.cardMeta}>
          <Text style={[styles.catBadge, { color: catColor }]}>
            {categoryIcons[ev.category_id]} {categoryName(ev.category_id)}
          </Text>
          <View style={styles.metaRight}>
            <SetupBadge setup={ev.setup} />
            <View style={[styles.impPill, { backgroundColor: imp.color + '22', borderColor: imp.color }]}>
              <Text style={[styles.impText, { color: imp.color }]}>{imp.label}</Text>
            </View>
          </View>
        </View>

        {d ? <Text style={styles.cardDate}>📅 {d}</Text> : null}

        <Text style={styles.cardTitle}>{cleanTitle(ev)}</Text>

        {(ev.entity || t) ? (
          <Text style={styles.cardSub}>
            {[ev.entity, t ? `⏰ ${t} ET` : null].filter(Boolean).join('  ·  ')}
          </Text>
        ) : null}

        {!!ev.company_intro && (
          ev.company_ticker ? (
            <Pressable onPress={() => openCompany(ev.company_ticker)}>
              <Text style={styles.companyIntro} numberOfLines={detail ? 5 : 3}>
                {ev.company_intro} <Text style={styles.companyLink}>About ›</Text>
              </Text>
            </Pressable>
          ) : (
            <Text style={styles.companyIntro} numberOfLines={detail ? 4 : 3}>{ev.company_intro}</Text>
          )
        )}

        {ev.setup ? (
          <Text style={[styles.setupLine, { color: setupColor(ev.setup.score) }]} numberOfLines={1}>
            ⚡ {ev.setup.label} · {setupSummary(ev.setup)}
          </Text>
        ) : null}

        {detail && ev.setup ? (
          <View style={[styles.setupDetail, { borderColor: setupColor(ev.setup.score) + '55' }]}>
            {ev.setup.bias ? <Text style={styles.setupBias}>↕ {ev.setup.bias}</Text> : null}
            {(ev.setup.notes || []).map((n, i) => (
              <Text key={i} style={styles.setupNote}>• {n}</Text>
            ))}
            {(ev.setup.sources || []).length ? (
              <View style={styles.setupSources}>
                {ev.setup.sources.map((u, i) => (
                  <Pressable key={i} onPress={() => Linking.openURL(u)}>
                    <Text style={styles.setupSrcLink}>source {i + 1} ↗</Text>
                  </Pressable>
                ))}
              </View>
            ) : null}
          </View>
        ) : null}

        {detail && ev.preview ? <EarningsPreviewBlock preview={ev.preview} /> : null}

        {/* Show the (often technical) description only when there's no company TL;DR;
            non-company events (macro, launches) still get their description. */}
        {!!ev.description && !ev.company_intro && (
          <Text style={styles.cardDesc} numberOfLines={detail ? 4 : 2}>{ev.description}</Text>
        )}

        {/* Minimal sourcing — friendly outlet name; tap-through only for real articles. */}
        {friendlySource(ev) ? (() => {
          const linkable = ev.source_url && !isApiUrl(ev.source_url);
          return (
            <Pressable
              onPress={() => linkable && Linking.openURL(ev.source_url)}
              disabled={!linkable}
              style={styles.sourceMiniRow}>
              <Text style={styles.sourceMini}>
                {friendlySource(ev)}
                {detail && ev.pub_date ? ` · ${ev.pub_date}` : ''}
                {linkable ? '  ↗' : ''}
              </Text>
            </Pressable>
          );
        })() : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    backgroundColor: colors.surface,
    borderRadius: 12,
    marginBottom: 10,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: colors.border,
  },
  catStripe:    { width: 4 },
  cardInner:    { flex: 1, padding: 12 },
  cardMeta: {
    flexDirection: 'row', alignItems: 'center',
    justifyContent: 'space-between', marginBottom: 5,
  },
  metaRight:     { flexDirection: 'row', alignItems: 'center', gap: 6 },
  setupBadge: {
    borderWidth: 1, borderRadius: 4,
    paddingHorizontal: 6, paddingVertical: 2,
    backgroundColor: '#f5b30118',
  },
  setupBadgeText:{ fontSize: 10, fontWeight: '800', letterSpacing: 0.5 },
  setupLine:     { fontSize: 11, fontWeight: '700', marginBottom: 5 },
  setupDetail: {
    borderWidth: 1, borderRadius: 8, padding: 8, marginBottom: 8,
    backgroundColor: '#f5b3010d', gap: 3,
  },
  setupBias:     { color: '#f5b301', fontSize: 11, fontWeight: '700', marginBottom: 2 },
  setupNote:     { color: colors.textSecondary, fontSize: 11, lineHeight: 16 },
  setupSources:  { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginTop: 4 },
  setupSrcLink:  { color: colors.accent, fontSize: 10, fontWeight: '600' },

  previewBlock: {
    borderWidth: 1, borderRadius: 8, padding: 10, marginBottom: 8,
    backgroundColor: colors.accent + '0d', gap: 3,
  },
  previewHeader:  { fontSize: 11, fontWeight: '800', letterSpacing: 0.6 },
  previewAsOf:    { color: colors.textMuted, fontSize: 10, marginBottom: 3 },
  previewDecision: {
    backgroundColor: colors.surfaceRaised,
    borderRadius: 7,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 8,
    marginVertical: 3,
  },
  previewDecisionLabel: {
    color: colors.accent,
    fontSize: 10,
    fontWeight: '800',
    marginBottom: 3,
  },
  previewDecisionText: {
    color: colors.text,
    fontSize: 13,
    fontWeight: '800',
    lineHeight: 18,
  },
  previewStats: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 2,
    flexWrap: 'wrap',
  },
  previewStat: {
    flexGrow: 1,
    minWidth: 128,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 7,
    paddingHorizontal: 8,
    paddingVertical: 6,
    backgroundColor: '#080e1a55',
  },
  previewStatLabel: { color: colors.textMuted, fontSize: 9, fontWeight: '800', marginBottom: 2 },
  previewStatValue: { color: colors.text, fontSize: 12, fontWeight: '800', lineHeight: 16 },
  previewMove:    { color: colors.textSecondary, fontSize: 11, fontWeight: '600', marginBottom: 2 },
  alphaRow: {
    borderWidth: 1, borderColor: '#34d39955', borderRadius: 7,
    backgroundColor: '#34d39911', padding: 7, marginTop: 4, marginBottom: 2, gap: 2,
  },
  alphaText:   { color: colors.textSecondary, fontSize: 11, lineHeight: 16 },
  alphaStrong: { color: '#34d399', fontWeight: '800' },
  previewLabel:   { color: colors.textMuted, fontSize: 9, fontWeight: '800', letterSpacing: 1, marginTop: 5 },
  previewBullet:  { color: colors.textSecondary, fontSize: 11, lineHeight: 16 },
  previewBull:    { color: '#34d399', fontSize: 11, lineHeight: 16, marginTop: 5 },
  previewBear:    { color: '#f87171', fontSize: 11, lineHeight: 16, marginTop: 3 },
  previewContrast:{ color: colors.textMuted, fontSize: 11, lineHeight: 16, marginTop: 3, fontStyle: 'italic' },
  previewDisc:    { color: colors.textMuted, fontSize: 9, fontStyle: 'italic', marginTop: 6 },
  catBadge:      { fontSize: 11, fontWeight: '700', letterSpacing: 0.3 },
  impPill: {
    borderWidth: 1, borderRadius: 4,
    paddingHorizontal: 6, paddingVertical: 2,
  },
  impText:       { fontSize: 10, fontWeight: '800', letterSpacing: 0.8 },
  cardDate:      { color: colors.accent, fontSize: 11, fontWeight: '700', letterSpacing: 0.3, marginBottom: 4 },
  cardTitle:     { color: colors.text, fontSize: 14, fontWeight: '700', lineHeight: 20, marginBottom: 3 },
  cardSub:       { color: colors.textMuted, fontSize: 11, marginBottom: 5 },
  companyIntro: {
    color: colors.textSecondary,
    fontSize: 12,
    lineHeight: 17,
    marginBottom: 6,
    fontWeight: '600',
  },
  companyLink: { color: colors.accent, fontSize: 11, fontWeight: '700' },
  cardDesc: {
    color: colors.textSecondary, fontSize: 12, lineHeight: 18,
    marginBottom: 8, opacity: 0.9,
  },
  provenanceRow: { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', gap: 6 },
  pill: {
    borderWidth: 1, borderRadius: 5,
    paddingHorizontal: 7, paddingVertical: 2,
  },
  pillText:      { fontSize: 10, fontWeight: '700', letterSpacing: 0.5 },
  provenanceMeta:{ color: colors.textMuted, fontSize: 10, flex: 1 },
  linkBtn: {
    paddingHorizontal: 8, paddingVertical: 3,
    backgroundColor: colors.accentDim, borderRadius: 5,
  },
  linkText:      { color: colors.accent, fontSize: 10, fontWeight: '600' },
  sourceMiniRow: { marginTop: 2 },
  sourceMini:    { color: colors.textMuted, fontSize: 10, fontWeight: '600' },
});
