import { useEffect, useState } from "react";
import AskForm from "./components/AskForm";
import AnswerPanel from "./components/AnswerPanel";
import HistoryPanel from "./components/HistoryPanel";
import EmptyState from "./components/EmptyState";
import ChecklistPage from "./components/ChecklistPage";
import AuthPage from "./components/AuthPage";
import FormPage from "./components/FormPage";

const API_BASE = "/api";
const USER_KEY = "ads_user";
const TOKEN_KEY = "ads_token";

export default function App() {
  const [activeTab, setActiveTab] = useState("assistant");
  const [user, setUser] = useState(null);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [checklistResult, setChecklistResult] = useState(null);
  const [checklistLoading, setChecklistLoading] = useState(false);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    validateStoredSession();
    loadHistory();
  }, []);

  async function validateStoredSession() {
    const raw = localStorage.getItem(USER_KEY);
    const token = localStorage.getItem(TOKEN_KEY);
    if (!raw || !token) return;
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Session invalide");
      const data = await res.json();
      setUser(data.user);
      localStorage.setItem(USER_KEY, JSON.stringify(data.user));
    } catch {
      localStorage.removeItem(USER_KEY);
      localStorage.removeItem(TOKEN_KEY);
      setUser(null);
    }
  }

  async function loadHistory() {
    try {
      const res = await fetch(`${API_BASE}/history`);
      if (!res.ok) return;
      const data = await res.json();
      setHistory(Array.isArray(data.items) ? data.items : []);
    } catch {
      // keep silent for first-load UX
    }
  }

  async function ask() {
    if (!question.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    setChecklistResult(null);
    try {
      const res = await fetch(`${API_BASE}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question })
      });
      if (!res.ok) throw new Error("Echec de la requete");
      const data = await res.json();
      setResult(data);
      await loadHistory();
    } catch (e) {
      setError(e.message || "Erreur inconnue");
    } finally {
      setLoading(false);
    }
  }

  async function generateChecklist() {
    if (!question.trim()) return;
    setChecklistLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/checklist`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ procedure: question })
      });
      if (!res.ok) throw new Error("Echec generation checklist");
      const data = await res.json();
      setChecklistResult(data);
      setActiveTab("checklist");
    } catch (e) {
      setError(e.message || "Erreur inconnue");
    } finally {
      setChecklistLoading(false);
    }
  }

  function onLogin(authPayload) {
    const nextUser = authPayload?.user || null;
    const token = authPayload?.token || "";
    if (!nextUser || !token) return;
    setUser(nextUser);
    localStorage.setItem(USER_KEY, JSON.stringify(nextUser));
    localStorage.setItem(TOKEN_KEY, token);
  }

  async function logout() {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) {
      try {
        await fetch(`${API_BASE}/auth/logout`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` }
        });
      } catch {
        // ignore network errors on logout
      }
    }
    setUser(null);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(TOKEN_KEY);
  }

  if (!user) {
    return <AuthPage onLogin={onLogin} />;
  }

  return (
    <main className="page">
      <header className="hero">
        <h1>Assistant Demarches Simplifiees - Togo</h1>
        <p>Pose ta question administrative et obtiens un plan d'action clair.</p>
        <div className="user-row">
          <span>Connecte: {user.name}</span>
          <button className="btn-secondary" onClick={logout}>Deconnexion</button>
        </div>
      </header>

      <nav className="tabs">
        <button
          className={activeTab === "assistant" ? "tab active" : "tab"}
          onClick={() => setActiveTab("assistant")}
        >
          Assistant
        </button>
        <button
          className={activeTab === "checklist" ? "tab active" : "tab"}
          onClick={() => setActiveTab("checklist")}
        >
          Checklist
        </button>
        <button
          className={activeTab === "form" ? "tab active" : "tab"}
          onClick={() => setActiveTab("form")}
        >
          Formulaire
        </button>
        <button
          className={activeTab === "history" ? "tab active" : "tab"}
          onClick={() => setActiveTab("history")}
        >
          Historique
        </button>
      </nav>

      {error && <p className="error">{error}</p>}

      {activeTab === "assistant" && (
        <>
          <AskForm
            question={question}
            loading={loading}
            checklistLoading={checklistLoading}
            onChangeQuestion={setQuestion}
            onAsk={ask}
            onGenerateChecklist={generateChecklist}
          />
          {!result && !loading && (
            <EmptyState
              title="Commence par une question"
              description="Exemple: Quels documents pour creer une entreprise au Togo ?"
            />
          )}
          <AnswerPanel result={result} />
        </>
      )}

      {activeTab === "checklist" && (
        <ChecklistPage
          question={question}
          checklistResult={checklistResult}
          loading={checklistLoading}
          onGenerate={generateChecklist}
        />
      )}

      {activeTab === "form" && <FormPage />}

      {activeTab === "history" && (
        <HistoryPanel history={history} onReuseQuestion={(q) => {
          setQuestion(q);
          setActiveTab("assistant");
        }} />
      )}
    </main>
  );
}
