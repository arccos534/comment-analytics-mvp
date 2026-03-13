"use client";

import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { useAddSources, useValidateSources } from "@/hooks/use-sources";

export function SourceInputForm({ projectId }: { projectId: string }) {
  const [value, setValue] = useState("");
  const validateSources = useValidateSources();
  const addSources = useAddSources(projectId);

  const urls = useMemo(() => value.split("\n").map((line) => line.trim()).filter(Boolean), [value]);

  async function handleValidate() {
    await validateSources.mutateAsync([value]);
  }

  async function handleAdd() {
    await addSources.mutateAsync([value]);
    setValue("");
  }

  return (
    <Card className="border-white/10 bg-card/70 backdrop-blur">
      <CardHeader>
        <CardTitle>Добавить источники</CardTitle>
        <CardDescription>
          Вставьте ссылки на открытые Telegram-каналы, Telegram-посты, VK-сообщества или VK-посты.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Textarea
          placeholder={"https://t.me/example\nhttps://vk.com/wall-1_123"}
          value={value}
          onChange={(event) => setValue(event.target.value)}
        />
        <div className="flex flex-wrap gap-3">
          <Button variant="secondary" onClick={handleValidate} disabled={!urls.length || validateSources.isPending}>
            Validate
          </Button>
          <Button onClick={handleAdd} disabled={!urls.length || addSources.isPending}>
            Add sources
          </Button>
        </div>

        {validateSources.data?.length ? (
          <div className="rounded-2xl border border-border/60 bg-background/60 p-4 text-sm">
            {validateSources.data.map((item) => (
              <div key={item.url} className="flex justify-between gap-3 py-1">
                <span className="truncate">{item.normalized_url || item.url}</span>
                <span className={item.is_valid ? "text-emerald-400" : "text-rose-400"}>
                  {item.is_valid ? `${item.platform}/${item.source_type}` : item.reason}
                </span>
              </div>
            ))}
          </div>
        ) : null}

        {addSources.data?.skipped.length ? (
          <div className="rounded-2xl border border-amber-500/20 bg-amber-500/10 p-4 text-sm text-amber-200">
            Пропущено: {addSources.data.skipped.map((item) => item.normalized_url || item.url).join(", ")}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
