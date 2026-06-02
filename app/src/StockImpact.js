// Stock impact cards for the day-detail panel.
import React from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { colors, directionConfig, confidenceColor } from './theme';

function TickerBadge({ ticker, direction }) {
  const dcfg = directionConfig[String(direction)] || directionConfig[0];
  return (
    <View style={[styles.badge, { borderColor: dcfg.color }]}>
      <Text style={[styles.badgeSym, { color: dcfg.color }]}>{dcfg.symbol} </Text>
      <Text style={[styles.badgeTicker, { color: dcfg.color }]}>{ticker}</Text>
    </View>
  );
}

function ImpactCard({ impact }) {
  const dcfg = directionConfig[String(impact.direction)] || directionConfig[0];
  const confColor = confidenceColor[impact.confidence] || colors.textMuted;
  return (
    <View style={styles.card}>
      <View style={[styles.dirStripe, { backgroundColor: dcfg.color }]} />
      <View style={styles.cardBody}>
        <View style={styles.cardHeader}>
          <TickerBadge ticker={impact.ticker} direction={impact.direction} />
          {impact.sector ? (
            <Text style={styles.sector}>{impact.sector.replace(/_/g, ' ')}</Text>
          ) : null}
          <View style={[styles.confPill, { borderColor: confColor }]}>
            <Text style={[styles.confText, { color: confColor }]}>
              {impact.confidence.toUpperCase()}
            </Text>
          </View>
        </View>
        <Text style={styles.reason}>{impact.reason}</Text>
      </View>
    </View>
  );
}

export default function StockImpactPanel({ impacts }) {
  if (!impacts || impacts.length === 0) {
    return (
      <View style={styles.empty}>
        <Text style={styles.emptyText}>No stock-impact signals for this event.</Text>
      </View>
    );
  }

  // Group: high → medium → low confidence
  const sorted = [...impacts].sort((a, b) => {
    const rankConf = { high: 0, medium: 1, low: 2 };
    return (rankConf[a.confidence] ?? 2) - (rankConf[b.confidence] ?? 2);
  });

  // De-duplicate by ticker (keep highest-confidence entry)
  const seen = new Set();
  const deduped = sorted.filter(imp => {
    if (seen.has(imp.ticker)) return false;
    seen.add(imp.ticker);
    return true;
  });

  return (
    <View style={styles.wrap}>
      <Text style={styles.sectionLabel}>LIKELY IMPACTED STOCKS</Text>
      {deduped.map((imp, i) => <ImpactCard key={i} impact={imp} />)}
      <Text style={styles.disclaimer}>
        Rules-based analysis — not financial advice. Verify before acting.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap:         { paddingBottom: 12 },
  sectionLabel: {
    color: colors.textMuted, fontSize: 10, fontWeight: '800',
    letterSpacing: 1.2, marginBottom: 10, marginTop: 4,
  },
  card: {
    flexDirection: 'row', backgroundColor: colors.surface,
    borderRadius: 10, marginBottom: 8, overflow: 'hidden',
    borderWidth: 1, borderColor: colors.border,
  },
  dirStripe: { width: 4 },
  cardBody:  { flex: 1, padding: 10 },
  cardHeader:{ flexDirection: 'row', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 5 },
  badge: {
    flexDirection: 'row', alignItems: 'center',
    borderWidth: 1, borderRadius: 6,
    paddingHorizontal: 8, paddingVertical: 3,
  },
  badgeSym:    { fontSize: 12, fontWeight: '700' },
  badgeTicker: { fontSize: 13, fontWeight: '800', letterSpacing: 0.5 },
  sector:      { color: colors.textMuted, fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5 },
  confPill: {
    borderWidth: 1, borderRadius: 4,
    paddingHorizontal: 6, paddingVertical: 2, marginLeft: 'auto',
  },
  confText:    { fontSize: 10, fontWeight: '700', letterSpacing: 0.8 },
  reason:      { color: colors.textSecondary, fontSize: 12, lineHeight: 17 },
  empty:       { paddingVertical: 16, alignItems: 'center' },
  emptyText:   { color: colors.textMuted, fontSize: 13 },
  disclaimer:  {
    color: colors.textMuted, fontSize: 10, textAlign: 'center',
    marginTop: 8, fontStyle: 'italic',
  },
});
