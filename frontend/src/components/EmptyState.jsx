export default function EmptyState({ title, description }) {
  return (
    <section className="card empty-state">
      <h3>{title}</h3>
      <p>{description}</p>
    </section>
  );
}
