type Props = {
  message?: string;
};

export function EmptyState({ message }: Props) {
  return (
    <p style={{ color: "var(--muted)" }}>
      {message ?? "No articles yet. The collector is still warming up."}
    </p>
  );
}
