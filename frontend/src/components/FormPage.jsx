import { useEffect, useMemo, useState } from "react";
import { jsPDF } from "jspdf";

const API_BASE = "/api";

export default function FormPage() {
  const [catalog, setCatalog] = useState([]);
  const [selectedFormId, setSelectedFormId] = useState("");
  const [values, setValues] = useState({});
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [assistLoadingKey, setAssistLoadingKey] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    loadCatalog();
  }, []);

  async function loadCatalog() {
    try {
      const res = await fetch(`${API_BASE}/form/catalog`);
      if (!res.ok) throw new Error("Impossible de charger les formulaires");
      const data = await res.json();
      const items = Array.isArray(data.items) ? data.items : [];
      setCatalog(items);
      if (items.length && !selectedFormId) {
        setSelectedFormId(items[0].form_id);
      }
    } catch (e) {
      setError(e.message || "Erreur chargement formulaires");
    }
  }

  const selectedForm = useMemo(
    () => catalog.find((item) => item.form_id === selectedFormId) || null,
    [catalog, selectedFormId]
  );

  function updateField(key, value) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  async function assistField(fieldKey) {
    if (!selectedFormId) return;
    setAssistLoadingKey(fieldKey);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/form/assist`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          form_id: selectedFormId,
          field_key: fieldKey,
          current_values: values
        })
      });
      if (!res.ok) throw new Error("Impossible de generer une suggestion");
      const data = await res.json();
      if (data.suggestion) {
        updateField(fieldKey, data.suggestion);
      }
    } catch (e) {
      setError(e.message || "Erreur assistance champ");
    } finally {
      setAssistLoadingKey("");
    }
  }

  async function generatePreview() {
    if (!selectedFormId) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/form/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ form_id: selectedFormId, values })
      });
      if (!res.ok) throw new Error("Generation impossible");
      const data = await res.json();
      setPreview(data);
    } catch (e) {
      setError(e.message || "Erreur generation exemplaire");
    } finally {
      setLoading(false);
    }
  }

  function downloadPreviewPdf() {
    if (!preview?.preview_lines?.length) return;
    const doc = new jsPDF();
    const lines = [...preview.preview_lines, "", preview.disclaimer || ""];
    let y = 16;
    doc.setFontSize(12);
    for (const line of lines) {
      const wrapped = doc.splitTextToSize(String(line), 180);
      for (const w of wrapped) {
        if (y > 280) {
          doc.addPage();
          y = 16;
        }
        doc.text(w, 14, y);
        y += 7;
      }
    }
    doc.save(`exemplaire-${selectedFormId || "formulaire"}.pdf`);
  }

  return (
    <section className="card">
      <h3>Formulaire assiste</h3>
      <p>Remplis les champs puis genere un exemplaire telechargeable.</p>
      <p className="disclaimer">
        Exemplaire genere = brouillon non officiel. A verifier avant soumission administrative.
      </p>

      {error && <p className="error">{error}</p>}

      <label>Type de formulaire</label>
      <select
        value={selectedFormId}
        onChange={(e) => {
          setSelectedFormId(e.target.value);
          setPreview(null);
          setValues({});
        }}
      >
        {catalog.map((item) => (
          <option key={item.form_id} value={item.form_id}>{item.title}</option>
        ))}
      </select>

      {selectedForm && (
        <div className="form-grid">
          {selectedForm.fields.map((field) => (
            <div className="field-row" key={field.key}>
              <label>{field.label}</label>
              <input
                value={values[field.key] || ""}
                onChange={(e) => updateField(field.key, e.target.value)}
                placeholder={field.placeholder || ""}
              />
              <button
                type="button"
                className="btn-secondary"
                disabled={assistLoadingKey === field.key}
                onClick={() => assistField(field.key)}
              >
                {assistLoadingKey === field.key ? "Suggestion..." : "Aider ce champ"}
              </button>
            </div>
          ))}
        </div>
      )}

      <button type="button" disabled={loading || !selectedFormId} onClick={generatePreview}>
        {loading ? "Generation..." : "Generer exemplaire"}
      </button>

      {preview?.preview_lines?.length > 0 && (
        <div className="answer">
          <h4>Apercu</h4>
          <ul>{preview.preview_lines.map((line, idx) => <li key={idx}>{line}</li>)}</ul>
          <p><strong>{preview.disclaimer}</strong></p>
          <button type="button" className="btn-secondary" onClick={downloadPreviewPdf}>
            Telecharger exemplaire PDF
          </button>
        </div>
      )}
    </section>
  );
}
