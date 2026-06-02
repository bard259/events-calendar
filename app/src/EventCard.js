import React from 'react';
import { View, Text, Pressable, StyleSheet, Linking } from 'react-native';
import { colors, categoryColors, categoryIcons, importanceConfig } from './theme';
import { categoryName } from './data';

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

// 📊 Earnings-preview deep-dive block (shown in the day-detail only).
export function EarningsPreviewBlock({ preview }) {
  if (!preview) return null;
  const A = colors.accent;
  return (
    <View style={[styles.previewBlock, { borderColor: A + '55' }]}>
      <Text style={[styles.previewHeader, { color: A }]}>
        📊 EARNINGS PREVIEW{preview.ticker ? ` · ${preview.ticker}` : ''}
      </Text>
      {preview.as_of ? <Text style={styles.previewAsOf}>{preview.as_of}</Text> : null}
      {preview.lean ? <Text style={styles.previewLean}>{preview.lean}</Text> : null}
      {(preview.implied_move || preview.avg_move) ? (
        <Text style={styles.previewMove}>
          Implied move {preview.implied_move || '—'}
          {preview.avg_move ? `  ·  avg ${preview.avg_move}` : ''}
        </Text>
      ) : null}

      {(preview.bar || []).length ? (
        <>
          <Text style={styles.previewLabel}>THE BAR</Text>
          {preview.bar.map((b, i) => <Text key={i} style={styles.previewBullet}>• {b}</Text>)}
        </>
      ) : null}
      {(preview.watch || []).length ? (
        <>
          <Text style={styles.previewLabel}>WATCH</Text>
          {preview.watch.map((w, i) => <Text key={i} style={styles.previewBullet}>• {w}</Text>)}
        </>
      ) : null}
      {preview.bull ? <Text style={styles.previewBull}>▲ Bull: {preview.bull}</Text> : null}
      {preview.bear ? <Text style={styles.previewBear}>▼ Bear: {preview.bear}</Text> : null}
      {preview.contrast ? <Text style={styles.previewContrast}>⇄ {preview.contrast}</Text> : null}

      {(preview.sources || []).length ? (
        <View style={styles.setupSources}>
          {preview.sources.map((u, i) => (
            <Pressable key={i} onPress={() => Linking.openURL(u)}>
              <Text style={styles.setupSrcLink}>source {i + 1} ↗</Text>
            </Pressable>
          ))}
        </View>
      ) : null}
      <Text style={styles.previewDisc}>Research, not financial advice — refresh before the print.</Text>
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

        <Text style={styles.cardTitle}>{ev.title}</Text>

        {(ev.entity || t) ? (
          <Text style={styles.cardSub}>
            {[ev.entity, t ? `⏰ ${t} ET` : null].filter(Boolean).join('  ·  ')}
          </Text>
        ) : null}

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

        {!!ev.description && (
          <Text style={styles.cardDesc} numberOfLines={3}>{ev.description}</Text>
        )}

        <View style={styles.provenanceRow}>
          <SourcePill sourceType={ev.source_type} />
          <Text style={styles.provenanceMeta}>
            {ev.pub_source ? `via ${ev.pub_source}` : ev.source}
            {ev.pub_date ? `  ·  published ${ev.pub_date}` : ''}
          </Text>
          {!!ev.source_url && (
            <Pressable onPress={() => Linking.openURL(ev.source_url)} style={styles.linkBtn}>
              <Text style={styles.linkText}>source ↗</Text>
            </Pressable>
          )}
        </View>
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
  previewLean:    { color: colors.text, fontSize: 12, fontWeight: '700', lineHeight: 17, marginBottom: 2 },
  previewMove:    { color: colors.textSecondary, fontSize: 11, fontWeight: '600', marginBottom: 2 },
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
});
