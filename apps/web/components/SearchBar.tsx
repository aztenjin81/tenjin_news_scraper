"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { slugify } from "@/lib/topics";

export function SearchBar() {
  const router = useRouter();
  const [v, setV] = useState("");
  const [focus, setFocus] = useState(false);
  const slug = slugify(v);
  const canSubmit = slug.length > 1;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (canSubmit) router.push(`/t/${slug}`);
      }}
      className="flex items-stretch overflow-hidden rounded-lg transition-colors duration-150"
      style={{
        border: `1px solid ${focus ? "rgba(197,48,31,0.55)" : "rgba(255,255,255,0.10)"}`,
        background: "var(--surface-1)",
        boxShadow: focus ? "0 0 0 3px rgba(197,48,31,0.15)" : "none",
      }}
    >
      <span
        className="inline-flex items-center px-3 text-[11px] font-medium uppercase tracking-wider"
        style={{
          color: "var(--muted)",
          borderRight: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        Topic
      </span>
      <input
        value={v}
        onChange={(e) => setV(e.target.value)}
        onFocus={() => setFocus(true)}
        onBlur={() => setFocus(false)}
        placeholder="Search any topic — iran, houthis, gaza…"
        className="flex-1 border-0 bg-transparent px-3.5 py-3.5 text-base outline-none"
        style={{ color: "var(--foreground)" }}
        aria-label="Search any topic"
      />
      <button
        type="submit"
        disabled={!canSubmit}
        className="px-[18px] text-sm font-medium transition-colors duration-150"
        style={{
          background: canSubmit ? "var(--accent)" : "rgba(255,255,255,0.06)",
          color: canSubmit ? "#fff" : "var(--muted)",
          cursor: canSubmit ? "pointer" : "not-allowed",
        }}
      >
        Open feed
      </button>
    </form>
  );
}
