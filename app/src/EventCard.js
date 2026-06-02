import React from 'react';
import { View, Text, Pressable, StyleSheet, Linking } from 'react-native';
import { colors, categoryColors, categoryIcons, importanceConfig } from './theme';
import { categoryName } from './data';

function timeLabel(ev) {
  if (!ev.event_datetime) return null;
  const d = new Date(ev.event_datetime);
  return isNaN(d) ? null : d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
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

export function EventCard({ ev }) {
  const catColor = categoryColors[ev.category_id] || colors.accent;
  const imp = importanceConfig[ev.importance] || importanceConfig.low;
  const t = timeLabel(ev);

  return (
    <View style={styles.card}>
      <View style={[styles.catStripe, { backgroundColor: catColor }]} />
      <View style={styles.cardInner}>
        <View style={styles.cardMeta}>
          <Text style={[styles.catBadge, { color: catColor }]}>
            {categoryIcons[ev.category_id]} {categoryName(ev.category_id)}
          </Text>
          <View style={[styles.impPill, { backgroundColor: imp.color + '22', borderColor: imp.color }]}>
            <Text style={[styles.impText, { color: imp.color }]}>{imp.label}</Text>
          </View>
        </View>

        <Text style={styles.cardTitle}>{ev.title}</Text>

        {(ev.entity || t) ? (
          <Text style={styles.cardSub}>
            {[ev.entity, t ? `⏰ ${t} ET` : null].filter(Boolean).join('  ·  ')}
          </Text>
        ) : null}

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
  catBadge:      { fontSize: 11, fontWeight: '700', letterSpacing: 0.3 },
  impPill: {
    borderWidth: 1, borderRadius: 4,
    paddingHorizontal: 6, paddingVertical: 2,
  },
  impText:       { fontSize: 10, fontWeight: '800', letterSpacing: 0.8 },
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
