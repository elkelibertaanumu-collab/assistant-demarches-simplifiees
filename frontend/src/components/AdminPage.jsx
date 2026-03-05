import { useEffect, useState } from "react";

const API_BASE = "/api";

const EMPTY_ROW = {
  id: "",
  title: "",
  url: "",
  category: "papiers_citoyennete",
  type: "html",
  updated_at: new Date().toISOString().slice(0, 10)
};

export default function AdminPage({ token }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [reindexing, setReindexing] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    loadSources();
  }, []);

  async function loadSources() {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/admin/sources`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Impossible de charger les sources");
      const data = await res.json();
      setItems(Array.isArray(data.items) ? data.items : []);
    } catch (err) {
      setError(err.message || "Erreur chargement admin");
    } finally {
      setLoading(false);
    }
  }

  function updateItem(index, key, value) {
    setItems((prev) => prev.map((row, i) => (i === index ? { ...row, [key]: value } : row)));
  }

  function addRow() {
    setItems((prev) => [...prev, { ...EMPTY_ROW }]);
  }

  function removeRow(index) {
    setItems((prev) => prev.filter((_, i) => i !== index));
  }

  async function saveSources() {
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const filtered = items.filter((row) => row.id && row.title && row.url);
      const res = await fetch(`${API_BASE}/admin/sources`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ items: filtered })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || "Sauvegarde impossible");
      setMessage(data.message || "Sources sauvegardees.");
      setItems(filtered);
    } catch (err) {
      setError(err.message || "Erreur sauvegarde");
    } finally {
      setSaving(false);
    }
  }

  async function reindexNow() {
    setReindexing(true);
    setError("");
    setMessage("");
    try {
      const res = await fetch(`${API_BASE}/admin/reindex`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || "Reindexation impossible");
      setMessage(data.message || "Reindexation terminee.");
    } catch (err) {
      setError(err.message || "Erreur reindexation");
    } finally {
      setReindexing(false);
    }
  }

  return (
    <section className="card">
      <h3>Espace Admin</h3>
      <p>Gere les sources officielles RAG puis lance la reindexation.</p>
      {loading && <p>Chargement des sources...</p>}
      {error && <p className="error">{error}</p>}
      {message && <p className="hint">{message}</p>}

      <div className="admin-grid">
        {items.map((row, index) => (
          <div key={`${row.id || "row"}-${index}`} className="admin-row">
            <input
              value={row.id}
              onChange={(e) => updateItem(index, "id", e.target.value)}
              placeholder="id"
            />
            <input
              value={row.title}
              onChange={(e) => updateItem(index, "title", e.target.value)}
              placeholder="title"
            />
            <input
              value={row.url}
              onChange={(e) => updateItem(index, "url", e.target.value)}
              placeholder="https://...gouv.tg/..."
            />
            <input
              value={row.category}
              onChange={(e) => updateItem(index, "category", e.target.value)}
              placeholder="category"
            />
            <input
              value={row.updated_at}
              onChange={(e) => updateItem(index, "updated_at", e.target.value)}
              placeholder="YYYY-MM-DD"
            />
            <button className="btn-danger" type="button" onClick={() => removeRow(index)}>
              Supprimer
            </button>
          </div>
        ))}
      </div>

      <div className="actions">
        <button type="button" className="btn-secondary" onClick={addRow}>Ajouter une source</button>
        <button type="button" disabled={saving} onClick={saveSources}>
          {saving ? "Sauvegarde..." : "Sauvegarder les sources"}
        </button>
      </div>

      <button type="button" className="btn-secondary" disabled={reindexing} onClick={reindexNow}>
        {reindexing ? "Reindexation..." : "Lancer reindexation RAG"}
      </button>
    </section>
  );
}
