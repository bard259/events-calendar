import React, { useMemo, useState } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { colors } from './theme';

function pct(v) {
  if (v == null || Number.isNaN(v)) return 'Pending';
  const sign = v > 0 ? '+' : '';
  return `${sign}${v.toFixed(2)}%`;
}

function price(v) {
  if (v == null || Number.isNaN(v)) return '—';
  return `$${Number(v).toFixed(2)}`;
}

function reportExcerpt(markdown) {
  return String(markdown || '')
    .split('\n')
    .filter(line => line.trim() && !line.startsWith('#'))
    .slice(0, 18);
}

function Stat({ label, value, tone }) {
  return (
    <View style={styles.stat}>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={[styles.statLabel, tone ? { color: tone } : null]}>{label}</Text>
    </View>
  );
}

function DecisionRow({ d }) {
  const ret = d.performance?.return_pct;
  const latest = d.performance?.latest;
  const color = ret == null ? colors.textMuted : ret >= 0 ? '#34d399' : '#f87171';
  return (
    <View style={styles.rowCard}>
      <View style={styles.rowTop}>
        <Text style={styles.ticker}>{d.action} {d.ticker}</Text>
        <Text style={[styles.score, { color }]}>{pct(ret)}</Text>
      </View>
      <Text style={styles.company} numberOfLines={1}>{d.company}</Text>
      <Text style={styles.rowMeta}>
        {d.event_date} · score {d.score} · {latest ? `latest ${price(latest.price)}` : 'price pending'}
      </Text>
      <Text style={styles.thesis} numberOfLines={2}>{d.thesis}</Text>
    </View>
  );
}

export default function ReportsView({ data }) {
  const [tab, setTab] = useState('performance');
  const decisions = data.latest_decisions || [];
  const tracked = decisions.filter(d => d.action === 'BUY' || d.action === 'WATCH');
  const topTracked = useMemo(
    () => tracked.slice().sort((a, b) => b.score - a.score).slice(0, 20),
    [tracked],
  );
  const perf = data.performance || {};
  const latestDecisionRun = data.decision_runs?.[0];
  const latestCriticRun = data.critic_runs?.[0];
  const findings = data.latest_findings || [];
  const lessons = data.memory?.lessons || [];

  return (
    <View style={styles.wrap}>
      <View style={styles.header}>
        <Text style={styles.title}>Agent reports</Text>
        <Text style={styles.sub}>
          Decision run {latestDecisionRun?.run_date || '—'} · Critic run {latestCriticRun?.run_date || '—'}
        </Text>
      </View>

      <View style={styles.statsGrid}>
        <Stat label="Tracked" value={perf.tracked_count ?? 0} />
        <Stat label="Measured" value={perf.measured_count ?? 0} />
        <Stat label="Pending" value={perf.pending_count ?? 0} />
        <Stat label="Avg return" value={pct(perf.avg_return_pct)} tone={perf.avg_return_pct >= 0 ? '#34d399' : '#f87171'} />
      </View>

      <View style={styles.tabBar}>
        {[
          ['performance', 'Performance'],
          ['decisions', 'Decision report'],
          ['critic', 'Critic report'],
          ['memory', 'Memory'],
        ].map(([key, label]) => (
          <Pressable key={key} onPress={() => setTab(key)}
            style={[styles.tab, tab === key && styles.tabActive]}>
            <Text style={[styles.tabText, tab === key && styles.tabTextActive]}>{label}</Text>
          </Pressable>
        ))}
      </View>

      {tab === 'performance' && (
        <View>
          <Text style={styles.sectionTitle}>Open BUY / WATCH ideas</Text>
          {topTracked.length ? topTracked.map(d => <DecisionRow key={d.id} d={d} />)
            : <Text style={styles.empty}>No BUY or WATCH decisions in the latest run.</Text>}
        </View>
      )}

      {tab === 'decisions' && (
        <View style={styles.reportCard}>
          <Text style={styles.sectionTitle}>Latest decision report</Text>
          {reportExcerpt(data.latest_decision_report).map((line, i) => (
            <Text key={i} style={styles.reportLine}>{line}</Text>
          ))}
        </View>
      )}

      {tab === 'critic' && (
        <View>
          <View style={styles.reportCard}>
            <Text style={styles.sectionTitle}>Latest critic report</Text>
            {reportExcerpt(data.latest_critic_report).map((line, i) => (
              <Text key={i} style={styles.reportLine}>{line}</Text>
            ))}
          </View>
          <Text style={styles.sectionTitle}>Findings</Text>
          {findings.length ? findings.map(f => (
            <View key={f.id} style={styles.rowCard}>
              <Text style={styles.ticker}>{f.finding_type} · {f.ticker || 'n/a'}</Text>
              <Text style={styles.thesis}>{f.summary}</Text>
              <Text style={styles.rowMeta}>{f.lesson}</Text>
            </View>
          )) : <Text style={styles.empty}>No critic findings in the latest run.</Text>}
        </View>
      )}

      {tab === 'memory' && (
        <View>
          <Text style={styles.sectionTitle}>Key knowledge memory</Text>
          {(data.memory?.principles || []).map((p, i) => (
            <View key={i} style={styles.memoryItem}>
              <Text style={styles.reportLine}>{p}</Text>
            </View>
          ))}
          <Text style={styles.sectionTitle}>Lessons</Text>
          {lessons.length ? lessons.slice(-12).map((l, i) => (
            <View key={i} style={styles.memoryItem}>
              <Text style={styles.rowMeta}>{l.date} · {l.source}</Text>
              <Text style={styles.reportLine}>{l.lesson}</Text>
            </View>
          )) : <Text style={styles.empty}>No critic lessons recorded yet.</Text>}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { width: '100%', maxWidth: 700, alignSelf: 'center' },
  header: { marginBottom: 12 },
  title: { color: colors.text, fontSize: 20, fontWeight: '800' },
  sub: { color: colors.textMuted, fontSize: 12, marginTop: 3 },
  statsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 12 },
  stat: {
    flexGrow: 1, minWidth: 120, backgroundColor: colors.surface,
    borderWidth: 1, borderColor: colors.border, borderRadius: 8,
    padding: 10,
  },
  statValue: { color: colors.text, fontSize: 18, fontWeight: '800' },
  statLabel: { color: colors.textMuted, fontSize: 10, fontWeight: '700', marginTop: 2 },
  tabBar: {
    flexDirection: 'row', marginBottom: 14, backgroundColor: colors.surface,
    borderRadius: 10, padding: 3, borderWidth: 1, borderColor: colors.border,
  },
  tab: { flex: 1, paddingVertical: 8, borderRadius: 8, alignItems: 'center' },
  tabActive: { backgroundColor: colors.accentDim },
  tabText: { color: colors.textMuted, fontSize: 12, fontWeight: '600' },
  tabTextActive: { color: colors.accent, fontWeight: '700' },
  sectionTitle: { color: colors.text, fontSize: 14, fontWeight: '800', marginBottom: 8 },
  rowCard: {
    backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border,
    borderRadius: 8, padding: 10, marginBottom: 8,
  },
  rowTop: { flexDirection: 'row', justifyContent: 'space-between', gap: 8 },
  ticker: { color: colors.text, fontSize: 13, fontWeight: '800' },
  score: { fontSize: 13, fontWeight: '800' },
  company: { color: colors.textSecondary, fontSize: 12, marginTop: 2 },
  rowMeta: { color: colors.textMuted, fontSize: 11, marginTop: 4, lineHeight: 15 },
  thesis: { color: colors.textSecondary, fontSize: 12, lineHeight: 17, marginTop: 6 },
  reportCard: {
    backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border,
    borderRadius: 8, padding: 12, marginBottom: 12,
  },
  reportLine: { color: colors.textSecondary, fontSize: 12, lineHeight: 18, marginBottom: 4 },
  memoryItem: {
    backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border,
    borderRadius: 8, padding: 10, marginBottom: 8,
  },
  empty: { color: colors.textMuted, fontSize: 13, textAlign: 'center', marginTop: 20 },
});
