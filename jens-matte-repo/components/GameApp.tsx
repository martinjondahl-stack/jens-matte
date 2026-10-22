"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import Illustration from "@/components/Illustration";
import MasteryBars from "@/components/MasteryBars";
import Confetti from "@/components/Confetti";
import { selectAdaptiveRound } from "@/lib/adaptive";
import { questionById, questions, topics } from "@/lib/questions";
import { cleanName, createLocalProfile, scoreAttempts, xpLevel } from "@/lib/progress";
import { clearProfile, loadProfile, loadSoundPreference, saveProfile, saveSoundPreference } from "@/lib/storage";
import { playCorrect, playLevelUp, playWrong } from "@/lib/sound";
import type { AnswerOption, Attempt, PlayerProfile, Question, RoundSummary, SkillProgress } from "@/lib/types";

type Screen = "welcome" | "home" | "playing" | "result" | "profile";
type SyncState = "idle" | "saving" | "saved" | "local" | "error";

const TOPIC_ICONS: Record<string, string> = {
  "Tall og regnearter": "➕",
  "Brøk": "◔",
  "Desimaltall": "0,5",
  "Prosent": "%",
  "Algebra og mønster": "x",
  "Geometri": "△",
  "Måling": "📏",
  "Statistikk og sannsynlighet": "▥",
  "Økonomi": "kr",
  "Problemløsing": "🧠",
};

export default function GameApp() {
  const [profile, setProfile] = useState<PlayerProfile | null>(null);
  const [screen, setScreen] = useState<Screen>("welcome");
  const [round, setRound] = useState<Question[]>([]);
  const [questionIndex, setQuestionIndex] = useState(0);
  const [attempts, setAttempts] = useState<Attempt[]>([]);
  const [selectedOption, setSelectedOption] = useState<AnswerOption["id"] | null>(null);
  const [showSteps, setShowSteps] = useState(false);
  const [usedHint, setUsedHint] = useState(false);
  const [currentStreak, setCurrentStreak] = useState(0);
  const [bestRoundStreak, setBestRoundStreak] = useState(0);
  const [summary, setSummary] = useState<RoundSummary | null>(null);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [syncState, setSyncState] = useState<SyncState>("idle");
  const [notice, setNotice] = useState<string>("");
  const [newCode, setNewCode] = useState<string | null>(null);
  const questionStartedAt = useRef(Date.now());

  useEffect(() => {
    const stored = loadProfile();
    setSoundEnabled(loadSoundPreference());
    if (stored) {
      setProfile(stored);
      setScreen("home");
      if (stored.token) void refreshCloudProfile(stored);
    }
  }, []);

  const refreshCloudProfile = useCallback(async (stored: PlayerProfile) => {
    if (!stored.token) return;
    try {
      const response = await fetch("/api/profile/sync", {
        headers: { Authorization: `Bearer ${stored.token}` },
        cache: "no-store",
      });
      if (!response.ok) return;
      const data = (await response.json()) as { profile: PlayerProfile };
      const refreshed = { ...data.profile, token: stored.token, playerCode: stored.playerCode };
      setProfile(refreshed);
      saveProfile(refreshed);
      setSyncState("saved");
    } catch {
      setSyncState("local");
    }
  }, []);

  const currentQuestion = round[questionIndex];
  const selected = currentQuestion?.options.find((option) => option.id === selectedOption);
  const isCorrect = Boolean(currentQuestion && selectedOption === currentQuestion.correctOption);

  const orderedSkills = useMemo(() => {
    if (!profile) return [];
    return Object.values(profile.skillProgress)
      .sort((a, b) => a.mastery - b.mastery || b.attempts - a.attempts);
  }, [profile]);

  const toggleSound = () => {
    const next = !soundEnabled;
    setSoundEnabled(next);
    saveSoundPreference(next);
  };

  async function createPlayer(name: string): Promise<void> {
    const cleaned = cleanName(name);
    setNotice("");
    setSyncState("saving");
    try {
      const response = await fetch("/api/profile/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: cleaned }),
      });
      const data = (await response.json()) as { profile?: PlayerProfile; playerCode?: string; error?: string };
      if (!response.ok || !data.profile) throw new Error(data.error || "Skyprofilen er ikke tilgjengelig.");
      const next = { ...data.profile, token: data.profile.token, playerCode: data.playerCode, mode: "synced" as const };
      setProfile(next);
      saveProfile(next);
      setNewCode(data.playerCode ?? null);
      setSyncState("saved");
      setScreen("home");
    } catch {
      const local = createLocalProfile(cleaned);
      setProfile(local);
      saveProfile(local);
      setSyncState("local");
      setNotice("Spillet startet lokalt. Progresjonen lagres på denne enheten til databasen er koblet til.");
      setScreen("home");
    }
  }

  async function restorePlayer(name: string, code: string): Promise<void> {
    setNotice("");
    setSyncState("saving");
    try {
      const response = await fetch("/api/profile/restore", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, code }),
      });
      const data = (await response.json()) as { profile?: PlayerProfile; error?: string };
      if (!response.ok || !data.profile) throw new Error(data.error || "Fant ikke spilleren.");
      const normalizedCode = code.toUpperCase().replace(/[^A-Z0-9]/g, "");
      const playerCode = normalizedCode.length === 8
        ? `${normalizedCode.slice(0, 4)}-${normalizedCode.slice(4)}`
        : code.toUpperCase();
      const next = { ...data.profile, token: data.profile.token, playerCode, mode: "synced" as const };
      setProfile(next);
      saveProfile(next);
      setSyncState("saved");
      setScreen("home");
    } catch (error) {
      setSyncState("error");
      setNotice(error instanceof Error ? error.message : "Kunne ikke hente spilleren.");
    }
  }

  function startRound(topic?: string) {
    if (!profile) return;
    const selectedQuestions = selectAdaptiveRound(questions, profile, {
      topic,
      size: 10,
      seed: Date.now(),
    });
    setRound(selectedQuestions);
    setQuestionIndex(0);
    setAttempts([]);
    setSelectedOption(null);
    setShowSteps(false);
    setUsedHint(false);
    setCurrentStreak(0);
    setBestRoundStreak(0);
    setSummary(null);
    setSyncState(profile.mode === "synced" ? "idle" : "local");
    questionStartedAt.current = Date.now();
    setScreen("playing");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function chooseAnswer(optionId: AnswerOption["id"]) {
    if (!currentQuestion || selectedOption) return;
    const correct = optionId === currentQuestion.correctOption;
    const nextStreak = correct ? currentStreak + 1 : 0;
    setSelectedOption(optionId);
    setCurrentStreak(nextStreak);
    setBestRoundStreak((value) => Math.max(value, nextStreak));
    setAttempts((items) => [
      ...items,
      {
        questionId: currentQuestion.id,
        selectedOption: optionId,
        usedHint,
        responseMs: Date.now() - questionStartedAt.current,
      },
    ]);
    if (soundEnabled) {
      if (correct) playCorrect();
      else playWrong();
    }
  }

  async function nextQuestion() {
    if (!selectedOption) return;
    if (questionIndex < round.length - 1) {
      setQuestionIndex((value) => value + 1);
      setSelectedOption(null);
      setShowSteps(false);
      setUsedHint(false);
      questionStartedAt.current = Date.now();
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    await finishRound(attempts);
  }

  async function finishRound(finalAttempts: Attempt[]) {
    if (!profile) return;
    const beforeLevel = profile.overallLevel;
    const localResult = scoreAttempts(profile, finalAttempts, questionById);
    const locallySaved = { ...localResult.profile, token: profile.token, playerCode: profile.playerCode, mode: profile.mode };
    setProfile(locallySaved);
    saveProfile(locallySaved);
    setSummary(localResult.summary);
    setScreen("result");
    setSyncState(profile.mode === "synced" ? "saving" : "local");
    window.scrollTo({ top: 0, behavior: "smooth" });

    if (locallySaved.overallLevel > beforeLevel && soundEnabled) playLevelUp();
    if (!profile.token) return;

    try {
      const response = await fetch("/api/round/submit", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${profile.token}`,
        },
        body: JSON.stringify({ attempts: finalAttempts }),
      });
      const data = (await response.json()) as { profile?: PlayerProfile; summary?: RoundSummary; error?: string };
      if (!response.ok || !data.profile || !data.summary) throw new Error(data.error || "Lagring mislyktes.");
      const cloud = { ...data.profile, token: profile.token, playerCode: profile.playerCode, mode: "synced" as const };
      setProfile(cloud);
      setSummary(data.summary);
      saveProfile(cloud);
      setSyncState("saved");
    } catch {
      setSyncState("error");
    }
  }

  function logOut() {
    clearProfile();
    setProfile(null);
    setRound([]);
    setAttempts([]);
    setSummary(null);
    setNotice("");
    setNewCode(null);
    setScreen("welcome");
  }

  async function deletePlayer() {
    if (!profile) return;
    const confirmed = window.confirm(`Slette profilen til ${profile.name} og all lagret progresjon?`);
    if (!confirmed) return;
    if (profile.token) {
      setSyncState("saving");
      try {
        const response = await fetch("/api/profile/delete", {
          method: "DELETE",
          headers: { Authorization: `Bearer ${profile.token}` },
        });
        if (!response.ok) {
          const data = (await response.json().catch(() => ({}))) as { error?: string };
          throw new Error(data.error || "Kunne ikke slette skyprofilen.");
        }
      } catch (error) {
        setSyncState("error");
        setNotice(error instanceof Error ? error.message : "Kunne ikke slette skyprofilen.");
        return;
      }
    }
    logOut();
  }

  useEffect(() => {
    if (screen !== "playing" || newCode) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      const target = event.target;
      if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement) return;
      if (!selectedOption) {
        const keys: Record<string, AnswerOption["id"]> = {
          a: "A", "1": "A", b: "B", "2": "B", c: "C", "3": "C", d: "D", "4": "D",
        };
        const optionId = keys[event.key.toLowerCase()];
        if (optionId) {
          event.preventDefault();
          chooseAnswer(optionId);
        }
      } else if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        void nextQuestion();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [screen, newCode, selectedOption, currentQuestion, questionIndex, attempts]);

  if (!profile || screen === "welcome") {
    return <Welcome onCreate={createPlayer} onRestore={restorePlayer} busy={syncState === "saving"} notice={notice} />;
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <button className="brand-button" onClick={() => setScreen("home")} aria-label="Gå til forsiden">
          <span className="brand-mark">JM</span>
          <span><strong>JENS MATTE</strong><small>5.–7.</small></span>
        </button>
        <div className="top-actions">
          <button className="icon-button" onClick={toggleSound} aria-label={soundEnabled ? "Slå av lyd" : "Slå på lyd"}>
            {soundEnabled ? "🔊" : "🔇"}
          </button>
          <button className="profile-pill" onClick={() => setScreen("profile")}>
            <span>{profile.name.slice(0, 1).toUpperCase()}</span>
            <strong>{profile.name}</strong>
          </button>
        </div>
      </header>

      {notice && <div className="notice" role="status">{notice}</div>}
      {newCode && <PlayerCodeModal code={newCode} onClose={() => setNewCode(null)} />}

      {screen === "home" && (
        <Home
          profile={profile}
          skills={orderedSkills}
          onStart={startRound}
          syncState={syncState}
        />
      )}

      {screen === "playing" && currentQuestion && (
        <section className="game-screen">
          <div className="game-status">
            <button className="text-button" onClick={() => setScreen("home")}>Avslutt</button>
            <div className="round-progress" aria-label={`Oppgave ${questionIndex + 1} av ${round.length}`}>
              <span style={{ width: `${((questionIndex + 1) / round.length) * 100}%` }} />
            </div>
            <div className="streak-chip">🔥 {currentStreak}</div>
          </div>

          <article className={`question-card ${currentQuestion.type === "challenge" ? "challenge" : ""}`}>
            <div className="question-meta">
              <span>{currentQuestion.type === "challenge" ? "🧠 Utfordring" : currentQuestion.topic}</span>
              <span>Nivå {currentQuestion.level}</span>
            </div>
            <h1>{currentQuestion.prompt}</h1>
            {currentQuestion.visual && <Illustration visual={currentQuestion.visual} />}

            {!selectedOption && (
              <button className="hint-button" onClick={() => setUsedHint(true)} disabled={usedHint}>
                {usedHint ? `💡 ${currentQuestion.hint}` : "💡 Vis et hint"}
              </button>
            )}

            <div className="answer-grid" role="group" aria-label="Svaralternativer">
              {currentQuestion.options.map((option) => {
                const state = selectedOption
                  ? option.id === currentQuestion.correctOption
                    ? "correct"
                    : option.id === selectedOption
                      ? "wrong"
                      : "dimmed"
                  : "";
                return (
                  <button
                    key={option.id}
                    className={`answer-button ${state}`}
                    onClick={() => chooseAnswer(option.id)}
                    disabled={Boolean(selectedOption)}
                  >
                    <span>{option.id}</span>
                    <strong>{option.text}</strong>
                  </button>
                );
              })}
            </div>
            {!selectedOption && <p className="keyboard-help">På Mac kan du bruke A–D eller tastene 1–4.</p>}

            {selectedOption && (
              <div className={`feedback-panel ${isCorrect ? "correct" : "wrong"}`} aria-live="polite">
                <div className="feedback-heading">
                  <span>{isCorrect ? "✓" : "↗"}</span>
                  <div>
                    <strong>{isCorrect ? "Riktig!" : "Ikke helt – se på dette"}</strong>
                    <p>{isCorrect ? currentQuestion.explanation.summary : selected?.feedback}</p>
                  </div>
                </div>
                {!isCorrect && (
                  <button className="steps-toggle" onClick={() => setShowSteps((value) => !value)}>
                    {showSteps ? "Skjul steg" : "Vis steg for steg"}
                  </button>
                )}
                {(isCorrect || showSteps) && (
                  <ol className="explanation-steps">
                    {currentQuestion.explanation.steps.map((step) => <li key={step}>{step}</li>)}
                  </ol>
                )}
                <button className="primary-button next-button" onClick={nextQuestion}>
                  {questionIndex === round.length - 1 ? "Se resultat" : "Neste oppgave"}
                </button>
              </div>
            )}
          </article>
        </section>
      )}

      {screen === "result" && summary && (
        <ResultScreen
          profile={profile}
          summary={summary}
          syncState={syncState}
          onAgain={() => startRound()}
          onHome={() => setScreen("home")}
        />
      )}

      {screen === "profile" && (
        <ProfileScreen
          profile={profile}
          skills={orderedSkills}
          syncState={syncState}
          onBack={() => setScreen("home")}
          onLogOut={logOut}
          onDelete={deletePlayer}
        />
      )}
    </main>
  );
}

function Welcome({
  onCreate,
  onRestore,
  busy,
  notice,
}: {
  onCreate: (name: string) => Promise<void>;
  onRestore: (name: string, code: string) => Promise<void>;
  busy: boolean;
  notice: string;
}) {
  const [mode, setMode] = useState<"new" | "restore">("new");
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  return (
    <main className="welcome-screen">
      <div className="welcome-art" aria-hidden="true">
        <span>⅗</span><span>π</span><span>42</span><span>%</span><span>x</span>
      </div>
      <section className="welcome-card">
        <div className="logo-lockup">
          <span className="brand-mark large">JM</span>
          <div><h1>JENS MATTE</h1><p>Matteeventyr for 5.–7. trinn</p></div>
        </div>
        <div className="feature-row">
          <span>500 oppgaver</span><span>Forklaring ved feil</span><span>Adaptivt nivå</span>
        </div>
        <div className="mode-tabs">
          <button className={mode === "new" ? "active" : ""} onClick={() => setMode("new")}>Ny spiller</button>
          <button className={mode === "restore" ? "active" : ""} onClick={() => setMode("restore")}>Jeg har spillkode</button>
        </div>
        <form onSubmit={(event: FormEvent<HTMLFormElement>) => {
          event.preventDefault();
          if (mode === "new") void onCreate(name);
          else void onRestore(name, code);
        }}>
          <label>
            Navn
            <input value={name} onChange={(event: ChangeEvent<HTMLInputElement>) => setName(event.target.value)} placeholder="For eksempel Jens" autoComplete="nickname" maxLength={24} required />
          </label>
          {mode === "restore" && (
            <label>
              Spillkode
              <input value={code} onChange={(event: ChangeEvent<HTMLInputElement>) => setCode(event.target.value.toUpperCase())} placeholder="ABCD-EFGH" autoCapitalize="characters" maxLength={9} required />
            </label>
          )}
          <button className="primary-button" type="submit" disabled={busy || name.trim().length < 2}>
            {busy ? "Kobler til …" : mode === "new" ? "Start matteeventyret" : "Hent spilleren min"}
          </button>
        </form>
        {notice && <p className="form-error" role="alert">{notice}</p>}
        <p className="privacy-note">Vi lagrer bare fornavn/kallenavn og matteprogresjon – ingen e-post eller fødselsdato.</p>
      </section>
    </main>
  );
}

function Home({
  profile,
  skills,
  onStart,
  syncState,
}: {
  profile: PlayerProfile;
  skills: SkillProgress[];
  onStart: (topic?: string) => void;
  syncState: SyncState;
}) {
  const strongest = [...skills].sort((a, b) => b.mastery - a.mastery)[0];
  const focus = skills[0];
  return (
    <section className="home-screen">
      <div className="hero-card">
        <div>
          <p className="eyebrow">Hei, {profile.name} 👋</p>
          <h1>Klar for ti nye nøtter?</h1>
          <p>Spillet velger oppgaver som passer nivået ditt og forklarer ordentlig når noe blir feil.</p>
          <button className="primary-button hero-cta" onClick={() => onStart()}>Start blandet runde</button>
        </div>
        <div className="level-orbit" aria-label={`Mattenivå ${profile.overallLevel}`}>
          <span>NIVÅ</span><strong>{profile.overallLevel}</strong><small>{profile.xp} XP</small>
        </div>
      </div>

      <div className="dashboard-grid">
        <article className="stat-card">
          <span>Skyprogresjon</span>
          <strong>{syncLabel(syncState, profile.mode)}</strong>
          <small>{profile.mode === "synced" ? "Samme profil på iPhone og Mac" : "Lagres på denne enheten"}</small>
        </article>
        <article className="stat-card">
          <span>Sterkest nå</span>
          <strong>{strongest?.skill ?? "Kom i gang"}</strong>
          <small>{strongest ? `${Math.round(strongest.mastery * 100)} % mestring` : "Første runde bygger profilen"}</small>
        </article>
        <article className="stat-card">
          <span>Neste fokus</span>
          <strong>{focus?.skill ?? "Blandet matte"}</strong>
          <small>{focus ? `Tren videre på nivå ${focus.level}` : "Vi finner riktig nivå sammen"}</small>
        </article>
      </div>

      <div className="section-heading">
        <div><p className="eyebrow">Velg treningsøkt</p><h2>Hva vil du øve på?</h2></div>
        <span>10 oppgaver · ingen tidtaking</span>
      </div>
      <div className="topic-grid">
        {topics.map((topic) => (
          <button key={topic} className="topic-card" onClick={() => onStart(topic)}>
            <span className="topic-icon">{TOPIC_ICONS[topic] ?? "∑"}</span>
            <strong>{topic}</strong>
            <small>{questions.filter((q) => q.topic === topic).length} oppgaver</small>
          </button>
        ))}
      </div>

      <div className="home-mastery">
        <div className="section-heading compact"><div><p className="eyebrow">Din læringsprofil</p><h2>Dette trener spillet på</h2></div></div>
        <MasteryBars skills={skills.slice(0, 6)} />
      </div>
    </section>
  );
}

function ResultScreen({
  profile,
  summary,
  syncState,
  onAgain,
  onHome,
}: {
  profile: PlayerProfile;
  summary: RoundSummary;
  syncState: SyncState;
  onAgain: () => void;
  onHome: () => void;
}) {
  const perfect = summary.correct === summary.total;
  return (
    <section className="result-screen">
      {(perfect || summary.bestStreak >= 7) && <Confetti />}
      <div className="result-card">
        <p className="eyebrow">Runden er ferdig</p>
        <h1>{perfect ? "Full pott!" : summary.correct >= 8 ? "Sterk runde!" : "Bra jobbet – du lærte noe nytt"}</h1>
        <div className="score-ring">
          <strong>{summary.correct}</strong><span>/ {summary.total}</span>
        </div>
        <div className="result-stats">
          <div><span>XP</span><strong>+{summary.xpEarned}</strong></div>
          <div><span>Beste streak</span><strong>🔥 {summary.bestStreak}</strong></div>
          <div><span>Mattenivå</span><strong>{profile.overallLevel}</strong></div>
        </div>
        <div className={`sync-message ${syncState}`}>
          {syncState === "saving" && "Lagrer progresjonen …"}
          {syncState === "saved" && "✓ Progresjonen er lagret på tvers av enheter"}
          {syncState === "local" && "Progresjonen er lagret på denne enheten"}
          {syncState === "error" && "Runden er lagret på denne enheten, men er ikke synkronisert."}
        </div>
      </div>

      <article className="focus-card">
        <h2>Smart neste steg</h2>
        <p>Spillet bruker resultatene til å justere nivå og velge neste runde.</p>
        <MasteryBars skills={summary.focusSkills} />
      </article>

      <div className="result-actions">
        <button className="primary-button" onClick={onAgain}>Ny blandet runde</button>
        <button className="secondary-button" onClick={onHome}>Til forsiden</button>
      </div>
    </section>
  );
}

function ProfileScreen({
  profile,
  skills,
  syncState,
  onBack,
  onLogOut,
  onDelete,
}: {
  profile: PlayerProfile;
  skills: SkillProgress[];
  syncState: SyncState;
  onBack: () => void;
  onLogOut: () => void;
  onDelete: () => void;
}) {
  const totalAttempts = skills.reduce((sum, item) => sum + item.attempts, 0);
  const totalCorrect = skills.reduce((sum, item) => sum + item.correct, 0);
  return (
    <section className="profile-screen">
      <button className="text-button" onClick={onBack}>← Tilbake</button>
      <div className="profile-hero">
        <div className="profile-avatar">{profile.name.slice(0, 1).toUpperCase()}</div>
        <div><p className="eyebrow">Spillerprofil</p><h1>{profile.name}</h1><p>{syncLabel(syncState, profile.mode)}</p></div>
        <div className="profile-level"><span>Nivå</span><strong>{profile.overallLevel}</strong></div>
      </div>
      <div className="dashboard-grid">
        <article className="stat-card"><span>Total XP</span><strong>{profile.xp}</strong><small>Spillnivå {xpLevel(profile.xp)}</small></article>
        <article className="stat-card"><span>Besvarte oppgaver</span><strong>{totalAttempts}</strong><small>på denne profilen</small></article>
        <article className="stat-card"><span>Treffprosent</span><strong>{totalAttempts ? Math.round(totalCorrect / totalAttempts * 100) : 0}%</strong><small>{totalCorrect} riktige svar</small></article>
      </div>
      {profile.playerCode && (
        <article className="code-card">
          <div><span>Spillkode</span><strong>{profile.playerCode}</strong></div>
          <p>Bruk navn + spillkode for å fortsette på en annen iPhone eller Mac. Ta gjerne et skjermbilde.</p>
        </article>
      )}
      <article className="profile-mastery">
        <h2>Mestring per ferdighet</h2>
        <MasteryBars skills={skills} />
      </article>
      <div className="profile-actions">
        <button className="secondary-button" onClick={onLogOut}>Bytt spiller på denne enheten</button>
        <button className="danger-button" onClick={onDelete}>Slett profil og progresjon</button>
      </div>
    </section>
  );
}

function PlayerCodeModal({ code, onClose }: { code: string; onClose: () => void }) {
  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="code-title">
      <div className="modal-card">
        <span className="modal-icon">☁️</span>
        <h2 id="code-title">Ta vare på spillkoden</h2>
        <p>Med denne koden kan du hente samme progresjon på en annen enhet.</p>
        <strong className="big-code">{code}</strong>
        <p className="muted">Koden finnes også på profilsiden. Ta gjerne et skjermbilde nå.</p>
        <button className="primary-button" onClick={onClose}>Jeg har lagret koden</button>
      </div>
    </div>
  );
}

function syncLabel(syncState: SyncState, mode: PlayerProfile["mode"]): string {
  if (mode === "local") return "Lokal lagring";
  if (syncState === "saving") return "Lagrer …";
  if (syncState === "error") return "Lokal reservekopi";
  if (syncState === "local") return "Frakoblet akkurat nå";
  return "På tvers av enheter";
}
