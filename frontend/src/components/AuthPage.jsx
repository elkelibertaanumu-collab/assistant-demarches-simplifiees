import { useState } from "react";

const API_BASE = "/api";

export default function AuthPage({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    setError("");
    if (!email.trim() || !password.trim() || (mode === "register" && !name.trim())) {
      setError("Remplis tous les champs requis.");
      return;
    }
    setLoading(true);
    try {
      const endpoint = mode === "register" ? "/auth/register" : "/auth/login";
      const payload = mode === "register"
        ? { name: name.trim(), email: email.trim(), password }
        : { email: email.trim(), password };
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail || "Authentification impossible");
      }
      const data = await res.json();
      onLogin({ token: data.token, user: data.user });
    } catch (err) {
      setError(err.message || "Erreur inconnue");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page">
      <section className="card auth-card">
        <h1>{mode === "login" ? "Connexion" : "Inscription"}</h1>
        <p>{mode === "login" ? "Connecte-toi pour acceder a l'assistant administratif." : "Cree ton compte pour utiliser l'assistant."}</p>
        <form onSubmit={submit} className="auth-form">
          {mode === "register" && (
            <>
              <label>Nom complet</label>
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Ton nom" />
            </>
          )}
          <label>Email</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="toi@email.com" />
          <label>Mot de passe</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="********" />
          {mode === "register" && (
            <p className="hint">Mot de passe: 8+ caracteres, avec majuscule, minuscule et chiffre.</p>
          )}
          {error && <p className="error">{error}</p>}
          <button type="submit" disabled={loading}>
            {loading ? "Chargement..." : mode === "login" ? "Se connecter" : "S'inscrire"}
          </button>
        </form>
        <button
          type="button"
          className="btn-secondary"
          onClick={() => {
            setMode((m) => (m === "login" ? "register" : "login"));
            setError("");
          }}
        >
          {mode === "login" ? "Creer un compte" : "J'ai deja un compte"}
        </button>
      </section>
    </main>
  );
}
