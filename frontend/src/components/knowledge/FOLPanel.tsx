import { useState } from "react";
import type { FormEvent } from "react";

import type { FOLResult } from "@/types";

interface Props {
  result: FOLResult | null;
  onQuery: (query: string) => void;
  pending: boolean;
}

export function FOLPanel({ result, onQuery, pending }: Props) {
  const [query, setQuery] = useState("Unsafe(R) & Road(R)");

  function submit(event: FormEvent) {
    event.preventDefault();
    onQuery(query);
  }

  const columns = result?.bindings?.[0] ? Object.keys(result.bindings[0]):[];

  return (
    <section className="rounded-panel border border-border bg-panel">
      <div className="border-b border-border px-4 py-3">
        <h2 className="text-2xs font-medium tracking-wide text-fg-muted uppercase">First-order logic query</h2>
        <p className="mt-1 text-[12px] text-fg-muted">Positive conjunctive queries with variables.</p>
      </div>
      <form onSubmit={submit} className="flex flex-col gap-2 p-4 sm:flex-row">
        <input value={query} onChange={(event) => setQuery(event.target.value)}
          aria-label="FOL query"
          className="min-w-0 flex-1 rounded-panel border border-border bg-bg px-3 py-2 font-mono text-[12px] text-fg outline-none focus:border-info/60"
          placeholder="Unsafe(R) & Road(R)" />
        <button type="submit" disabled={pending || !query.trim()}
          className="rounded-panel border border-info/40 bg-info/10 px-3 py-2 text-2xs uppercase tracking-wide text-info disabled:opacity-40">
          {pending ? "Querying…" : "Query"}
        </button>
      </form>
      <div className="px-4 pb-4">
        <div className="mb-2 font-mono text-2xs text-fg-muted">{result?.query ?? "No query yet"} · {result?.count ?? 0} matches</div>
        {result && result.bindings.length > 0 ? (
          <div className="overflow-auto rounded-panel border border-border">
            <table className="w-full text-left text-[11px]">
              <thead className="bg-panel-2 text-2xs uppercase tracking-wide text-fg-muted">
                <tr>{columns.map((column) => <th key={column} className="px-3 py-2">{column}</th>)}</tr>
              </thead>
              <tbody>{result.bindings.map((row, index) => <tr key={index} className="border-t border-border"><>{columns.map((column) => <td key={column} className="px-3 py-2 font-mono text-fg">{row[column]}</td>)}</></tr>)}</tbody>
            </table>
          </div>
        ) : result ? <p className="rounded-panel border border-border bg-bg p-3 text-[12px] text-fg-muted">No bindings matched.</p> : null}
      </div>
    </section>
  );
}
