import React, { useState, useEffect, useMemo } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { colors, categoryColors } from './theme';
import { EventCard } from './EventCard';

const DAY_ABBREVS = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

export default function WeekView({ weekDates, eventsByDate, selectedDate, onSelectDay, today }) {
  const [activeDay, setActiveDay] = useState(() => {
    if (selectedDate && weekDates.includes(selectedDate)) return selectedDate;
    return weekDates.find(d => (eventsByDate[d] || []).length > 0) || weekDates[0];
  });

  useEffect(() => {
    if (selectedDate && weekDates.includes(selectedDate)) {
      setActiveDay(selectedDate);
    } else {
      const best = weekDates.find(d => (eventsByDate[d] || []).length > 0);
      setActiveDay(best || weekDates[0]);
    }
  }, [weekDates]);

  const activeDayEvents = useMemo(() => eventsByDate[activeDay] || [], [eventsByDate, activeDay]);

  const dayTitle = new Date(activeDay + 'T00:00:00').toLocaleDateString(undefined, {
    weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
  });

  return (
    <View style={styles.wrap}>

      {/* ── Compact week strip ────────────────────────── */}
      <View style={styles.strip}>
        {weekDates.map(date => {
          const d        = new Date(date + 'T00:00:00');
          const isToday  = date === today;
          const isActive = date === activeDay;
          const count    = (eventsByDate[date] || []).length;
          return (
            <Pressable key={date} onPress={() => setActiveDay(date)} style={styles.stripCol}>
              <Text style={[styles.abbrev, isActive && styles.abbrevActive]}>
                {DAY_ABBREVS[d.getDay()]}
              </Text>
              <View style={[
                styles.numWrap,
                isToday && !isActive && styles.numToday,
                isActive && styles.numActive,
              ]}>
                <Text style={[
                  styles.num,
                  isToday && !isActive && styles.numTodayTxt,
                  isActive && styles.numActiveTxt,
                ]}>
                  {d.getDate()}
                </Text>
              </View>
              {count > 0 && (
                <View style={[
                  styles.dot,
                  isActive  && styles.dotActive,
                  !isActive && isToday && styles.dotToday,
                ]} />
              )}
            </Pressable>
          );
        })}
      </View>

      {/* ── Day title ─────────────────────────────────── */}
      <Text style={styles.dayTitle}>{dayTitle}</Text>
      <View style={styles.sep} />

      {/* ── Event list ────────────────────────────────── */}
      {activeDayEvents.length === 0
        ? <Text style={styles.empty}>No events this day.</Text>
        : activeDayEvents.map((ev, i) => <EventCard key={i} ev={ev} />)
      }

    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { width: '100%', maxWidth: 700, alignSelf: 'center' },

  strip: {
    flexDirection: 'row',
    backgroundColor: colors.surface,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.border,
    paddingVertical: 10,
    marginBottom: 14,
  },
  stripCol:     { flex: 1, alignItems: 'center', gap: 4 },
  abbrev: {
    color: colors.textMuted, fontSize: 11,
    fontWeight: '700', letterSpacing: 1, textTransform: 'uppercase',
  },
  abbrevActive: { color: colors.accent },
  numWrap: {
    width: 32, height: 32, borderRadius: 16,
    alignItems: 'center', justifyContent: 'center',
  },
  numToday:     { backgroundColor: colors.today },
  numActive:    { backgroundColor: colors.accent },
  num:          { color: colors.text, fontSize: 16, fontWeight: '700' },
  numTodayTxt:  { color: colors.todayText, fontWeight: '800' },
  numActiveTxt: { color: '#ffffff', fontWeight: '800' },
  dot:          { width: 4, height: 4, borderRadius: 2, backgroundColor: colors.textMuted },
  dotActive:    { backgroundColor: colors.accent },
  dotToday:     { backgroundColor: colors.today },

  dayTitle: { color: colors.text, fontSize: 16, fontWeight: '700', marginBottom: 10 },
  sep:      { height: 1, backgroundColor: colors.border, marginBottom: 12 },

  empty:    { color: colors.textMuted, fontSize: 13, fontStyle: 'italic', textAlign: 'center', marginTop: 24 },
});
