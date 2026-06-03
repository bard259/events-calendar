import React, { useState, useRef, useEffect, useMemo } from 'react';
import { View, Text, Pressable, StyleSheet, PanResponder, Platform } from 'react-native';
import { colors } from './theme';
import graph from '../assets/company_graph.json';
import { openCompany } from './companyStore';

const PAD = 34;
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

export default function GraphView() {
  const [W, setW] = useState(360);
  const H = Math.max(380, Math.min(W, 560) * 0.9);
  const innerW = W - 2 * PAD;
  const innerH = H - 2 * PAD;
  const px = x => PAD + x * innerW;
  const py = y => PAD + y * innerH;

  const groups = graph.groups || {};
  const byTicker = useMemo(() => Object.fromEntries(graph.nodes.map(n => [n.ticker, n])), []);
  const maxDeg = Math.max(1, ...graph.nodes.map(n => n.degree));
  const nodeR = n => 9 + Math.round((n.degree / maxDeg) * 12);

  // Cluster centroids (for labels), computed from node positions.
  const clusters = useMemo(() => {
    const acc = {};
    for (const n of graph.nodes) {
      const a = (acc[n.group] ||= { xs: 0, ys: 0, c: 0 });
      a.xs += n.x; a.ys += n.y; a.c += 1;
    }
    return Object.entries(acc).map(([g, v]) => ({ g, x: v.xs / v.c, y: v.ys / v.c }));
  }, []);

  // ── Pan + zoom ────────────────────────────────────────────────
  const [tf, setTf] = useState({ x: 0, y: 0, s: 1 });
  const tfRef = useRef(tf); tfRef.current = tf;
  const start = useRef({ x: 0, y: 0 });
  const containerRef = useRef(null);

  const pan = useRef(PanResponder.create({
    // Only claim the gesture on a real drag, so node taps still register.
    onMoveShouldSetPanResponder: (_e, g) => Math.abs(g.dx) > 3 || Math.abs(g.dy) > 3,
    onPanResponderGrant: () => { start.current = { x: tfRef.current.x, y: tfRef.current.y }; },
    onPanResponderMove: (_e, g) =>
      setTf(t => ({ ...t, x: start.current.x + g.dx, y: start.current.y + g.dy })),
  })).current;

  const zoomBy = f => setTf(t => ({ ...t, s: clamp(+(t.s * f).toFixed(3), 0.4, 5) }));
  const reset = () => setTf({ x: 0, y: 0, s: 1 });

  // Mouse-wheel zoom on web.
  useEffect(() => {
    if (Platform.OS !== 'web' || !containerRef.current) return;
    const node = containerRef.current;
    const onWheel = e => {
      e.preventDefault();
      setTf(t => ({ ...t, s: clamp(+(t.s * (e.deltaY < 0 ? 1.1 : 0.9)).toFixed(3), 0.4, 5) }));
    };
    node.addEventListener && node.addEventListener('wheel', onWheel, { passive: false });
    return () => node.removeEventListener && node.removeEventListener('wheel', onWheel);
  }, [W]);

  return (
    <View style={styles.wrap}>
      <View style={styles.banner}>
        <Text style={styles.title}>Company relationship graph</Text>
        <Text style={styles.sub}>
          {graph.nodes.length} companies · {graph.edges.length} links, grouped into clusters.
          Two companies link when they co-move in the same event's stock signals. Drag to move,
          scroll/±/ to zoom, tap a node for its company card.
        </Text>
      </View>

      <View style={styles.legend}>
        {Object.entries(groups).map(([g, c]) => (
          <View key={g} style={styles.legendItem}>
            <View style={[styles.legendDot, { backgroundColor: c }]} />
            <Text style={styles.legendText}>{g}</Text>
          </View>
        ))}
      </View>

      <View
        ref={containerRef}
        style={[styles.plot, { height: H }]}
        onLayout={e => setW(e.nativeEvent.layout.width)}
        {...pan.panHandlers}
      >
        {/* zoom controls (fixed, outside the transformed canvas) */}
        <View style={styles.controls} pointerEvents="box-none">
          <Pressable style={styles.ctrlBtn} onPress={() => zoomBy(1.25)}><Text style={styles.ctrlTxt}>+</Text></Pressable>
          <Pressable style={styles.ctrlBtn} onPress={() => zoomBy(0.8)}><Text style={styles.ctrlTxt}>−</Text></Pressable>
          <Pressable style={styles.ctrlBtn} onPress={reset}><Text style={styles.ctrlTxtSm}>⟲</Text></Pressable>
        </View>

        {/* transformed canvas (pans + zooms) */}
        <View style={[styles.canvas, { transform: [{ translateX: tf.x }, { translateY: tf.y }, { scale: tf.s }] }]}>
          {/* cluster labels (behind nodes) */}
          {clusters.map(c => (
            <Text key={c.g} pointerEvents="none" style={[styles.clusterLabel, {
              left: px(c.x) - 70, top: py(c.y) - 8, color: (groups[c.g] || colors.textMuted) + 'cc',
            }]} numberOfLines={1}>{c.g}</Text>
          ))}

          {/* edges */}
          {graph.edges.map((e, i) => {
            const a = byTicker[e.a], b = byTicker[e.b];
            if (!a || !b) return null;
            const x1 = px(a.x), y1 = py(a.y), x2 = px(b.x), y2 = py(b.y);
            const dx = x2 - x1, dy = y2 - y1;
            const len = Math.hypot(dx, dy);
            const angle = (Math.atan2(dy, dx) * 180) / Math.PI;
            return (
              <View key={`e${i}`} pointerEvents="none" style={[styles.edge, {
                left: (x1 + x2) / 2 - len / 2, top: (y1 + y2) / 2,
                width: len, height: Math.min(4, 1 + e.weight * 0.5),
                opacity: Math.min(0.55, 0.2 + e.weight * 0.06),
                transform: [{ rotate: `${angle}deg` }],
              }]} />
            );
          })}

          {/* nodes */}
          {graph.nodes.map(n => {
            const r = nodeR(n);
            const color = groups[n.group] || colors.accent;
            return (
              <Pressable key={n.ticker} onPress={() => openCompany(n.ticker)}
                style={[styles.node, {
                  left: px(n.x) - r, top: py(n.y) - r, width: r * 2, height: r * 2,
                  borderRadius: r, backgroundColor: color + '33', borderColor: color,
                }]}>
                <Text style={[styles.nodeLabel, { color }]} numberOfLines={1}>{n.ticker}</Text>
              </Pressable>
            );
          })}
        </View>
      </View>

      <Text style={styles.hint}>Node size = connections · line thickness = shared events · drag to pan · scroll or ± to zoom</Text>
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
  canvas: { ...StyleSheet.absoluteFillObject },
  controls: { position: 'absolute', top: 8, right: 8, zIndex: 10, gap: 6 },
  ctrlBtn: {
    width: 30, height: 30, borderRadius: 8, backgroundColor: colors.surfaceRaised,
    borderWidth: 1, borderColor: colors.border, alignItems: 'center', justifyContent: 'center',
  },
  ctrlTxt: { color: colors.text, fontSize: 18, fontWeight: '800', lineHeight: 20 },
  ctrlTxtSm: { color: colors.text, fontSize: 13, fontWeight: '800' },
  clusterLabel: {
    position: 'absolute', width: 140, textAlign: 'center',
    fontSize: 9, fontWeight: '800', letterSpacing: 0.5, textTransform: 'uppercase', opacity: 0.6,
  },
  edge: { position: 'absolute', backgroundColor: colors.borderAccent },
  node: { position: 'absolute', borderWidth: 1.5, alignItems: 'center', justifyContent: 'center' },
  nodeLabel: { fontSize: 8, fontWeight: '800' },
  hint: { color: colors.textMuted, fontSize: 11, fontStyle: 'italic', textAlign: 'center', marginTop: 10 },
});
