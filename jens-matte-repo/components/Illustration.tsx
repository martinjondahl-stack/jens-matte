import type { CSSProperties, ReactNode } from "react";
import type { VisualSpec } from "@/lib/types";

type Props = {
  visual: VisualSpec;
};

const W = 360;
const H = 190;

function number(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function text(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function numbers(value: unknown): number[] {
  return Array.isArray(value) ? value.map((item) => number(item)).filter(Number.isFinite) : [];
}

function strings(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => String(item)) : [];
}

function Frame({ children, label }: { children: ReactNode; label: string }) {
  return (
    <svg className="question-visual" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label}>
      <rect x="1" y="1" width={W - 2} height={H - 2} rx="24" className="visual-bg" />
      {children}
    </svg>
  );
}

export default function Illustration({ visual }: Props) {
  const v = visual as Record<string, unknown>;
  switch (visual.type) {
    case "numberLine":
      return <NumberLine v={v} />;
    case "fractionBar":
      return <FractionBar v={v} />;
    case "fractionCompare":
      return <FractionCompare v={v} />;
    case "percentGrid":
      return <PercentGrid v={v} />;
    case "priceTag":
      return <PriceTag v={v} />;
    case "progressBar":
      return <ProgressBar v={v} />;
    case "pattern":
      return <Pattern v={v} />;
    case "functionTable":
      return <FunctionTable v={v} />;
    case "rectangle":
      return <RectangleVisual v={v} />;
    case "triangle":
      return <TriangleVisual v={v} />;
    case "circle":
      return <CircleVisual v={v} />;
    case "angles":
      return <AnglesVisual v={v} />;
    case "coordinateGrid":
      return <CoordinateGrid v={v} />;
    case "compositeL":
      return <CompositeL v={v} />;
    case "ruler":
      return <RulerVisual v={v} />;
    case "clockPair":
      return <ClockPair v={v} />;
    case "prism":
      return <PrismVisual v={v} />;
    case "mapScale":
      return <MapScale v={v} />;
    case "dataDots":
      return <DataDots v={v} />;
    case "barChart":
      return <BarChart v={v} />;
    case "probabilityBag":
      return <ProbabilityBag v={v} />;
    case "dice":
      return <DiceVisual v={v} />;
    case "receipt":
      return <Receipt v={v} />;
    case "budget":
      return <Budget v={v} />;
    case "offers":
      return <Offers v={v} />;
    case "recipe":
      return <Recipe v={v} />;
    case "tiledRectangle":
      return <TiledRectangle v={v} />;
    case "combinationGrid":
      return <CombinationGrid v={v} />;
    case "fractionTank":
      return <FractionTank v={v} />;
    default:
      return (
        <Frame label="Matematisk illustrasjon">
          <circle cx="180" cy="84" r="40" className="visual-accent" />
          <text x="180" y="94" textAnchor="middle" className="visual-big-text">?</text>
          <text x="180" y="150" textAnchor="middle" className="visual-label">Tenk med en modell</text>
        </Frame>
      );
  }
}

function NumberLine({ v }: { v: Record<string, unknown> }) {
  const min = number(v.min, -10);
  const max = number(v.max, 10);
  const range = Math.max(1, max - min);
  const x = (value: number) => 34 + ((value - min) / range) * 292;
  const ticks = Array.from({ length: 9 }, (_, i) => min + (range * i) / 8);
  const points = numbers(v.points);
  const start = typeof v.start === "number" ? v.start : undefined;
  const end = typeof v.end === "number" ? v.end : undefined;
  const legacyOpenAt = typeof v.openAt === "number" ? v.openAt : undefined;
  const boundary = typeof v.boundary === "number" ? v.boundary : legacyOpenAt;
  const direction = v.direction === "left" ? "left" : "right";
  const closed = v.closed === true;
  return (
    <Frame label="Tallinje">
      <line x1="34" y1="102" x2="326" y2="102" className="visual-line" />
      {ticks.map((tick, i) => (
        <g key={i}>
          <line x1={x(tick)} y1="94" x2={x(tick)} y2="110" className="visual-line-thin" />
          <text x={x(tick)} y="132" textAnchor="middle" className="visual-tiny">{format(tick)}</text>
        </g>
      ))}
      {points.map((point, i) => (
        <g key={`${point}-${i}`}>
          <circle cx={x(point)} cy="102" r="8" className={i === 0 ? "visual-accent" : "visual-secondary"} />
          <text x={x(point)} y="76" textAnchor="middle" className="visual-label">{format(point)}</text>
        </g>
      ))}
      {start !== undefined && end !== undefined && (
        <>
          <circle cx={x(start)} cy="102" r="7" className="visual-secondary" />
          <path d={`M ${x(start)} 74 Q ${(x(start) + x(end)) / 2} 34 ${x(end)} 74`} className="visual-arrow" />
          <circle cx={x(end)} cy="102" r="8" className="visual-accent" />
          <text x={x(start)} y="150" textAnchor="middle" className="visual-label">start {format(start)}</text>
          <text x={x(end)} y="150" textAnchor="middle" className="visual-label">slutt {format(end)}</text>
        </>
      )}
      {boundary !== undefined && (
        <>
          <line
            x1={direction === "left" ? 40 : x(boundary) + 10}
            y1="102"
            x2={direction === "left" ? x(boundary) - 10 : 320}
            y2="102"
            className="visual-accent-line"
          />
          {direction === "left" ? (
            <path d="M 40 102 l 12 -7 v 14 z" className="visual-accent" />
          ) : (
            <path d="M 320 102 l -12 -7 v 14 z" className="visual-accent" />
          )}
          <circle cx={x(boundary)} cy="102" r="8" className={closed ? "visual-accent" : "visual-open"} />
          <text x={x(boundary)} y="76" textAnchor="middle" className="visual-label">
            {closed ? "med" : "uten"} {format(boundary)}
          </text>
        </>
      )}
    </Frame>
  );
}

function FractionBar({ v }: { v: Record<string, unknown> }) {
  const denominator = Math.max(1, Math.round(number(v.denominator, 4)));
  const numerator = Math.max(0, Math.min(denominator, Math.round(number(v.numerator, 1))));
  const gap = 3;
  const totalWidth = 286;
  const cell = (totalWidth - gap * (denominator - 1)) / denominator;
  return (
    <Frame label={`Brøkmodell for ${numerator}/${denominator}`}>
      <text x="180" y="46" textAnchor="middle" className="visual-title">{text(v.label, `${numerator}/${denominator}`)}</text>
      {Array.from({ length: denominator }, (_, i) => (
        <rect
          key={i}
          x={37 + i * (cell + gap)}
          y="72"
          width={cell}
          height="62"
          rx="7"
          className={i < numerator ? "visual-accent" : "visual-empty"}
        />
      ))}
      <text x="180" y="163" textAnchor="middle" className="visual-label">{numerator} av {denominator} like deler</text>
    </Frame>
  );
}

function FractionCompare({ v }: { v: Record<string, unknown> }) {
  const fractions = strings(v.fractions).slice(0, 4);
  const barX = 82;
  const barWidth = 232;
  const rowHeight = 37;
  return (
    <Frame label="Sammenligning av brøker">
      {fractions.map((fraction, i) => {
        const [nRaw, dRaw] = fraction.split("/");
        const numerator = Number(nRaw) || 0;
        const denominator = Math.max(1, Number(dRaw) || 1);
        const ratio = Math.max(0, Math.min(1, numerator / denominator));
        const y = 22 + i * rowHeight;
        return (
          <g key={`${fraction}-${i}`}>
            <text x="52" y={y + 18} textAnchor="middle" className="visual-label">{fraction}</text>
            <rect x={barX} y={y} width={barWidth} height="24" rx="7" className="visual-empty" />
            <rect x={barX} y={y} width={barWidth * ratio} height="24" rx="7" className="visual-accent" />
            {denominator <= 16 && Array.from({ length: denominator - 1 }, (_, j) => (
              <line
                key={j}
                x1={barX + ((j + 1) / denominator) * barWidth}
                y1={y + 1}
                x2={barX + ((j + 1) / denominator) * barWidth}
                y2={y + 23}
                className="visual-fraction-mark"
              />
            ))}
          </g>
        );
      })}
    </Frame>
  );
}

function PercentGrid({ v }: { v: Record<string, unknown> }) {
  const percent = Math.max(0, Math.min(100, number(v.percent, 50)));
  const filled = Math.round(percent);
  return (
    <Frame label={`${format(percent)} prosent i hundredelrutenett`}>
      <g transform="translate(91 22)">
        {Array.from({ length: 100 }, (_, i) => (
          <rect key={i} x={(i % 10) * 18} y={Math.floor(i / 10) * 14} width="15" height="11" rx="2"
            className={i < filled ? "visual-accent" : "visual-empty"} />
        ))}
      </g>
      <text x="180" y="178" textAnchor="middle" className="visual-title">{format(percent)} %</text>
    </Frame>
  );
}

function PriceTag({ v }: { v: Record<string, unknown> }) {
  return (
    <Frame label="Prislapp med rabatt">
      <path d="M82 48 H244 L292 95 L244 142 H82 Z" className="visual-secondary" />
      <circle cx="257" cy="95" r="9" className="visual-bg-solid" />
      <text x="165" y="90" textAnchor="middle" className="visual-big-text">{format(number(v.price))} kr</text>
      <text x="165" y="119" textAnchor="middle" className="visual-label">før rabatt</text>
      <circle cx="282" cy="54" r="33" className="visual-accent" />
      <text x="282" y="61" textAnchor="middle" className="visual-dark-text">−{format(number(v.percent))}%</text>
    </Frame>
  );
}

function ProgressBar({ v }: { v: Record<string, unknown> }) {
  const percent = Math.max(0, Math.min(100, number(v.percent, 50)));
  return (
    <Frame label="Prosentstolpe">
      <text x="180" y="54" textAnchor="middle" className="visual-title">{text(v.label, `${format(percent)} %`)}</text>
      <rect x="42" y="82" width="276" height="44" rx="22" className="visual-empty" />
      <rect x="42" y="82" width={276 * percent / 100} height="44" rx="22" className="visual-accent" />
      <text x="180" y="158" textAnchor="middle" className="visual-label">{format(percent)} % av hele</text>
    </Frame>
  );
}

function Pattern({ v }: { v: Record<string, unknown> }) {
  const values = numbers(v.values).slice(0, 6);
  return (
    <Frame label="Tallmønster">
      {values.map((value, i) => (
        <g key={i}>
          <circle cx={48 + i * 61} cy="92" r="25" className={i % 2 ? "visual-secondary" : "visual-accent"} />
          <text x={48 + i * 61} y="100" textAnchor="middle" className="visual-dark-text">{format(value)}</text>
          {i < values.length - 1 && <path d={`M ${76 + i * 61} 92 H ${91 + i * 61}`} className="visual-arrow" />}
        </g>
      ))}
      <circle cx="324" cy="92" r="25" className="visual-empty" />
      <text x="324" y="100" textAnchor="middle" className="visual-title">?</text>
    </Frame>
  );
}

function FunctionTable({ v }: { v: Record<string, unknown> }) {
  const a = number(v.a, 2);
  const b = number(v.b, 3);
  const x = number(v.x, 4);
  return (
    <Frame label="Funksjonstabell">
      <text x="180" y="36" textAnchor="middle" className="visual-title">y = {format(a)}x + {format(b)}</text>
      <rect x="76" y="58" width="208" height="88" rx="12" className="visual-empty" />
      <line x1="180" y1="58" x2="180" y2="146" className="visual-line-thin" />
      <line x1="76" y1="102" x2="284" y2="102" className="visual-line-thin" />
      <text x="128" y="87" textAnchor="middle" className="visual-label">x</text>
      <text x="232" y="87" textAnchor="middle" className="visual-label">y</text>
      <text x="128" y="131" textAnchor="middle" className="visual-title">{format(x)}</text>
      <text x="232" y="131" textAnchor="middle" className="visual-title">?</text>
    </Frame>
  );
}

function RectangleVisual({ v }: { v: Record<string, unknown> }) {
  return (
    <Frame label="Rektangel med mål">
      <rect x="75" y="48" width="210" height="95" rx="4" className="visual-shape" />
      <text x="180" y="171" textAnchor="middle" className="visual-label">{format(number(v.width))} {text(v.unit, "cm")}</text>
      <text x="52" y="102" textAnchor="middle" transform="rotate(-90 52 102)" className="visual-label">{format(number(v.height))} {text(v.unit, "cm")}</text>
    </Frame>
  );
}

function TriangleVisual({ v }: { v: Record<string, unknown> }) {
  return (
    <Frame label="Trekant med grunnlinje og høyde">
      <polygon points="64,143 296,143 222,40" className="visual-shape" />
      <line x1="222" y1="40" x2="222" y2="143" className="visual-dashed" />
      <text x="180" y="170" textAnchor="middle" className="visual-label">grunnlinje {format(number(v.base))} {text(v.unit, "cm")}</text>
      <text x="242" y="94" className="visual-label">h = {format(number(v.height))}</text>
    </Frame>
  );
}

function CircleVisual({ v }: { v: Record<string, unknown> }) {
  const showDiameter = text(v.show) === "diameter";
  return (
    <Frame label="Sirkel med radius eller diameter">
      <circle cx="180" cy="94" r="62" className="visual-shape" />
      <line x1={showDiameter ? 118 : 180} y1="94" x2="242" y2="94" className="visual-accent-line" />
      <circle cx="180" cy="94" r="4" className="visual-accent" />
      <text x="180" y="174" textAnchor="middle" className="visual-label">
        {showDiameter ? "diameter" : "radius"} = {format(number(v.radius) * (showDiameter ? 2 : 1))}
      </text>
    </Frame>
  );
}

function AnglesVisual({ v }: { v: Record<string, unknown> }) {
  const values = numbers(v.angles);
  if (Boolean(v.triangle)) {
    return (
      <Frame label="Trekant med vinkler">
        <polygon points="65,145 295,145 190,38" className="visual-shape" />
        <text x="92" y="134" className="visual-label">{format(values[0])}°</text>
        <text x="250" y="134" className="visual-label">{format(values[1])}°</text>
        <text x="187" y="70" textAnchor="middle" className="visual-title">?</text>
      </Frame>
    );
  }
  return (
    <Frame label="Vinkler på en rett linje">
      <line x1="48" y1="137" x2="312" y2="137" className="visual-line" />
      <line x1="180" y1="137" x2="246" y2="48" className="visual-line" />
      <path d="M 205 137 A 35 35 0 0 0 192 109" className="visual-accent-line" />
      <text x="230" y="113" className="visual-label">{format(values[0])}°</text>
      <text x="120" y="114" className="visual-title">?</text>
    </Frame>
  );
}

function CoordinateGrid({ v }: { v: Record<string, unknown> }) {
  const point = numbers(v.point);
  const px = 180 + (point[0] ?? 0) * 15;
  const py = 95 - (point[1] ?? 0) * 15;
  return (
    <Frame label="Koordinatsystem">
      {Array.from({ length: 17 }, (_, i) => (
        <g key={i}>
          <line x1={60 + i * 15} y1="20" x2={60 + i * 15} y2="170" className="visual-grid" />
          {i < 11 && <line x1="60" y1={20 + i * 15} x2="300" y2={20 + i * 15} className="visual-grid" />}
        </g>
      ))}
      <line x1="60" y1="95" x2="300" y2="95" className="visual-line" />
      <line x1="180" y1="20" x2="180" y2="170" className="visual-line" />
      <circle cx={px} cy={py} r="7" className="visual-accent" />
      <text x={px + 12} y={py - 9} className="visual-label">({point[0]}, {point[1]})</text>
    </Frame>
  );
}

function CompositeL({ v }: { v: Record<string, unknown> }) {
  const outer = numbers(v.outer);
  const cutout = numbers(v.cutout);
  return (
    <Frame label="L-formet sammensatt figur">
      <path d="M72 38 H288 V142 H190 V91 H72 Z" className="visual-shape" />
      <rect x="190" y="38" width="98" height="53" className="visual-cutout" />
      <text x="180" y="174" textAnchor="middle" className="visual-label">ytterkant {outer[0]} × {outer[1]} · utsnitt {cutout[0]} × {cutout[1]}</text>
    </Frame>
  );
}

function RulerVisual({ v }: { v: Record<string, unknown> }) {
  return (
    <Frame label="Måleenheter">
      <rect x="42" y="72" width="276" height="54" rx="8" className="visual-secondary" />
      {Array.from({ length: 21 }, (_, i) => (
        <line key={i} x1={48 + i * 13.2} y1="72" x2={48 + i * 13.2} y2={i % 5 === 0 ? 101 : 90} className="visual-dark-line" />
      ))}
      <text x="92" y="158" textAnchor="middle" className="visual-title">{format(number(v.value))} {text(v.from)}</text>
      <path d="M 144 151 H 216" className="visual-arrow" />
      <text x="268" y="158" textAnchor="middle" className="visual-title">? {text(v.to)}</text>
    </Frame>
  );
}

function ClockPair({ v }: { v: Record<string, unknown> }) {
  const start = numbers(v.start);
  const end = numbers(v.end);
  return (
    <Frame label="To klokkeslett">
      <Clock cx={105} cy={92} hour={start[0] ?? 0} minute={start[1] ?? 0} />
      <Clock cx={255} cy={92} hour={end[0] ?? 0} minute={end[1] ?? 0} />
      <path d="M 160 92 H 200" className="visual-arrow" />
      <text x="105" y="174" textAnchor="middle" className="visual-label">{pad(start[0])}:{pad(start[1])}</text>
      <text x="255" y="174" textAnchor="middle" className="visual-label">{pad(end[0])}:{pad(end[1])}</text>
    </Frame>
  );
}

function Clock({ cx, cy, hour, minute }: { cx: number; cy: number; hour: number; minute: number }) {
  const minuteAngle = (minute / 60) * Math.PI * 2 - Math.PI / 2;
  const hourAngle = (((hour % 12) + minute / 60) / 12) * Math.PI * 2 - Math.PI / 2;
  return (
    <g>
      <circle cx={cx} cy={cy} r="53" className="visual-shape" />
      {Array.from({ length: 12 }, (_, i) => {
        const angle = (i / 12) * Math.PI * 2 - Math.PI / 2;
        return <circle key={i} cx={cx + Math.cos(angle) * 43} cy={cy + Math.sin(angle) * 43} r="2" className="visual-accent" />;
      })}
      <line x1={cx} y1={cy} x2={cx + Math.cos(hourAngle) * 28} y2={cy + Math.sin(hourAngle) * 28} className="visual-line" />
      <line x1={cx} y1={cy} x2={cx + Math.cos(minuteAngle) * 39} y2={cy + Math.sin(minuteAngle) * 39} className="visual-accent-line" />
      <circle cx={cx} cy={cy} r="4" className="visual-accent" />
    </g>
  );
}

function PrismVisual({ v }: { v: Record<string, unknown> }) {
  return (
    <Frame label="Rett prisme med mål">
      <rect x="86" y="62" width="178" height="85" className="visual-shape" />
      <path d="M86 62 L127 34 H305 L264 62 M264 62 L305 34 V119 L264 147" className="visual-line" />
      <text x="176" y="173" textAnchor="middle" className="visual-label">l={format(number(v.length))}</text>
      <text x="286" y="153" className="visual-label">b={format(number(v.width))}</text>
      <text x="65" y="107" className="visual-label">h={format(number(v.height))}</text>
    </Frame>
  );
}

function MapScale({ v }: { v: Record<string, unknown> }) {
  return (
    <Frame label="Kart og målestokk">
      <path d="M54 132 Q95 35 142 90 T236 76 T307 122" className="visual-route" />
      <circle cx="54" cy="132" r="7" className="visual-accent" />
      <circle cx="307" cy="122" r="7" className="visual-secondary" />
      <text x="180" y="37" textAnchor="middle" className="visual-title">{format(number(v.cm))} cm på kartet</text>
      <rect x="86" y="151" width="188" height="25" rx="8" className="visual-empty" />
      <text x="180" y="169" textAnchor="middle" className="visual-label">målestokk 1:{format(number(v.scale))}</text>
    </Frame>
  );
}

function DataDots({ v }: { v: Record<string, unknown> }) {
  const values = numbers(v.values);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = Math.max(1, max - min);
  const stack = new Map<number, number>();
  return (
    <Frame label="Prikkdiagram">
      <line x1="40" y1="135" x2="320" y2="135" className="visual-line" />
      {values.map((value, i) => {
        const count = stack.get(value) ?? 0;
        stack.set(value, count + 1);
        const x = 50 + ((value - min) / range) * 260;
        return <circle key={i} cx={x} cy={118 - count * 18} r="7" className="visual-accent" />;
      })}
      {[min, (min + max) / 2, max].map((value, i) => (
        <text key={i} x={50 + ((value - min) / range) * 260} y="160" textAnchor="middle" className="visual-label">{format(value)}</text>
      ))}
    </Frame>
  );
}

function BarChart({ v }: { v: Record<string, unknown> }) {
  const labels = strings(v.labels);
  const values = numbers(v.values);
  const max = Math.max(1, ...values);
  return (
    <Frame label="Søylediagram">
      <line x1="45" y1="148" x2="320" y2="148" className="visual-line" />
      {values.map((value, i) => {
        const height = (value / max) * 100;
        return (
          <g key={i}>
            <rect x={66 + i * 63} y={148 - height} width="36" height={height} rx="5" className={i % 2 ? "visual-secondary" : "visual-accent"} />
            <text x={84 + i * 63} y={139 - height} textAnchor="middle" className="visual-label">{format(value)}</text>
            <text x={84 + i * 63} y="170" textAnchor="middle" className="visual-tiny">{labels[i]}</text>
          </g>
        );
      })}
    </Frame>
  );
}

function ProbabilityBag({ v }: { v: Record<string, unknown> }) {
  const red = Math.round(number(v.red));
  const blue = Math.round(number(v.blue));
  const total = red + blue;
  const redLabel = red === 1 ? "1 rød" : `${red} røde`;
  const blueLabel = blue === 1 ? "1 blå" : `${blue} blå`;
  return (
    <Frame label="Pose med kuler">
      <path d="M105 49 Q180 21 255 49 L280 145 Q180 176 80 145 Z" className="visual-bag" />
      {Array.from({ length: Math.min(15, total) }, (_, i) => {
        const col = i % 5;
        const row = Math.floor(i / 5);
        return <circle key={i} cx={116 + col * 32 + (row % 2) * 8} cy={83 + row * 29} r="10" className={i < red ? "visual-accent" : "visual-secondary"} />;
      })}
      <text x="180" y="178" textAnchor="middle" className="visual-label">{redLabel} · {blueLabel}</text>
    </Frame>
  );
}

function DiceVisual({ v }: { v: Record<string, unknown> }) {
  const target = Math.max(2, Math.min(12, Math.round(number(v.target, 7))));
  let first = Math.floor(target / 2);
  let second = target - first;
  if (second > 6) {
    second = 6;
    first = target - second;
  }
  return (
    <Frame label={`To terninger som til sammen viser ${target}`}>
      <Die x={83} y={50} value={first} />
      <Die x={207} y={50} value={second} />
      <text x="180" y="166" textAnchor="middle" className="visual-title">ett eksempel: {first} + {second} = {target}</text>
    </Frame>
  );
}

function Die({ x, y, value }: { x: number; y: number; value: number }) {
  const dots: Record<number, Array<[number, number]>> = {
    1: [[36, 36]],
    2: [[18, 18], [54, 54]],
    3: [[18, 18], [36, 36], [54, 54]],
    4: [[18, 18], [54, 18], [18, 54], [54, 54]],
    5: [[18, 18], [54, 18], [36, 36], [18, 54], [54, 54]],
    6: [[18, 18], [54, 18], [18, 36], [54, 36], [18, 54], [54, 54]],
  };
  return (
    <g>
      <rect x={x} y={y} width="72" height="72" rx="14" className="visual-shape" />
      {(dots[value] ?? dots[1]).map(([dx, dy], i) => <circle key={i} cx={x + dx} cy={y + dy} r="5" className="visual-accent" />)}
    </g>
  );
}

function Receipt({ v }: { v: Record<string, unknown> }) {
  return (
    <Frame label="Kvittering">
      <path d="M96 27 H264 V162 L250 151 L236 162 L222 151 L208 162 L194 151 L180 162 L166 151 L152 162 L138 151 L124 162 L110 151 L96 162 Z" className="visual-paper" />
      <text x="180" y="58" textAnchor="middle" className="visual-title">KVITTERING</text>
      <text x="118" y="92" className="visual-label">{format(number(v.quantity))} × {format(number(v.unitPrice))} kr</text>
      <line x1="118" y1="105" x2="242" y2="105" className="visual-line-thin" />
      <text x="118" y="130" className="visual-label">Betalt</text>
      <text x="242" y="130" textAnchor="end" className="visual-label">{format(number(v.paid))} kr</text>
    </Frame>
  );
}

function Budget({ v }: { v: Record<string, unknown> }) {
  const income = number(v.income, 1);
  const expenses = numbers(v.expenses);
  const total = expenses.reduce((a, b) => a + b, 0);
  const max = Math.max(income, total);
  return (
    <Frame label="Budsjett">
      <text x="180" y="40" textAnchor="middle" className="visual-title">Budsjett</text>
      <text x="52" y="83" className="visual-label">Penger inn</text>
      <rect x="128" y="65" width={(income / max) * 182} height="25" rx="8" className="visual-accent" />
      <text x="52" y="124" className="visual-label">Utgifter</text>
      <rect x="128" y="106" width={(total / max) * 182} height="25" rx="8" className="visual-secondary" />
      <text x="180" y="165" textAnchor="middle" className="visual-label">{format(income)} kr − {format(total)} kr</text>
    </Frame>
  );
}

function Offers({ v }: { v: Record<string, unknown> }) {
  const a = (v.a ?? {}) as Record<string, unknown>;
  const b = (v.b ?? {}) as Record<string, unknown>;
  return (
    <Frame label="To pristilbud">
      <OfferCard x={38} title="Tilbud A" qty={number(a.qty)} price={number(a.price)} />
      <OfferCard x={198} title="Tilbud B" qty={number(b.qty)} price={number(b.price)} />
    </Frame>
  );
}

function OfferCard({ x, title, qty, price }: { x: number; title: string; qty: number; price: number }) {
  return (
    <g>
      <rect x={x} y="30" width="124" height="128" rx="18" className="visual-empty" />
      <text x={x + 62} y="60" textAnchor="middle" className="visual-title">{title}</text>
      <text x={x + 62} y="102" textAnchor="middle" className="visual-big-text">{format(qty)} stk.</text>
      <text x={x + 62} y="134" textAnchor="middle" className="visual-label">{format(price)} kr</text>
    </g>
  );
}

function Recipe({ v }: { v: Record<string, unknown> }) {
  return (
    <Frame label="Oppskrift som skal skaleres">
      <path d="M65 131 Q84 58 132 58 H228 Q276 58 295 131 Z" className="visual-bowl" />
      <path d="M110 62 Q180 20 250 62" className="visual-route" />
      <text x="180" y="97" textAnchor="middle" className="visual-title">{format(number(v.amount))} {text(v.unit)}</text>
      <text x="180" y="164" textAnchor="middle" className="visual-label">{format(number(v.oldServings))} porsjoner → {format(number(v.newServings))} porsjoner</text>
    </Frame>
  );
}

function TiledRectangle({ v }: { v: Record<string, unknown> }) {
  const cols = Math.max(2, Math.min(10, Math.round(number(v.length) / Math.max(1, number(v.tile)))));
  const rows = Math.max(2, Math.min(6, Math.round(number(v.width) / Math.max(1, number(v.tile)))));
  return (
    <Frame label="Gulv med kvadratiske fliser">
      <g transform="translate(66 31)">
        {Array.from({ length: rows * cols }, (_, i) => (
          <rect key={i} x={(i % cols) * (228 / cols)} y={Math.floor(i / cols) * (108 / rows)} width={228 / cols - 2} height={108 / rows - 2}
            className={(i + Math.floor(i / cols)) % 2 ? "visual-empty" : "visual-secondary-soft"} />
        ))}
      </g>
      <text x="180" y="169" textAnchor="middle" className="visual-label">{format(number(v.length))} m × {format(number(v.width))} m · flis {format(number(v.tile))} m</text>
    </Frame>
  );
}

function CombinationGrid({ v }: { v: Record<string, unknown> }) {
  const rows = Math.max(1, Math.min(8, Math.round(number(v.rows, 3))));
  const cols = Math.max(1, Math.min(8, Math.round(number(v.cols, 4))));
  return (
    <Frame label="Rutenett med kombinasjoner">
      <g transform="translate(80 30)">
        {Array.from({ length: rows * cols }, (_, i) => (
          <g key={i} transform={`translate(${(i % cols) * (200 / cols)}, ${Math.floor(i / cols) * (120 / rows)})`}>
            <circle cx="8" cy="8" r="7" className={Math.floor(i / cols) % 2 ? "visual-secondary" : "visual-accent"} />
            <rect x="18" y="2" width="18" height="12" rx="4" className={i % cols % 2 ? "visual-secondary" : "visual-accent"} />
          </g>
        ))}
      </g>
      <text x="180" y="174" textAnchor="middle" className="visual-label">{rows} × {cols} mulige kombinasjoner</text>
    </Frame>
  );
}

function FractionTank({ v }: { v: Record<string, unknown> }) {
  const parseFraction = (value: unknown) => {
    const [n, d] = text(value, "1/2").split("/").map(Number);
    return d ? n / d : 0.5;
  };
  const start = parseFraction(v.start);
  const end = parseFraction(v.end);
  return (
    <Frame label="Beholder som fylles">
      <Tank x={62} fraction={start} label={text(v.start)} />
      <path d="M 147 93 H 213" className="visual-arrow" />
      <text x="180" y="72" textAnchor="middle" className="visual-label">+ {format(number(v.added))} {text(v.unit)}</text>
      <Tank x={226} fraction={end} label={text(v.end)} />
    </Frame>
  );
}

function Tank({ x, fraction, label }: { x: number; fraction: number; label: string }) {
  const h = 104;
  const fill = Math.max(0, Math.min(1, fraction)) * h;
  return (
    <g>
      <rect x={x} y="43" width="72" height={h} rx="10" className="visual-shape" />
      <path d={`M ${x + 4} ${147 - fill} H ${x + 68} V 143 H ${x + 4} Z`} className="visual-secondary" />
      <text x={x + 36} y="172" textAnchor="middle" className="visual-label">{label}</text>
    </g>
  );
}

function format(value: number): string {
  if (!Number.isFinite(value)) return "";
  return Number.isInteger(value) ? String(value) : String(Number(value.toFixed(2))).replace(".", ",");
}

function pad(value: number | undefined): string {
  return String(Math.round(value ?? 0)).padStart(2, "0");
}

export const illustrationPalette: CSSProperties = {};
