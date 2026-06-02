import React, { useState } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { colors } from './theme';
import { EventCard } from './EventCard';
import StockImpactPanel from './StockImpact';

function aggregateDayImpacts(events) {
  const seen = new Map();
  const rankConf = { high: 0, medium: 1, low: 2 };
  for (const ev of events) {
    for (const imp of ev.stock_impacts || []) {
      const existing = seen.get(imp.ticker);
      if (!existing || (rankConf[imp.confidence] ?? 2) < (rankConf[existing.confidence] ?? 2)) {
        seen.set(imp.ticker, imp);
      }
    }
  }
  return Array.from(seen.values());
}

export default function DayView({ date, events }) {
  const [tab, setTab] = useState('events');
  const dayImpacts = aggregateDayImpacts(events);

  const prettyDate = date
    ? new Date(date + 'T00:00:00').toLocaleDateString(undefined, {
        weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
      })
    : '';

  return (
    <View style={styles.wrap}>
      <View style={styles.header}>
        <Text style={styles.dateLabel}>{prettyDate}</Text>
        <Text style={styles.dateSub}>
          {events.length} event{events.length !== 1 ? 's' : ''}
          {dayImpacts.length > 0 ? `  ·  ${dayImpacts.length} stock signals` : ''}
        </Text>
      </View>

      <View style={styles.tabBar}>
        {[
          { key: 'events', label: `Events (${events.length})` },
          { key: 'stocks', label: `Stocks (${dayImpacts.length})` },
        ].map(({ key, label }) => (
          <Pressable key={key} onPress={() => setTab(key)}
            style={[styles.tab, tab === key && styles.tabActive]}>
            <Text style={[styles.tabText, tab === key && styles.tabTextActive]}>{label}</Text>
          </Pressable>
        ))}
      </View>

      {tab === 'events' ? (
        events.length === 0
          ? <Text style={styles.empty}>No events for this day.</Text>
          : events.map((ev, i) => <EventCard key={i} ev={ev} />)
      ) : (
        <StockImpactPanel impacts={dayImpacts} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { width: '100%', maxWidth: 700, alignSelf: 'center' },

  header:    { marginBottom: 14 },
  dateLabel: { color: colors.text, fontSize: 20, fontWeight: '800' },
  dateSub:   { color: colors.textMuted, fontSize: 12, marginTop: 3 },

  tabBar: {
    flexDirection: 'row',
    marginBottom: 14,
    backgroundColor: colors.surface,
    borderRadius: 10,
    padding: 3,
    borderWidth: 1,
    borderColor: colors.border,
  },
  tab:          { flex: 1, paddingVertical: 8, borderRadius: 8, alignItems: 'center' },
  tabActive:    { backgroundColor: colors.accentDim },
  tabText:      { color: colors.textMuted, fontSize: 13, fontWeight: '600' },
  tabTextActive:{ color: colors.accent, fontWeight: '700' },

  empty: { color: colors.textMuted, textAlign: 'center', marginTop: 40 },
});
