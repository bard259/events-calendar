import React, { useState, useMemo } from 'react';
import {
  Modal, View, Text, TextInput, ScrollView, Pressable, StyleSheet, Platform,
} from 'react-native';
import { colors, categoryColors, categoryIcons, importanceConfig } from './theme';
import { searchEvents } from './data';

function prettyDate(date) {
  return new Date(date + 'T00:00:00').toLocaleDateString(undefined, {
    weekday: 'short', month: 'short', day: 'numeric',
  });
}

function ResultRow({ ev, onPress }) {
  const col = categoryColors[ev.category_id] || colors.accent;
  const imp = importanceConfig[ev.importance] || importanceConfig.low;
  return (
    <Pressable onPress={() => onPress(ev)}
      style={({ pressed, hovered }) => [styles.row, (pressed || hovered) && styles.rowHover]}>
      <View style={[styles.stripe, { backgroundColor: col }]} />
      <View style={styles.rowBody}>
        <View style={styles.rowTop}>
          <Text style={[styles.cat, { color: col }]} numberOfLines={1}>
            {categoryIcons[ev.category_id]} {ev.category}
          </Text>
          <Text style={styles.date}>{prettyDate(ev.event_date)}</Text>
        </View>
        <Text style={styles.title} numberOfLines={2}>{ev.title}</Text>
        <View style={styles.rowBottom}>
          {!!ev.entity && <Text style={styles.entity} numberOfLines={1}>{ev.entity}</Text>}
          <View style={[styles.impPill, { backgroundColor: imp.color + '22', borderColor: imp.color }]}>
            <Text style={[styles.impTxt, { color: imp.color }]}>{imp.label}</Text>
          </View>
        </View>
      </View>
    </Pressable>
  );
}

export default function SearchModal({ visible, onClose, onPick }) {
  const [query, setQuery] = useState('');
  const results = useMemo(() => searchEvents(query), [query]);

  function pick(ev) {
    onPick(ev);
    setQuery('');
  }

  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
      <View style={styles.backdrop}>
        <View style={styles.sheet}>
          {/* Search bar */}
          <View style={styles.searchRow}>
            <View style={styles.inputWrap}>
              <Text style={styles.searchIcon}>🔍</Text>
              <TextInput
                style={styles.input}
                placeholder="Search events, companies, tickers…"
                placeholderTextColor={colors.textMuted}
                value={query}
                onChangeText={setQuery}
                autoFocus
                returnKeyType="search"
              />
              {query.length > 0 && (
                <Pressable onPress={() => setQuery('')} style={styles.clearBtn}>
                  <Text style={styles.clearTxt}>✕</Text>
                </Pressable>
              )}
            </View>
            <Pressable onPress={onClose} style={styles.cancelBtn}>
              <Text style={styles.cancelTxt}>Cancel</Text>
            </Pressable>
          </View>

          {/* Result count */}
          {query.trim().length > 0 && (
            <Text style={styles.countTxt}>
              {results.length} result{results.length !== 1 ? 's' : ''}
            </Text>
          )}

          {/* Results */}
          <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent}
            keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
            {query.trim().length === 0 ? (
              <Text style={styles.hint}>
                Type to search across all events — by title, company, category or ticker
                (e.g. “Apple”, “NVDA”, “Starship”, “earnings”).
              </Text>
            ) : results.length === 0 ? (
              <Text style={styles.hint}>No events match “{query.trim()}”.</Text>
            ) : (
              results.map((ev, i) => <ResultRow key={i} ev={ev} onPress={pick} />)
            )}
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'flex-end' },
  sheet: {
    backgroundColor: colors.bg,
    borderTopLeftRadius: 24, borderTopRightRadius: 24,
    borderTopWidth: 1, borderColor: colors.borderAccent,
    maxHeight: '92%', minHeight: '60%',
    paddingTop: 14,
  },

  searchRow: {
    flexDirection: 'row', alignItems: 'center', gap: 10,
    paddingHorizontal: 16, marginBottom: 10,
  },
  inputWrap: {
    flex: 1, flexDirection: 'row', alignItems: 'center',
    backgroundColor: colors.surface, borderRadius: 10,
    borderWidth: 1, borderColor: colors.border,
    paddingHorizontal: 10,
  },
  searchIcon: { fontSize: 14, marginRight: 6 },
  input: {
    flex: 1, color: colors.text, fontSize: 15,
    paddingVertical: Platform.OS === 'web' ? 10 : 9,
    ...(Platform.OS === 'web' ? { outlineStyle: 'none' } : {}),
  },
  clearBtn: { padding: 4 },
  clearTxt: { color: colors.textMuted, fontSize: 13 },
  cancelBtn: { paddingVertical: 6 },
  cancelTxt: { color: colors.accent, fontSize: 15, fontWeight: '600' },

  countTxt: {
    color: colors.textMuted, fontSize: 11, fontWeight: '700',
    letterSpacing: 0.5, paddingHorizontal: 20, marginBottom: 6,
  },

  scroll: { paddingHorizontal: 16 },
  scrollContent: { paddingBottom: 40 },
  hint: {
    color: colors.textMuted, fontSize: 13, lineHeight: 20,
    textAlign: 'center', marginTop: 40, paddingHorizontal: 20,
  },

  row: {
    flexDirection: 'row',
    backgroundColor: colors.surface,
    borderRadius: 12, marginBottom: 8,
    overflow: 'hidden',
    borderWidth: 1, borderColor: colors.border,
  },
  rowHover: { backgroundColor: colors.surfaceHover },
  stripe:   { width: 4 },
  rowBody:  { flex: 1, padding: 12 },
  rowTop:   { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 },
  cat:      { fontSize: 11, fontWeight: '700', flex: 1, marginRight: 8 },
  date:     { color: colors.textMuted, fontSize: 11, fontWeight: '600' },
  title:    { color: colors.text, fontSize: 14, fontWeight: '700', lineHeight: 19, marginBottom: 6 },
  rowBottom:{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8 },
  entity:   { color: colors.textSecondary, fontSize: 12, flex: 1 },
  impPill:  { borderWidth: 1, borderRadius: 4, paddingHorizontal: 6, paddingVertical: 2 },
  impTxt:   { fontSize: 10, fontWeight: '800', letterSpacing: 0.8 },
});
