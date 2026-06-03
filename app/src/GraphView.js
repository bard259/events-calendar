import React, { useState } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { colors } from './theme';
import graph from '../assets/company_graph.json';
import { openCompany } from './companyStore';

const PAD = 30;

export default function GraphView() {
  const [W, setW] = useState(360);
  const H = Math.max(360, Math.min(W, 560) * 0.82);
  const innerW = W - 2 * PAD;
  const innerH = H - 2 * PAD;
  const px = x => PAD + x * innerW;
  const py = y => PAD + y * innerH;

  const byTicker = Object.fromEntries(graph.nodes.map(n => [n.ticker, n]));
  const maxDeg = Math.max(1, ...graph.nodes.map(n => n.degree));
  const nodeR = n => 9 + Math.round((n.degree / maxDeg) * 12); // 9–21px radius
  const groups = graph.groups || {};

  return (
    <View style={styles.wrap}>
      <View style={styles.banner}>
        <Text style={styles.title}>Company relationship graph</Text>
        <Text style={styles.sub}>
          {graph.nodes.length} companies · {graph.edges.length} links. Two companies are linked
          when they co-move in the same event's stock signals (AI chain, defense, energy…).
          Tap a node for its company card.
        </Text>
      </View>

      {/* Legend */}
      <View style={styles.legend}>
        {Object.entries(groups).map(([g, c]) => (
          <View key={g} style={styles.legendItem}>
            <View style={[styles.legendDot, { backgroundColor: c }]} />
            <Text style={styles.legendText}>{g}</Text>
          </View>
        ))}
      </View>

      {/* Plot area */}
      <View style={[styles.plot, { height: H }]} onLayout={e => setW(e.nativeEvent.layout.width)}>
        {/* edges first (under nodes) */}
        {graph.edges.map((e, i) => {
          const a = byTicker[e.a], b = byTicker[e.b];
          if (!a || !b) return null;
          const x1 = px(a.x), y1 = py(a.y), x2 = px(b.x), y2 = py(b.y);
          const dx = x2 - x1, dy = y2 - y1;
          const len = Math.hypot(dx, dy);
          const angle = (Math.atan2(dy, dx) * 180) / Math.PI;
          return (
            <View key={`e${i}`} pointerEvents="none" style={[styles.edge, {
              left: (x1 + x2) / 2 - len / 2,
              top: (y1 + y2) / 2,
              width: len,
              height: Math.min(4, 1 + e.weight * 0.5),
              opacity: Math.min(0.5, 0.18 + e.weight * 0.06),
              transform: [{ rotate: `${angle}deg` }],
            }]} />
          );
        })}

        {/* nodes on top */}
        {graph.nodes.map(n => {
          const r = nodeR(n);
          const color = groups[n.group] || colors.accent;
          return (
            <Pressable key={n.ticker} onPress={() => openCompany(n.ticker)}
              style={[styles.node, { left: px(n.x) - r, top: py(n.y) - r,
                width: r * 2, height: r * 2, borderRadius: r,
                backgroundColor: color + '33', borderColor: color }]}>
              <Text style={[styles.nodeLabel, { color }]} numberOfLines={1}>{n.ticker}</Text>
            </Pressable>
          );
        })}
      </View>

      <Text style={styles.hint}>Node size = number of connections · line thickness = shared events</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { width: '100%', maxWidth: 700, alignSelf: 'center' },
  banner: {
    backgroundColor: colors.surface, borderRadius: 12, borderWidth: 1, borderColor: colors.border,
    padding: 14, marginBottom: 12,
  },
  title: { color: colors.text, fontSize: 16, fontWeight: '800' },
  sub: { color: colors.textMuted, fontSize: 12, marginTop: 4, lineHeight: 17 },
  legend: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 10 },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  legendDot: { width: 9, height: 9, borderRadius: 5 },
  legendText: { color: colors.textSecondary, fontSize: 10, fontWeight: '600' },
  plot: {
    width: '100%', backgroundColor: colors.surface, borderRadius: 12,
    borderWidth: 1, borderColor: colors.border, position: 'relative', overflow: 'hidden',
  },
  edge: { position: 'absolute', backgroundColor: colors.borderAccent },
  node: {
    position: 'absolute', borderWidth: 1.5, alignItems: 'center', justifyContent: 'center',
  },
  nodeLabel: { fontSize: 8, fontWeight: '800' },
  hint: { color: colors.textMuted, fontSize: 11, fontStyle: 'italic', textAlign: 'center', marginTop: 10 },
});
