export default function AskForm({
  question,
  loading,
  checklistLoading,
  onChangeQuestion,
  onAsk,
  onGenerateChecklist
}) {
  return (
    <section className="card">
      <textarea
        rows={4}
        placeholder="Ex: Comment creer une micro-entreprise au Togo ?"
        value={question}
        onChange={(e) => onChangeQuestion(e.target.value)}
      />
      <div className="actions">
        <button disabled={loading} onClick={onAsk}>
          {loading ? "Analyse..." : "Demander"}
        </button>
        <button className="btn-secondary" disabled={checklistLoading} onClick={onGenerateChecklist}>
          {checklistLoading ? "Generation..." : "Generer checklist"}
        </button>
      </div>
    </section>
  );
}
