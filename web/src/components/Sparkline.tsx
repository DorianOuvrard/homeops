import { useMemo } from "react";

const TEAL = "#7a9e7e";
const ORANGE = "#d4915e";
const RED = "#c45d5d";

interface Props {
  values: number[];
  width?: number;
  height?: number;
}

export default function Sparkline({ values, width = 280, height = 48 }: Props) {
  if (values.length < 2) return null;

  const { points, linePath, areaPath, anomalyStart, isAnomaly, dotColor } = useMemo(() => {
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    const padY = 3;

    const pts = values.map((v, i) => ({
      x: (i / (values.length - 1)) * width,
      y: padY + (1 - (v - min) / range) * (height - padY * 2),
    }));

    const line = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ");
    const area = `${line} L${width},${height} L0,${height} Z`;

    // Anomaly detection: baseline from first 80%, compare tail
    const baselineEnd = Math.floor(values.length * 0.8);
    const baseline = values.slice(0, baselineEnd);
    const bMean = baseline.reduce((a, b) => a + b, 0) / baseline.length;
    const bStddev = Math.sqrt(baseline.reduce((a, b) => a + (b - bMean) ** 2, 0) / baseline.length);
    const threshold = bMean + 2 * bStddev;

    // Find first sustained anomaly
    let anomalyIdx = -1;
    for (let i = baselineEnd; i < values.length - 1; i++) {
      if (values[i] > threshold && values[i + 1] > threshold) {
        anomalyIdx = i;
        break;
      }
    }

    const anom = anomalyIdx >= 0;
    const anomX = anom ? anomalyIdx / (values.length - 1) : 1;
    const lastVal = values[values.length - 1];
    const dot = anom && lastVal > threshold ? RED : TEAL;

    return { points: pts, linePath: line, areaPath: area, anomalyStart: anomX, isAnomaly: anom, dotColor: dot };
  }, [values, width, height]);

  const gradId = `spark-grad-${width}-${height}`;
  const fillId = `spark-fill-${width}-${height}`;

  return (
    <svg width="100%" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" className="block">
      <defs>
        {isAnomaly ? (
          <>
            <linearGradient id={gradId} x1="0" x2="1" y1="0" y2="0">
              <stop offset={`${(anomalyStart * 0.95).toFixed(2)}`} stopColor={TEAL} />
              <stop offset={`${anomalyStart.toFixed(2)}`} stopColor={ORANGE} />
              <stop offset="1" stopColor={RED} />
            </linearGradient>
            <linearGradient id={fillId} x1="0" x2="1" y1="0" y2="0">
              <stop offset={`${(anomalyStart * 0.95).toFixed(2)}`} stopColor={TEAL} stopOpacity="0.08" />
              <stop offset={`${anomalyStart.toFixed(2)}`} stopColor={ORANGE} stopOpacity="0.12" />
              <stop offset="1" stopColor={RED} stopOpacity="0.18" />
            </linearGradient>
          </>
        ) : (
          <>
            <linearGradient id={gradId}><stop stopColor={TEAL} /></linearGradient>
            <linearGradient id={fillId}><stop stopColor={TEAL} stopOpacity="0.08" /></linearGradient>
          </>
        )}
      </defs>
      <path d={areaPath} fill={`url(#${fillId})`} />
      <path d={linePath} fill="none" stroke={`url(#${gradId})`} strokeWidth={1.5} strokeLinejoin="round" />
      <circle
        cx={points[points.length - 1].x}
        cy={points[points.length - 1].y}
        r={3}
        fill={dotColor}
      />
    </svg>
  );
}
