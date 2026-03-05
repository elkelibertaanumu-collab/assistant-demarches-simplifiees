export default function HistoryPanel({ history, onReuseQuestion }) {
  if (!history.length) return null;

  return (
    <section className="card">
      <h3>Historique recent</h3>
      <ul className="history-list">
        {history.map((item) => (
          <li key={item.id}>
            <button className="history-btn" onClick={() => onReuseQuestion(item.question)}>
              <strong>{item.question}</strong>
              <span className="history-meta">
                {new Date(item.generated_at).toLocaleString()}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
