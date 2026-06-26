// Status badge (rounded pill). `tone` drives the colour token.

export type BadgeTone = "neutral" | "cloud" | "local" | "voice" | "chat";

export function Badge({
  tone = "neutral",
  children,
  title,
}: {
  tone?: BadgeTone;
  children: React.ReactNode;
  title?: string;
}) {
  return (
    <span className={`badge badge-${tone}`} title={title}>
      {children}
    </span>
  );
}
