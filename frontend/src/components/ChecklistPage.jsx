import { jsPDF } from "jspdf";

export default function ChecklistPage({ question, checklistResult, loading, onGenerate }) {
  function downloadChecklistPdf() {
    if (!checklistResult?.items?.length) return;
    const doc = new jsPDF();
    const lines = [
      "Assistant Demarches Simplifiees - Checklist",
      "",
      `Procedure: ${checklistResult.procedure}`,
      "",
      ...checklistResult.items.map((item, i) => `${i + 1}. ${item}`)
    ];
    let y = 16;
    doc.setFontSize(12);
    for (const line of lines) {
      const wrapped = doc.splitTextToSize(line, 180);
      for (const w of wrapped) {
        if (y > 280) {
          doc.addPage();
          y = 16;
        }
        doc.text(w, 14, y);
        y += 7;
      }
    }
    doc.save("checklist-demarche.pdf");
  }

  return (
    <section className="card">
      <h3>Checklist</h3>
      <p className="disclaimer">
        Checklist d'appui non officielle. Controle toujours les exigences sur les portails de l'Etat.
      </p>
      {!question.trim() && (
        <p>Pose d'abord une question dans l'onglet Assistant.</p>
      )}
      {question.trim() && (
        <>
          <p><strong>Procedure:</strong> {question}</p>
          <button className="btn-secondary" disabled={loading} onClick={onGenerate}>
            {loading ? "Generation..." : "Generer checklist"}
          </button>
        </>
      )}

      {checklistResult?.items?.length > 0 && (
        <>
          <ul>{checklistResult.items.map((item, i) => <li key={i}>{item}</li>)}</ul>
          <button className="btn-secondary" onClick={downloadChecklistPdf}>
            Telecharger checklist PDF
          </button>
        </>
      )}
    </section>
  );
}
