import React, { useMemo } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { colors } from './theme';
import { EventCard } from './EventCard';
import { LAST_COLLECTED } from './data';

function collectedDate(ev) {
  return String(ev.collected_at || '').slice(0, 10);
}

function relLabel(dateStr, today) {
  if (!dateStr) return 'Earlier';
  if (dateStr === today) return 'Just added today';
  const d = new Date(dateStr + 'T00:00:00');
  const diff = Math.round((new Date(today + 'T00:00:00') - d) / 86400000);
  if (diff === 1) return 'Added yesterday';
  if (diff > 1 && diff <= 7) return `Added ${diff} days ago`;
  return new Date(dateStr + 'T00:00:00').toLocaleDateString(undefined, {
    month: 'long', day: 'numeric', year: 'numeric',
  });
}

export default function LatestView({ events, onSelectDay, today }) {
  // Group consecutively by collected date (already sorted newest-first by caller).
  const groups = useMemo(() => {
    const out = [];
    let cur = null;
    for (const ev of events) {
      const d = collectedDate(ev);
      if (!cur || cur.date !== d) {
        cur = { date: d, items: [] };
        out.push(cur);
      }
      cur.items.push(ev);
    }
    return out;
  }, [events]);

  const newestDate = LAST_COLLECTED;
  const newestCount = groups.length && groups[0].date === newestDate ? groups[0].items.length : 0;

  return (
    <View style={styles.wrap}>
      <View style={styles.banner}>
        <Text style={styles.bannerTitle}>Latest identified events</Text>
        <Text style={styles.bannerSub}>
          {newestCount > 0
            ? `${newestCount} event${newestCount !== 1 ? 's' : ''} from the most recent collection · newest first`
            : 'Most recently collected first'}
        </Text>
      </View>

      {events.length === 0 ? (
        <Text style={styles.empty}>No events match the current filters.</Text>
      ) : (
        groups.map((g, gi) => {
          const isNewest = gi === 0 && g.date === newestDate;
          return (
            <View key={g.date || `g${gi}`} style={styles.group}>
              <View style={styles.groupHeaderRow}>
                <Text style={[styles.groupHeader, isNewest && styles.groupHeaderNew]}>
                  {relLabel(g.date, today)}
                </Text>
                {isNewest && (
                  <View style={styles.newBadge}>
                    <Text style={styles.newBadgeTxt}>NEW</Text>
                  </View>
                )}
                <Text style={styles.groupCount}>{g.items.length}</Text>
              </View>
              {g.items.map((ev, i) => (
                <Pressable key={i} onPress={() => onSelectDay(ev.event_date)}>
                  <EventCard ev={ev} showDate />
                </Pressable>
              ))}
            </View>
          );
        })
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { width: '100%', maxWidth: 700, alignSelf: 'center' },

  banner: {
    backgroundColor: colors.surface,
    borderRadius: 12, borderWidth: 1, borderColor: colors.border,
    padding: 14, marginBottom: 14,
  },
  bannerTitle: { color: colors.text, fontSize: 16, fontWeight: '800' },
  bannerSub:   { color: colors.textMuted, fontSize: 12, marginTop: 3 },

  empty: { color: colors.textMuted, fontSize: 13, textAlign: 'center', marginTop: 30 },

  group: { marginBottom: 8 },
  groupHeaderRow: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    marginTop: 6, marginBottom: 8,
  },
  groupHeader:    { color: colors.textSecondary, fontSize: 12, fontWeight: '700', letterSpacing: 0.5 },
  groupHeaderNew: { color: colors.accent },
  newBadge: {
    backgroundColor: colors.accent, borderRadius: 4,
    paddingHorizontal: 6, paddingVertical: 1,
  },
  newBadgeTxt: { color: '#fff', fontSize: 9, fontWeight: '800', letterSpacing: 1 },
  groupCount: {
    marginLeft: 'auto', color: colors.textMuted, fontSize: 11, fontWeight: '700',
  },
});
