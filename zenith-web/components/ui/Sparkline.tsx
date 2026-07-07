interface SparklineProps {
  data: number[];
  stroke?: string;
  fillId: string;
  className?: string;
}

function buildPaths(data: number[], width: number, height: number) {
  if (data.length < 2) {
    const y = height / 2;
    return {
      line: `M0,${y} L${width},${y}`,
      area: `M0,${y} L${width},${y} L${width},${height} L0,${height} Z`,
    };
  }

  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const step = width / (data.length - 1);

  const points = data.map((value, index) => {
    const x = index * step;
    const y = height - ((value - min) / range) * (height - 6) - 3;
    return { x, y };
  });

  const line = points
    .map(
      (point, index) =>
        `${index === 0 ? "M" : "L"}${point.x.toFixed(2)},${point.y.toFixed(2)}`,
    )
    .join(" ");

  const area = `${line} L${width},${height} L0,${height} Z`;

  return { line, area };
}

export function Sparkline({
  data,
  stroke = "var(--brand)",
  fillId,
  className = "",
}: SparklineProps) {
  const width = 120;
  const height = 32;
  const { line, area } = buildPaths(data, width, height);

  const isFlat = data.length < 2 || data.every((v) => v === 0 || v === data[0]);

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      className={`block h-8 w-full overflow-visible ${className}`}
      style={{ opacity: isFlat ? 0.15 : 0.85 }}
      aria-hidden
    >
      <defs>
        <linearGradient id={fillId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={stroke} stopOpacity={0.18} />
          <stop offset="100%" stopColor="transparent" stopOpacity={0} />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${fillId})`} />
      <path
        d={line}
        fill="none"
        stroke={stroke}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}
