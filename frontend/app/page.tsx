"use client";

import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

const API = "http://127.0.0.1:8000";

type Risk = {
  date: string;
  eur_ron: number;
  risk_level: "scazut" | "mediu" | "ridicat";
  historical_big_move_rate: number;
  big_move_threshold_pct: number;
  drivers: {
    eur_change_today_pct: number;
    eur_volatility_5d: number;
    eur_max_move_5d_pct: number;
  };
};

type Day = {
  date: string;
  eur_ron: number;
  risk_level: string;
  big_move_next_day: boolean | null;
};

const LEVEL_STYLE = {
  scazut: { label: "Scăzut", color: "bg-green-100 text-green-900 border-green-300" },
  mediu: { label: "Mediu", color: "bg-yellow-100 text-yellow-900 border-yellow-300" },
  ridicat: { label: "Ridicat", color: "bg-red-100 text-red-900 border-red-300" },
};

export default function Home() {
  const [risk, setRisk] = useState<Risk | null>(null);
  const [history, setHistory] = useState<Day[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/risk/latest`).then((r) => r.json()),
      fetch(`${API}/history?days=120`).then((r) => r.json()),
    ])
      .then(([riskData, historyData]) => {
        setRisk(riskData);
        setHistory(historyData);
      })
      .catch(() => setError("Nu pot contacta API-ul. Este pornit serverul pe portul 8000?"));
  }, []);

  if (error) return <main className="p-8 text-red-700">{error}</main>;
  if (!risk) return <main className="p-8">Se încarcă...</main>;

  const style = LEVEL_STYLE[risk.risk_level];

  return (
    <main className="mx-auto max-w-3xl p-6 space-y-8">
      <header>
        <h1 className="text-3xl font-bold">FXcast</h1>
        <p className="opacity-70">Riscul unei mișcări mari a cursului EUR/RON în ziua următoare</p>
      </header>

      <section className={`rounded-xl border p-6 ${style.color}`}>
        <p className="text-sm uppercase tracking-wide">Risc pentru ziua următoare</p>
        <p className="text-4xl font-bold mt-1">{style.label}</p>
        <p className="mt-3">
          Istoric, după zile cu acest nivel de risc, cursul s-a mișcat cu peste{" "}
          {risk.big_move_threshold_pct}% în {(risk.historical_big_move_rate * 100).toFixed(1)}% din cazuri.
        </p>
      </section>

      <section className="grid grid-cols-3 gap-4 text-center">
        <Stat label="Curs BNR" value={risk.eur_ron.toFixed(4)} sub={risk.date} />
        <Stat label="Schimbare azi" value={`${risk.drivers.eur_change_today_pct}%`} />
        <Stat label="Max. 5 zile" value={`${risk.drivers.eur_max_move_5d_pct}%`} />
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-2">Cursul EUR/RON, ultimele 120 de zile</h2>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={history}>
              <XAxis dataKey="date" tick={{ fontSize: 12 }} minTickGap={40} />
              <YAxis domain={["auto", "auto"]} tick={{ fontSize: 12 }} width={60} />
              <Tooltip />
              <Line type="monotone" dataKey="eur_ron" stroke="#2563eb" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      <footer className="text-sm opacity-70 border-t pt-4">
        Instrument educațional, nu sfat financiar. Modelul estimează riscul unei mișcări mari, nu
        direcția cursului, și nu poate anticipa șocuri politice care nu au fost precedate de agitație pe piață.
      </footer>
    </main>
  );
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border p-4">
      <p className="text-sm opacity-70">{label}</p>
      <p className="text-xl font-semibold">{value}</p>
      {sub && <p className="text-xs opacity-60">{sub}</p>}
    </div>
  );
}