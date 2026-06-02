import React, { useMemo } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { colors, categoryColors } from './theme';

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

function pad(n) { return String(n).padStart(2, '0'); }

export default function Calendar({ year, month0, eventsByDate, selectedDate, onSelectDay, today }) {
  const cells = useMemo(() => {
    const firstDow = new Date(year, month0, 1).getDay();
    const daysInMonth = new Date(year, month0 + 1, 0).getDate();
    const out = [];
    for (let i = 0; i < firstDow; i++) out.push(null);
    for (let d = 1; d <= daysInMonth; d++)
      out.push(`${year}-${pad(month0 + 1)}-${pad(d)}`);
    while (out.length % 7 !== 0) out.push(null);
    return out;
  }, [year, month0]);

  return (
    <View style={styles.wrap}>
      {/* Weekday headers */}
      <View style={styles.weekRow}>
        {WEEKDAYS.map((w) => (
          <Text key={w} style={styles.weekday}>{w}</Text>
        ))}
      </View>

      {/* Divider */}
      <View style={styles.divider} />

      {/* Grid */}
      <View style={styles.grid}>
        {cells.map((date, i) => {
          if (!date) return <View key={`e${i}`} style={styles.cellEmpty} />;
          const dayEvents = eventsByDate[date] || [];
          const cats = [...new Set(dayEvents.map((e) => e.category_id))].slice(0, 5);
          const highCount = dayEvents.filter(e => e.importance === 'high').length;
          const isSelected = date === selectedDate;
          const isToday = date === today;
          const dayNum = Number(date.slice(-2));
          const isWeekend = [0, 6].includes(new Date(date + 'T00:00:00').getDay());

          return (
            <Pressable
              key={date}
              onPress={() => onSelectDay(date)}
              style={({ pressed, hovered }) => [
                styles.cell,
                isWeekend && styles.cellWeekend,
                isSelected && styles.cellSelected,
                (pressed || hovered) && !isSelected && styles.cellHover,
              ]}
            >
              {/* High-importance indicator line */}
              {highCount > 0 && <View style={styles.urgentBar} />}

              {/* Day number */}
              <View style={styles.dayRow}>
                <View style={[styles.dayNumWrap, isToday && styles.dayNumToday]}>
                  <Text style={[styles.dayNum, isToday && styles.dayNumTodayText]}>
                    {dayNum}
                  </Text>
                </View>
                {dayEvents.length > 0 && (
                  <Text style={styles.eventCount}>{dayEvents.length}</Text>
                )}
              </View>

              {/* Category dots */}
              <View style={styles.dots}>
                {cats.map((c) => (
                  <View key={c} style={[styles.dot, { backgroundColor: categoryColors[c] }]} />
                ))}
              </View>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const CELL_BORDER = `${colors.border}`;

const styles = StyleSheet.create({
  wrap:        { width: '100%', maxWidth: 700, alignSelf: 'center' },
  weekRow:     { flexDirection: 'row', paddingVertical: 8 },
  weekday: {
    flex: 1, textAlign: 'center',
    color: colors.textMuted, fontSize: 11, fontWeight: '700',
    letterSpacing: 1, textTransform: 'uppercase',
  },
  divider: { height: 1, backgroundColor: colors.border, marginBottom: 2 },
  grid:    { flexDirection: 'row', flexWrap: 'wrap' },

  cell: {
    width: `${100 / 7}%`,
    aspectRatio: 0.9,
    padding: 7,
    borderWidth: 0.5,
    borderColor: colors.border,
    backgroundColor: colors.surface,
    position: 'relative',
    overflow: 'hidden',
  },
  cellEmpty:   { width: `${100 / 7}%`, aspectRatio: 0.9, backgroundColor: colors.bg },
  cellWeekend: { backgroundColor: '#0a1220' },
  cellSelected: {
    backgroundColor: colors.surfaceRaised,
    borderColor: colors.accent,
    borderWidth: 1.5,
  },
  cellHover:   { backgroundColor: colors.surfaceHover },

  urgentBar: {
    position: 'absolute', top: 0, left: 0, right: 0,
    height: 2, backgroundColor: '#f87171',
  },

  dayRow:      { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  dayNumWrap:  { width: 22, height: 22, borderRadius: 11, alignItems: 'center', justifyContent: 'center' },
  dayNumToday: { backgroundColor: colors.today },
  dayNum:      { color: colors.text, fontSize: 13, fontWeight: '600' },
  dayNumTodayText: { color: colors.todayText, fontWeight: '800' },
  eventCount:  { color: colors.textMuted, fontSize: 10, fontWeight: '700' },

  dots:        { flexDirection: 'row', flexWrap: 'wrap', gap: 3, marginTop: 'auto', paddingTop: 4 },
  dot:         { width: 6, height: 6, borderRadius: 3 },
});
