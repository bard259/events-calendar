import React, { useMemo, useState, useEffect } from 'react';
import {
  SafeAreaView, View, Text, ScrollView, Pressable,
  StyleSheet, Platform,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import Calendar from './src/Calendar';
import WeekView from './src/WeekView';
import DayView from './src/DayView';
import LatestView from './src/LatestView';
import ReportsView from './src/ReportsView';
import DayDetail from './src/DayDetail';
import SearchModal from './src/SearchModal';
import CompanyModal from './src/CompanyModal';
import { registerCompanyOpener } from './src/companyStore';
import { colors, categoryColors, categoryIcons } from './src/theme';
import {
  ALL_EVENTS, CATEGORIES, MONTHS, RANGE_START, RANGE_END,
  AGENT_REPORTS, groupByDate, parseMonth,
} from './src/data';

const TODAY = new Date().toISOString().slice(0, 10);

// Range label e.g. "Jun – Dec 2026"
function monthName(ym, opts = { month: 'short' }) {
  return new Date(ym + '-01T00:00:00').toLocaleDateString(undefined, opts);
}
const RANGE_LABEL = MONTHS.length > 1
  ? `${monthName(MONTHS[0])} – ${monthName(MONTHS[MONTHS.length - 1])} ${MONTHS[MONTHS.length - 1].slice(0, 4)}`
  : monthName(MONTHS[0], { month: 'long', year: 'numeric' });

// Initial cursor: today if in range, else first event.
const CLAMP_DATE = d => (d < RANGE_START ? RANGE_START : d > RANGE_END ? RANGE_END : d);
const INIT_DATE  = TODAY >= RANGE_START && TODAY <= RANGE_END ? TODAY : RANGE_START;
const INIT_MONTH = MONTHS.includes(INIT_DATE.slice(0, 7)) ? INIT_DATE.slice(0, 7) : MONTHS[0];

function addDays(dateStr, n) {
  const d = new Date(dateStr + 'T00:00:00');
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}
function getWeekDates(dateStr) {
  const d = new Date(dateStr + 'T00:00:00');
  const sun = new Date(d);
  sun.setDate(d.getDate() - d.getDay());
  return Array.from({ length: 7 }, (_, i) => {
    const day = new Date(sun);
    day.setDate(sun.getDate() + i);
    return day.toISOString().slice(0, 10);
  });
}
const fmtShort = s => new Date(s + 'T00:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
function weekLabel(dateStr) {
  const w = getWeekDates(dateStr);
  return `${fmtShort(w[0])} – ${fmtShort(w[6])}`;
}
function dayLabel(dateStr) {
  return new Date(dateStr + 'T00:00:00').toLocaleDateString(undefined, {
    weekday: 'short', month: 'short', day: 'numeric',
  });
}

const VIEW_MODES  = ['month', 'week', 'day', 'latest', 'reports'];
const VIEW_LABELS = { month: 'Month', week: 'Week', day: 'Day', latest: 'Latest', reports: 'Reports' };

export default function App() {
  const [activeCats, setActiveCats]     = useState(() => new Set(CATEGORIES.map(c => c.id)));
  const [selectedDate, setSelectedDate] = useState(null);
  const [detailOpen, setDetailOpen]     = useState(false);
  const [searchOpen, setSearchOpen]     = useState(false);
  const [viewMode, setViewMode]         = useState('month');
  const [monthCursor, setMonthCursor]   = useState(INIT_MONTH); // "YYYY-MM"
  const [cursorDate, setCursorDate]     = useState(INIT_DATE);  // "YYYY-MM-DD"
  const [companyTicker, setCompanyTicker] = useState(null);

  // Let any EventCard open the company modal without prop-drilling.
  useEffect(() => registerCompanyOpener(setCompanyTicker), []);

  const filtered     = useMemo(() => ALL_EVENTS.filter(e => activeCats.has(e.category_id)), [activeCats]);
  const eventsByDate = useMemo(() => groupByDate(filtered), [filtered]);
  const highCount    = useMemo(() => ALL_EVENTS.filter(e => e.importance === 'high').length, []);
  const weekDates    = useMemo(() => getWeekDates(cursorDate), [cursorDate]);
  const dayEvents    = useMemo(() => eventsByDate[cursorDate] || [], [eventsByDate, cursorDate]);
  const latestList   = useMemo(() => [...filtered].sort(
    (a, b) => String(b.collected_at || '').localeCompare(String(a.collected_at || ''))), [filtered]);

  const { year, month0 } = parseMonth(monthCursor);
  const monthIdx = MONTHS.indexOf(monthCursor);
  const allTypesSelected = activeCats.size === CATEGORIES.length;

  function showAllTypes() {
    setActiveCats(new Set(CATEGORIES.map(c => c.id)));
  }

  // Single-select: tap a type to view ONLY that event type; tap it again (or "All") to reset.
  function selectOnlyCat(id) {
    setActiveCats(prev => (prev.size === 1 && prev.has(id))
      ? new Set(CATEGORIES.map(c => c.id))
      : new Set([id]));
  }

  function openDay(date) {
    setSelectedDate(date);
    setDetailOpen(true);
  }

  function navigate(dir) {
    if (viewMode === 'month') {
      const next = monthIdx + dir;
      if (next >= 0 && next < MONTHS.length) setMonthCursor(MONTHS[next]);
    } else {
      const step = viewMode === 'day' ? 1 : 7;
      setCursorDate(prev => CLAMP_DATE(addDays(prev, dir * step)));
    }
  }

  function switchView(mode) {
    setViewMode(mode);
    if (mode === 'week' || mode === 'day') setCursorDate(CLAMP_DATE(selectedDate || cursorDate));
  }

  function pickSearchResult(ev) {
    setSearchOpen(false);
    const ym = ev.event_date.slice(0, 7);
    if (MONTHS.includes(ym)) setMonthCursor(ym);
    setCursorDate(CLAMP_DATE(ev.event_date));
    openDay(ev.event_date);
  }

  // Navigation disabled flags
  const canPrev = viewMode === 'month' ? monthIdx > 0                 : cursorDate > RANGE_START;
  const canNext = viewMode === 'month' ? monthIdx < MONTHS.length - 1 : cursorDate < RANGE_END;

  const navLabel = viewMode === 'month' ? monthName(monthCursor, { month: 'long', year: 'numeric' })
                 : viewMode === 'week'  ? weekLabel(cursorDate)
                 : dayLabel(cursorDate);

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar style="light" />
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>

        {/* ── Header ─────────────────────────────────── */}
        <View style={styles.header}>
          <View style={{ flex: 1 }}>
            <Text style={styles.eyebrow}>MARKET INTELLIGENCE</Text>
            <Text style={styles.h1}>{RANGE_LABEL}</Text>
          </View>
          <Pressable onPress={() => setSearchOpen(true)} style={styles.searchBtn}>
            <Text style={styles.searchBtnIcon}>🔍</Text>
          </Pressable>
          <View style={styles.statsRow}>
            <View style={styles.statPill}>
              <Text style={styles.statNum}>{ALL_EVENTS.length}</Text>
              <Text style={styles.statLabel}>EVENTS</Text>
            </View>
            <View style={[styles.statPill, { borderColor: '#f87171' }]}>
              <Text style={[styles.statNum, { color: '#f87171' }]}>{highCount}</Text>
              <Text style={styles.statLabel}>HIGH</Text>
            </View>
          </View>
        </View>

        {/* ── Event type selector ──────────────────────── */}
        {viewMode !== 'reports' && (
          <>
            <View style={styles.filterHeader}>
              <Text style={styles.filterLabel}>Event type</Text>
              <Text style={styles.filterCount}>
                {allTypesSelected ? `${filtered.length} shown` : `Only: ${filtered.length} shown · tap again for all`}
              </Text>
            </View>
            <ScrollView horizontal showsHorizontalScrollIndicator={false}
              style={styles.chipsScroll} contentContainerStyle={styles.chipsContent}>
              <Pressable onPress={showAllTypes}
                style={[
                  styles.chip,
                  allTypesSelected
                    ? { borderColor: colors.accent, backgroundColor: colors.accent + '18' }
                    : { borderColor: colors.border, backgroundColor: 'transparent' },
                ]}>
                <Text style={styles.chipIcon}>•</Text>
                <Text style={[styles.chipText, { color: allTypesSelected ? colors.accent : colors.textMuted }]}>
                  All
                </Text>
              </Pressable>
              {CATEGORIES.map(c => {
                const on  = activeCats.has(c.id);
                const solo = activeCats.size === 1 && on;
                const col = categoryColors[c.id];
                return (
                  <Pressable key={c.id} onPress={() => selectOnlyCat(c.id)}
                    style={[
                      styles.chip,
                      on ? { borderColor: col, backgroundColor: col + (solo ? '30' : '18') }
                         : { borderColor: colors.border, backgroundColor: 'transparent' },
                    ]}>
                    <Text style={styles.chipIcon}>{categoryIcons[c.id]}</Text>
                    <Text style={[styles.chipText, { color: on ? col : colors.textMuted }]} numberOfLines={1}>
                      {c.name}
                    </Text>
                  </Pressable>
                );
              })}
            </ScrollView>
          </>
        )}

        <View style={styles.divider} />

        {/* ── View mode switcher ──────────────────────── */}
        <View style={styles.switcherWrap}>
          <View style={styles.switcher}>
            {VIEW_MODES.map(mode => (
              <Pressable key={mode} onPress={() => switchView(mode)}
                style={[styles.switchTab, viewMode === mode && styles.switchTabActive]}>
                <Text style={[styles.switchText, viewMode === mode && styles.switchTextActive]}>
                  {VIEW_LABELS[mode]}
                </Text>
              </Pressable>
            ))}
          </View>
        </View>

        {/* ── Period navigation (calendar views only) ─── */}
        {viewMode !== 'latest' && viewMode !== 'reports' && (
          <View style={styles.navRow}>
            <Pressable onPress={() => navigate(-1)} disabled={!canPrev}
              style={[styles.navBtn, !canPrev && styles.navBtnDisabled]}>
              <Text style={[styles.navArrow, !canPrev && styles.navArrowDisabled]}>‹</Text>
            </Pressable>
            <Text style={styles.navLabel}>{navLabel}</Text>
            <Pressable onPress={() => navigate(1)} disabled={!canNext}
              style={[styles.navBtn, !canNext && styles.navBtnDisabled]}>
              <Text style={[styles.navArrow, !canNext && styles.navArrowDisabled]}>›</Text>
            </Pressable>
          </View>
        )}

        {/* ── Main content ────────────────────────────── */}
        {viewMode === 'month' && (
          <Calendar
            year={year} month0={month0}
            eventsByDate={eventsByDate}
            selectedDate={selectedDate}
            onSelectDay={openDay}
            today={TODAY}
          />
        )}
        {viewMode === 'week' && (
          <WeekView
            weekDates={weekDates}
            eventsByDate={eventsByDate}
            selectedDate={selectedDate}
            onSelectDay={openDay}
            today={TODAY}
          />
        )}
        {viewMode === 'day' && (
          <DayView date={cursorDate} events={dayEvents} />
        )}
        {viewMode === 'latest' && (
          <LatestView events={latestList} onSelectDay={openDay} today={TODAY} />
        )}
        {viewMode === 'reports' && (
          <ReportsView data={AGENT_REPORTS} />
        )}

        {/* ── Legend (month only) ─────────────────────── */}
        {viewMode === 'month' && (
          <View style={styles.legend}>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: '#f87171' }]} />
              <Text style={styles.legendText}>High importance</Text>
            </View>
            <View style={styles.legendItem}>
              <View style={styles.legendUrgent} />
              <Text style={styles.legendText}>Red top bar = high-priority day</Text>
            </View>
            <Text style={styles.hint}>Tap any day → Events & Stock signals</Text>
          </View>
        )}

      </ScrollView>

      <DayDetail
        visible={detailOpen}
        date={selectedDate}
        events={selectedDate ? eventsByDate[selectedDate] || [] : []}
        onClose={() => setDetailOpen(false)}
      />

      <SearchModal
        visible={searchOpen}
        onClose={() => setSearchOpen(false)}
        onPick={pickSearchResult}
      />

      <CompanyModal ticker={companyTicker} onClose={() => setCompanyTicker(null)} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe:   { flex: 1, backgroundColor: colors.bg },
  scroll: { padding: 16, paddingTop: Platform.OS === 'web' ? 32 : 12 },

  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end',
    maxWidth: 700, alignSelf: 'center', width: '100%', marginBottom: 18, gap: 10,
  },
  eyebrow: { color: colors.accent, fontSize: 10, fontWeight: '800', letterSpacing: 2, marginBottom: 4 },
  h1:      { color: colors.text, fontSize: 26, fontWeight: '800' },
  searchBtn: {
    width: 40, height: 40, borderRadius: 10,
    backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border,
    alignItems: 'center', justifyContent: 'center',
  },
  searchBtnIcon: { fontSize: 16 },
  statsRow:{ flexDirection: 'row', gap: 8 },
  statPill: {
    alignItems: 'center', paddingHorizontal: 12, paddingVertical: 6,
    backgroundColor: colors.surface, borderRadius: 8,
    borderWidth: 1, borderColor: colors.border,
  },
  statNum:   { color: colors.text, fontSize: 18, fontWeight: '800', lineHeight: 22 },
  statLabel: { color: colors.textMuted, fontSize: 9, fontWeight: '700', letterSpacing: 1 },

  filterHeader: {
    maxWidth: 700, alignSelf: 'center', width: '100%',
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    marginBottom: 7,
  },
  filterLabel: { color: colors.text, fontSize: 12, fontWeight: '800' },
  filterCount: { color: colors.textMuted, fontSize: 11, fontWeight: '600' },
  chipsScroll:  { maxWidth: 700, alignSelf: 'center', width: '100%', flexGrow: 0, marginBottom: 14 },
  chipsContent: { gap: 8, paddingVertical: 2 },
  chip: {
    flexDirection: 'row', alignItems: 'center', gap: 5,
    paddingHorizontal: 11, paddingVertical: 7,
    borderRadius: 20, borderWidth: 1,
  },
  chipIcon: { fontSize: 13 },
  chipText: { fontSize: 12, fontWeight: '600', maxWidth: 130 },

  divider: {
    height: 1, backgroundColor: colors.border,
    maxWidth: 700, alignSelf: 'center', width: '100%', marginBottom: 14,
  },

  switcherWrap: { maxWidth: 700, alignSelf: 'center', width: '100%', marginBottom: 12 },
  switcher: {
    flexDirection: 'row',
    backgroundColor: colors.surface,
    borderRadius: 10, padding: 3,
    borderWidth: 1, borderColor: colors.border,
  },
  switchTab:       { flex: 1, paddingVertical: 8, borderRadius: 8, alignItems: 'center' },
  switchTabActive: { backgroundColor: colors.accentDim },
  switchText:      { color: colors.textMuted, fontSize: 13, fontWeight: '600' },
  switchTextActive:{ color: colors.accent, fontWeight: '700' },

  navRow: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    maxWidth: 700, alignSelf: 'center', width: '100%', marginBottom: 12,
  },
  navBtn: {
    width: 40, height: 40, alignItems: 'center', justifyContent: 'center',
    backgroundColor: colors.surface, borderRadius: 8,
    borderWidth: 1, borderColor: colors.border,
  },
  navBtnDisabled: { opacity: 0.35 },
  navArrow:         { color: colors.text, fontSize: 22, fontWeight: '400' },
  navArrowDisabled: { color: colors.textMuted },
  navLabel: { color: colors.text, fontSize: 15, fontWeight: '700' },

  legend: {
    maxWidth: 700, alignSelf: 'center', width: '100%',
    marginTop: 16, gap: 4,
  },
  legendItem:   { flexDirection: 'row', alignItems: 'center', gap: 6 },
  legendDot:    { width: 7, height: 7, borderRadius: 4 },
  legendUrgent: { width: 16, height: 3, backgroundColor: '#f87171', borderRadius: 2 },
  legendText:   { color: colors.textMuted, fontSize: 11 },
  hint: {
    color: colors.textMuted, textAlign: 'center',
    marginTop: 8, fontSize: 12, fontStyle: 'italic',
  },
});
