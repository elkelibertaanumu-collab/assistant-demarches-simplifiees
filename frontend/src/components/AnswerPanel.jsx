export default function AnswerPanel({ result }) {
  if (!result) return null;

  const latestSourceDate = result.sources?.length
    ? result.sources.map((s) => s.updated_at).sort().reverse()[0]
    : null;

  return (
    <section className="result">
      <p className="disclaimer">
        Brouillon informatif non officiel. Verifie toujours sur la source administrative avant depot.
      </p>
      <h2>Resume</h2>
      <p>{result.summary}</p>
      <p><strong>Confiance:</strong> {Math.round((result.confidence_score || 0) * 100)}%</p>
      <p><strong>Genere le:</strong> {new Date(result.generated_at).toLocaleString()}</p>

      <h3>Etapes</h3>
      <ol>{result.steps.map((s, i) => <li key={i}>{s}</li>)}</ol>

      <h3>Pieces requises</h3>
      <ul>{result.required_documents.map((d, i) => <li key={i}>{d}</li>)}</ul>

      <h3>Erreurs frequentes</h3>
      <ul>{result.common_mistakes.map((m, i) => <li key={i}>{m}</li>)}</ul>

      <h3>Checklist suggestion</h3>
      <ul>{result.checklist.map((c, i) => <li key={i}>{c}</li>)}</ul>

      <h3>Sources officielles</h3>
      {latestSourceDate && <p><strong>Derniere mise a jour source:</strong> {latestSourceDate}</p>}
      <ul>
        {result.sources.map((src, i) => (
          <li key={i}>
            <a href={src.url} target="_blank" rel="noreferrer">{src.title}</a> - maj {src.updated_at}
          </li>
        ))}
      </ul>
    </section>
  );
}
