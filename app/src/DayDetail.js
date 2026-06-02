import React, { useState } from 'react';
import {
  Modal, View, Text, ScrollView, Pressable, StyleSheet, Platform,
} from 'react-native';
import { colors } from './theme';
import StockImpactPanel from './StockImpact';
import { EventCard } from './EventCard';

function prettyDate(date) {
  if (!date) return '';
  return new Date(date + 'T00:00:00').toLocaleDateString(undefined, {
    weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
  });
}

// Collect all stock impacts across the day's events, deduplicated
function aggregateDayImpacts(events) {
  const seen = new Map(); // ticker → best impact
  for (const ev of events) {
    const rankConf = { high: 0, medium: 1, low: 2 };
    for (const imp of ev.stock_impacts || []) {
      const existing = seen.get(imp.ticker);
      if (!existing || (rankConf[imp.confidence] ?? 2) < (rankConf[existing.confidence] ?? 2)) {
        seen.set(imp.ticker, imp);
      }
    }
  }
  return Array.from(seen.values());
}

export default function DayDetail({ visible, date, events, onClose }) {
  const [tab, setTab] = useState('events');
  const dayImpacts = aggregateDayImpacts(events);

  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
      <View style={styles.backdrop}>
        <View style={styles.sheet}>
          {/* Header */}
          <View style={styles.header}>
            <View style={{ flex: 1 }}>
              <Text style={styles.dateLabel}>{prettyDate(date)}</Text>
              <Text style={styles.dateSubLabel}>
                {events.length} event{events.length !== 1 ? 's' : ''}
                {dayImpacts.length > 0 ? `  ·  ${dayImpacts.length} stock signals` : ''}
              </Text>
            </View>
            <Pressable onPress={onClose} style={styles.closeBtn}>
              <Text style={styles.closeIcon}>✕</Text>
            </Pressable>
          </View>

          {/* Tabs */}
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

          {/* Content */}
          <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent}
            showsVerticalScrollIndicator={false}>
            {tab === 'events' ? (
              events.length === 0
                ? <Text style={styles.emptyMsg}>No collected events for this day.</Text>
                : events.map((ev, i) => <EventCard key={i} ev={ev} />)
            ) : (
              <StockImpactPanel impacts={dayImpacts} />
            )}
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'flex-end',
  },
  sheet: {
    backgroundColor: colors.bg,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    borderTopWidth: 1,
    borderColor: colors.borderAccent,
    maxHeight: '88%',
    paddingTop: 4,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingHorizontal: 20,
    paddingTop: 18,
    paddingBottom: 12,
  },
  dateLabel:    { color: colors.text, fontSize: 20, fontWeight: '800' },
  dateSubLabel: { color: colors.textMuted, fontSize: 12, marginTop: 3 },
  closeBtn: {
    width: 32, height: 32, borderRadius: 16,
    backgroundColor: colors.surfaceRaised,
    borderWidth: 1, borderColor: colors.border,
    alignItems: 'center', justifyContent: 'center',
  },
  closeIcon:    { color: colors.textSecondary, fontSize: 14, fontWeight: '600' },

  // Tabs
  tabBar: {
    flexDirection: 'row',
    marginHorizontal: 20,
    marginBottom: 12,
    backgroundColor: colors.surface,
    borderRadius: 10,
    padding: 3,
    borderWidth: 1,
    borderColor: colors.border,
  },
  tab: {
    flex: 1, paddingVertical: 8, borderRadius: 8, alignItems: 'center',
  },
  tabActive:    { backgroundColor: colors.accentDim },
  tabText:      { color: colors.textMuted, fontSize: 13, fontWeight: '600' },
  tabTextActive:{ color: colors.accent, fontWeight: '700' },

  scroll:        { paddingHorizontal: 20 },
  scrollContent: { paddingBottom: 40 },
  emptyMsg:      { color: colors.textMuted, textAlign: 'center', marginTop: 40 },

});
