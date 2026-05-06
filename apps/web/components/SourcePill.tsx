import type { SourceKind } from "@/lib/sources";

type Props = {
  kind: SourceKind;
  label: string;
};

export function SourcePill({ kind, label }: Props) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium"
      style={{
        background: `var(--src-${kind}-bg)`,
        color: `var(--src-${kind}-fg)`,
      }}
    >
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ background: `var(--src-${kind}-dot)` }}
      />
      {label}
    </span>
  );
}
