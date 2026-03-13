"use client";

import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { IndexPeriodPreset, StartIndexingPayload } from "@/types/source";

type IndexModeUi = "full" | "latest_posts" | "period";
type PeriodOption = IndexPeriodPreset | "custom";

const modeButtonClass =
  "rounded-xl border border-border/70 bg-card/50 px-3 py-2 text-sm text-muted-foreground transition hover:border-primary/40 hover:text-foreground data-[active=true]:border-primary data-[active=true]:bg-primary/15 data-[active=true]:text-foreground";

export function IndexingControls({
  disabled,
  isPending,
  onStart,
}: {
  disabled: boolean;
  isPending: boolean;
  onStart: (payload: StartIndexingPayload) => void;
}) {
  const [mode, setMode] = useState<IndexModeUi>("latest_posts");
  const [latestPostsLimit, setLatestPostsLimit] = useState("100");
  const [periodOption, setPeriodOption] = useState<PeriodOption>("month");
  const [periodFrom, setPeriodFrom] = useState("");
  const [periodTo, setPeriodTo] = useState("");

  const payload = useMemo<StartIndexingPayload | null>(() => {
    if (mode === "full") {
      return { mode: "full" };
    }

    if (mode === "latest_posts") {
      const parsedLimit = Number.parseInt(latestPostsLimit, 10);
      if (!Number.isFinite(parsedLimit) || parsedLimit <= 0) {
        return null;
      }
      return { mode: "latest_posts", latest_posts_limit: parsedLimit };
    }

    if (periodOption === "custom") {
      if (!periodFrom) {
        return null;
      }
      return {
        mode: "custom_period",
        period_from: new Date(`${periodFrom}T00:00:00`).toISOString(),
        period_to: periodTo ? new Date(`${periodTo}T23:59:59`).toISOString() : null,
      };
    }

    return {
      mode: "preset_period",
      period_preset: periodOption,
    };
  }, [latestPostsLimit, mode, periodFrom, periodOption, periodTo]);

  const helperText =
    mode === "full"
      ? "Полный backfill всех доступных постов и комментариев. Самый долгий режим."
      : mode === "latest_posts"
        ? "Быстрый режим для первичной проверки источников."
        : "Ограничивает индекс по времени, чтобы не тянуть весь архив.";

  return (
    <Card className="bg-white/5">
      <CardHeader>
        <CardTitle>Indexing scope</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-2 md:grid-cols-3">
          <button className={cn(modeButtonClass)} data-active={mode === "full"} onClick={() => setMode("full")} type="button">
            All history
          </button>
          <button
            className={cn(modeButtonClass)}
            data-active={mode === "latest_posts"}
            onClick={() => setMode("latest_posts")}
            type="button"
          >
            Latest N posts
          </button>
          <button className={cn(modeButtonClass)} data-active={mode === "period"} onClick={() => setMode("period")} type="button">
            By period
          </button>
        </div>

        {mode === "latest_posts" ? (
          <div className="space-y-2">
            <Label htmlFor="latest-posts-limit">How many latest posts to fetch</Label>
            <Input
              id="latest-posts-limit"
              className="bg-card/70"
              inputMode="numeric"
              min={1}
              placeholder="100"
              type="number"
              value={latestPostsLimit}
              onChange={(event) => setLatestPostsLimit(event.target.value)}
            />
          </div>
        ) : null}

        {mode === "period" ? (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="period-preset">Period preset</Label>
              <Select
                id="period-preset"
                className="bg-card/70"
                value={periodOption}
                onChange={(event) => setPeriodOption(event.target.value as PeriodOption)}
              >
                <option value="day">Last day</option>
                <option value="week">Last week</option>
                <option value="month">Last month</option>
                <option value="three_months">Last 3 months</option>
                <option value="six_months">Last 6 months</option>
                <option value="year">Last year</option>
                <option value="custom">Custom range</option>
              </Select>
            </div>

            {periodOption === "custom" ? (
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="period-from">From</Label>
                  <Input
                    id="period-from"
                    className="bg-card/70"
                    type="date"
                    value={periodFrom}
                    onChange={(event) => setPeriodFrom(event.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="period-to">To</Label>
                  <Input
                    id="period-to"
                    className="bg-card/70"
                    type="date"
                    value={periodTo}
                    onChange={(event) => setPeriodTo(event.target.value)}
                  />
                </div>
              </div>
            ) : null}
          </div>
        ) : null}

        <div className="rounded-xl border border-border/60 bg-background/50 px-3 py-2 text-sm text-muted-foreground">
          {helperText}
        </div>

        <Button disabled={disabled || isPending || !payload} onClick={() => payload && onStart(payload)}>
          {isPending ? "Indexing..." : "Start indexing"}
        </Button>
      </CardContent>
    </Card>
  );
}
