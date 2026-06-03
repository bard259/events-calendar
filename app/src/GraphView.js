import React, { useState, useRef, useEffect, useMemo } from 'react';
import { View, Text, Pressable, StyleSheet, PanResponder, Platform } from 'react-native';
import { colors } from './theme';
import coMove from '../assets/company_graph.json';
import ecosystem from '../assets/anthropic_graph.json';
import { openCompany } from './companyStore';

const PAD = 34;
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const shortLabel = n => n.ticker || (n.label || n.id || '').split(/[ (]/)[0];

// Normalize the two datasets to one shape: nodes{key,label,color,ticker,degree,x,y,center},
// edges{a,b,color,width}, plus legends.
function model(mode) {
  if (mode === 'ecosystem') {
    const sc = ecosystem.sectorColors || {}, ec = ecosystem.edgeColors || {};
    return {
      nodes: ecosystem.nodes.map(n => ({
        key: n.id, label: n.label, ticker: n.ticker, degree: n.degree, x: n.x, y: n.y,
        color: sc[n.sector] || colors.accent, center: n.id === ecosystem.center,
      })),
      edges: ecosystem.edges.map(e => ({ a: e.a, b: e.b, color: ec[e.type] || colors.borderAccent, width: 1.5 })),
      nodeLegend: sc, edgeLegend: ec,
    };
  }
  const gc = coMove.groups || {};
  return {
    nodes: coMove.nodes.map(n => ({
      key: n.ticker, label: n.ticker, ticker: n.ticker, degree: n.degree, x: n.x, y: n.y,
      color: gc[n.group] || colors.accent, center: false,
    })),
    edges: coMove.edges.map(e => ({ a: e.a, b: e.b, color: colors.borderAccent,
      width: Math.min(4, 1 + e.weight * 0.5), opacity: Math.min(0.55, 0.2 + e.weight * 0.06) })),
    nodeLegend: gc, edgeLegend: null,
  };
}

export default function GraphView() {
  const [mode, setMode] = useState('ecosystem');
  const g = useMemo(() => model(mode), [mode]);
  const byKey = useMemo(() => Object.fromEntries(g.nodes.map(n => [n.key, n])), [g]);
  const maxDeg = Math.max(1, ...g.nodes.map(n => n.degree));

  const [W, setW] = useState(360);
  const H = Math.max(420, Math.min(W, 600) * 0.95);
  const px = x => PAD + x * (W - 2 * PAD);
  const py = y => PAD + y * (H - 2 * PAD);
  const nodeR = n => (n.center ? 20 : 8 + Math.round((n.degree / maxDeg) * 13));

  // pan + zoom
  const [tf, setTf] = useState({ x: 0, y: 0, s: 1 });
  const tfRef = useRef(tf); tfRef.current = tf;
  const start = useRef({ x: 0, y: 0 });
  const containerRef = useRef(null);
  const pan = useRef(PanResponder.create({
    onMoveShouldSetPanResponder: (_e, gs) => Math.abs(gs.dx) > 3 || Math.abs(gs.dy) > 3,
    onPanResponderGrant: () => { start.current = { x: tfRef.current.x, y: tfRef.current.y }; },
    onPanResponderMove: (_e, gs) => setTf(t => ({ ...t, x: start.current.x + gs.dx, y: start.current.y + gs.dy })),
  })).current;
  const zoomBy = f => setTf(t => ({ ...t, s: clamp(+(t.s * f).toFixed(3), 0.4, 6) }));
  const reset = () => setTf({ x: 0, y: 0, s: 1 });
  useEffect(() => {
    if (Platform.OS !== 'web' || !containerRef.current) return;
    const node = containerRef.current;
    const onWheel = e => { e.preventDefault(); setTf(t => ({ ...t, s: clamp(+(t.s * (e.deltaY < 0 ? 1.1 : 0.9)).toFixed(3), 0.4, 6) })); };
    node.addEventListener && node.addEventListener('wheel', onWheel, { passive: false });
    return () => node.removeEventListener && node.removeEventListener('wheel', onWheel);
  }, [W]);

  return (
    <View style={styles.wrap}>
      <View style={styles.banner}>
        <Text style={styles.title}>
          {mode === 'ecosystem' ? 'Anthropic ecosystem map' : 'Company relationship graph'}
        </Text>
        <Text style={styles.sub}>
          {mode === 'ecosystem'
            ? `${g.nodes.length} entities · ${g.edges.length} typed links across AI · chips · space · energy. Anthropic at center; edges = who invests in / supplies / powers / partners with whom.`
            : `${g.nodes.length} companies · ${g.edges.length} links — companies that co-move in the same event's stock signals.`}
          {'  '}Drag to pan, scroll/± to zoom, tap a node for its company card.
        </Text>
      </View>

      {/* mode toggle */}
      <View style={styles.toggle}>
        {[['ecosystem', 'Ecosystem map'], ['comovement', 'Co-movement']].map(([m, label]) => (
          <Pressable key={m} onPress={() => { setMode(m); reset(); }}
            style={[styles.tBtn, mode === m && styles.tBtnOn]}>
            <Text style={[styles.tTxt, mode === m && styles.tTxtOn]}>{label}</Text>
          </Pressable>
        ))}
      </View>

      {/* node (sector) legend */}
      <View style={styles.legend}>
        {Object.entries(g.nodeLegend).map(([k, c]) => (
          <View key={k} style={styles.legendItem}>
            <View style={[styles.legendDot, { backgroundColor: c }]} />
            <Text style={styles.legendText}>{k}</Text>
          </View>
        ))}
      </View>
      {/* edge (relationship) legend */}
      {g.edgeLegend && (
        <View style={styles.legend}>
          {Object.entries(g.edgeLegend).map(([k, c]) => (
            <View key={k} style={styles.legendItem}>
              <View style={[styles.legendLine, { backgroundColor: c }]} />
              <Text style={styles.legendText}>{k.replace(/_/g, ' ')}</Text>
            </View>
          ))}
        </View>
      )}

      <View ref={containerRef} style={[styles.plot, { height: H }]}
        onLayout={e => setW(e.nativeEvent.layout.width)} {...pan.panHandlers}>
        <View style={styles.controls} pointerEvents="box-none">
          <Pressable style={styles.ctrlBtn} onPress={() => zoomBy(1.25)}><Text style={styles.ctrlTxt}>+</Text></Pressable>
          <Pressable style={styles.ctrlBtn} onPress={() => zoomBy(0.8)}><Text style={styles.ctrlTxt}>−</Text></Pressable>
          <Pressable style={styles.ctrlBtn} onPress={reset}><Text style={styles.ctrlTxtSm}>⟲</Text></Pressable>
        </View>

        <View style={[styles.canvas, { transform: [{ translateX: tf.x }, { translateY: tf.y }, { scale: tf.s }] }]}>
          {/* edges */}
          {g.edges.map((e, i) => {
            const a = byKey[e.a], b = byKey[e.b];
            if (!a || !b) return null;
            const x1 = px(a.x), y1 = py(a.y), x2 = px(b.x), y2 = py(b.y);
            const dx = x2 - x1, dy = y2 - y1;
            const len = Math.hypot(dx, dy);
            const angle = (Math.atan2(dy, dx) * 180) / Math.PI;
            return (
              <View key={`e${i}`} pointerEvents="none" style={{
                position: 'absolute', left: (x1 + x2) / 2 - len / 2, top: (y1 + y2) / 2,
                width: len, height: e.width || 1.5, backgroundColor: e.color,
                opacity: e.opacity != null ? e.opacity : 0.5, transform: [{ rotate: `${angle}deg` }],
              }} />
            );
          })}
          {/* nodes */}
          {g.nodes.map(n => {
            const r = nodeR(n);
            return (
              <Pressable key={n.key} onPress={() => n.ticker && openCompany(n.ticker)}
                style={[styles.node, {
                  left: px(n.x) - r, top: py(n.y) - r, width: r * 2, height: r * 2, borderRadius: r,
                  backgroundColor: n.color + (n.center ? '55' : '33'),
                  borderColor: n.color, borderWidth: n.center ? 2.5 : 1.5,
                }]}>
                <Text style={[styles.nodeLabel, { color: n.color, fontSize: n.center ? 9 : 8 }]} numberOfLines={1}>
                  {shortLabel(n)}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </View>

      <Text style={styles.hint}>
        Node size = connections{mode === 'ecosystem' ? ' · Anthropic pinned at center' : ' · line = shared events'} · tap a public company for its card
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { width: '100%', maxWidth: 700, alignSelf: 'center' },
  banner: { backgroundColor: colors.surface, borderRadius: 12, borderWidth: 1, borderColor: colors.border, padding: 14, marginBottom: 10 },
  title: { color: colors.text, fontSize: 16, fontWeight: '800' },
  sub: { color: colors.textMuted, fontSize: 12, marginTop: 4, lineHeight: 17 },
  toggle: { flexDirection: 'row', backgroundColor: colors.surface, borderRadius: 10, padding: 3, borderWidth: 1, borderColor: colors.border, marginBottom: 10 },
  tBtn: { flex: 1, paddingVertical: 7, borderRadius: 8, alignItems: 'center' },
  tBtnOn: { backgroundColor: colors.accentDim },
  tTxt: { color: colors.textMuted, fontSize: 12, fontWeight: '700' },
  tTxtOn: { color: colors.accent },
  legend: { flexDirection: 'row', flexWrap: 'wrap', gap: 9, marginBottom: 8 },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  legendDot: { width: 9, height: 9, borderRadius: 5 },
  legendLine: { width: 14, height: 3, borderRadius: 2 },
  legendText: { color: colors.textSecondary, fontSize: 10, fontWeight: '600', textTransform: 'capitalize' },
  plot: { width: '100%', backgroundColor: colors.surface, borderRadius: 12, borderWidth: 1, borderColor: colors.border, position: 'relative', overflow: 'hidden' },
  canvas: { ...StyleSheet.absoluteFillObject },
  controls: { position: 'absolute', top: 8, right: 8, zIndex: 10, gap: 6 },
  ctrlBtn: { width: 30, height: 30, borderRadius: 8, backgroundColor: colors.surfaceRaised, borderWidth: 1, borderColor: colors.border, alignItems: 'center', justifyContent: 'center' },
  ctrlTxt: { color: colors.text, fontSize: 18, fontWeight: '800', lineHeight: 20 },
  ctrlTxtSm: { color: colors.text, fontSize: 13, fontWeight: '800' },
  node: { position: 'absolute', alignItems: 'center', justifyContent: 'center' },
  nodeLabel: { fontWeight: '800' },
  hint: { color: colors.textMuted, fontSize: 11, fontStyle: 'italic', textAlign: 'center', marginTop: 10 },
});
