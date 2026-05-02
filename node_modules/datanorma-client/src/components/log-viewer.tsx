import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

type Level = "all" | "info" | "warning" | "error";
type Stage = "all" | "extract" | "staging" | "normalize" | "validate" | "load";

function parseLevel(line: string): string {
  const m = line.match(/\[(info|warning|error)\]/i);
  return m?.[1]?.toLowerCase() ?? "";
}

function parseStage(line: string): string {
  const m = line.match(/\[(extract|staging|normalize|validate|load)\]/i);
  return m?.[1]?.toLowerCase() ?? "";
}

export function LogViewer({ logs }: { logs: string[] }) {
  const [query, setQuery] = useState("");
  const [level, setLevel] = useState<Level>("all");
  const [stage, setStage] = useState<Stage>("all");
  const [wrap, setWrap] = useState(true);

  const filtered = useMemo(() => {
    return logs.filter((l) => {
      if (query && !l.toLowerCase().includes(query.toLowerCase())) return false;
      if (level !== "all") {
        const lv = parseLevel(l);
        if (lv && lv !== level) return false;
      }
      if (stage !== "all") {
        const st = parseStage(l);
        if (st && st !== stage) return false;
      }
      return true;
    });
  }, [logs, query, level, stage]);

  const text = filtered.join("\n");

  const copyAll = async () => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="rounded-lg border bg-card p-3" data-testid="panel-log-viewer">
      <div className="mb-2 flex flex-wrap gap-2">
        <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Поиск по логам..." data-testid="input-log-search" className="max-w-xs" />
        <select
          className="h-9 rounded-md border bg-background px-2 text-sm"
          value={level}
          onChange={(e) => setLevel(e.target.value as Level)}
          data-testid="select-log-level"
          aria-label="Уровень лога"
        >
          <option value="all">Все уровни</option>
          <option value="info">info</option>
          <option value="warning">warning</option>
          <option value="error">error</option>
        </select>
        <select
          className="h-9 rounded-md border bg-background px-2 text-sm"
          value={stage}
          onChange={(e) => setStage(e.target.value as Stage)}
          data-testid="select-log-stage"
          aria-label="Этап"
        >
          <option value="all">Все этапы</option>
          <option value="extract">extract</option>
          <option value="staging">staging</option>
          <option value="normalize">normalize</option>
          <option value="validate">validate</option>
          <option value="load">load</option>
        </select>
        <Button type="button" variant="outline" onClick={copyAll} data-testid="button-log-copy">
          Копировать
        </Button>
        <Button type="button" variant="outline" onClick={() => setWrap((w) => !w)} data-testid="button-log-wrap">
          {wrap ? "Без переноса" : "Перенос строк"}
        </Button>
        <Button type="button" variant="outline" data-testid="button-log-download">
          Скачать
        </Button>
      </div>
      <pre
        className={cn("max-h-72 overflow-auto rounded-md bg-muted p-3 font-mono text-xs", wrap ? "whitespace-pre-wrap" : "whitespace-pre")}
        data-testid="log-content"
      >
        {text}
      </pre>
    </div>
  );
}
