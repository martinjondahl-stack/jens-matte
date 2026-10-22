import type { CSSProperties } from "react";

export default function Confetti() {
  return (
    <div className="confetti" aria-hidden="true">
      {Array.from({ length: 30 }, (_, i) => (
        <i key={i} style={{ "--i": i } as CSSProperties} />
      ))}
    </div>
  );
}
