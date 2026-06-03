import React from 'react';
import { Modal, View, Text, Pressable, StyleSheet, ScrollView } from 'react-native';
import { colors } from './theme';
import { COMPANY_CARDS } from './companyStore';

const SRC_LABEL = { curated: 'curated profile', sic: 'SEC industry (SIC)', size: 'derived from filings' };

export default function CompanyModal({ ticker, onClose }) {
  const c = ticker ? COMPANY_CARDS[ticker] : null;
  return (
    <Modal visible={!!c} transparent animationType="fade" onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose}>
        <Pressable style={styles.sheet} onPress={() => {}}>
          {c ? (
            <ScrollView showsVerticalScrollIndicator={false}>
              <View style={styles.headRow}>
                <View style={styles.tickerPill}><Text style={styles.tickerText}>{c.ticker}</Text></View>
                <Text style={styles.eyebrow}>COMPANY</Text>
                <Pressable onPress={onClose} style={styles.closeBtn}>
                  <Text style={styles.closeIcon}>✕</Text>
                </Pressable>
              </View>
              <Text style={styles.name}>{c.name}</Text>
              <Text style={styles.intro}>{c.intro}</Text>
              <View style={styles.metaRow}>
                {c.industry ? <Tag label={c.industry} /> : null}
                {c.size ? <Tag label={`${c.size}-cap`} /> : null}
              </View>
              <Text style={styles.events}>
                Appears in {c.n_events} event{c.n_events !== 1 ? 's' : ''}
                {c.next_event ? ` · next ${c.next_event}` : ''}
              </Text>
              <Text style={styles.disc}>Company profile · {SRC_LABEL[c.intro_source] || c.intro_source}</Text>
            </ScrollView>
          ) : null}
        </Pressable>
      </Pressable>
    </Modal>
  );
}

function Tag({ label }) {
  return <View style={styles.tag}><Text style={styles.tagText}>{label}</Text></View>;
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1, backgroundColor: 'rgba(0,0,0,0.7)',
    alignItems: 'center', justifyContent: 'center', padding: 20,
  },
  sheet: {
    width: '100%', maxWidth: 460, maxHeight: '80%',
    backgroundColor: colors.surfaceRaised, borderRadius: 16,
    borderWidth: 1, borderColor: colors.borderAccent, padding: 18,
  },
  headRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 8 },
  tickerPill: {
    backgroundColor: colors.accentDim, borderRadius: 6,
    paddingHorizontal: 8, paddingVertical: 3,
  },
  tickerText: { color: colors.accent, fontSize: 13, fontWeight: '800', letterSpacing: 0.5 },
  eyebrow: { color: colors.textMuted, fontSize: 9, fontWeight: '800', letterSpacing: 1.5, flex: 1 },
  closeBtn: {
    width: 28, height: 28, borderRadius: 14, backgroundColor: colors.surface,
    borderWidth: 1, borderColor: colors.border, alignItems: 'center', justifyContent: 'center',
  },
  closeIcon: { color: colors.textSecondary, fontSize: 12, fontWeight: '700' },
  name: { color: colors.text, fontSize: 18, fontWeight: '800', marginBottom: 6 },
  intro: { color: colors.textSecondary, fontSize: 13, lineHeight: 19, marginBottom: 10 },
  metaRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 10 },
  tag: {
    borderWidth: 1, borderColor: colors.border, borderRadius: 5,
    paddingHorizontal: 8, paddingVertical: 3, backgroundColor: colors.surface,
  },
  tagText: { color: colors.textSecondary, fontSize: 11, fontWeight: '600', textTransform: 'capitalize' },
  events: { color: colors.textMuted, fontSize: 12, fontWeight: '600', marginBottom: 8 },
  disc: { color: colors.textMuted, fontSize: 10, fontStyle: 'italic' },
});
