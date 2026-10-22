import type { SkillProgress } from "@/lib/types";

type Props = {
  skills: SkillProgress[];
  compact?: boolean;
};

export default function MasteryBars({ skills, compact = false }: Props) {
  if (skills.length === 0) {
    return <p className="muted">Spill noen runder, så bygger vi mestringsprofilen din.</p>;
  }
  return (
    <div className={compact ? "mastery-list compact" : "mastery-list"}>
      {skills.map((item) => {
        const percent = Math.round(item.mastery * 100);
        return (
          <div className="mastery-row" key={`${item.topic}-${item.skill}`}>
            <div className="mastery-copy">
              <strong>{item.skill}</strong>
              <span>Nivå {item.level} · {percent}%</span>
            </div>
            <div className="mastery-track" aria-label={`${item.skill}: ${percent} prosent mestring`}>
              <span style={{ width: `${percent}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
