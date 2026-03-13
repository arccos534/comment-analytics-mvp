 "use client";

import { Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDate } from "@/lib/utils";
import { Source } from "@/types/source";
import { useDeleteSource } from "@/hooks/use-sources";

import { SourceStatusBadge } from "./source-status-badge";

export function SourceTable({ projectId, sources }: { projectId: string; sources: Source[] }) {
  const deleteSource = useDeleteSource(projectId);

  const handleDelete = async (source: Source) => {
    const confirmed = window.confirm(`Delete source "${source.title || source.source_url}"?`);
    if (!confirmed) {
      return;
    }

    try {
      await deleteSource.mutateAsync(source.id);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to delete source";
      window.alert(message);
    }
  };

  return (
    <div className="overflow-hidden rounded-2xl border border-white/10 bg-card/70 backdrop-blur">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Source</TableHead>
            <TableHead>Platform</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Last indexed</TableHead>
            <TableHead className="w-[72px] text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sources.map((source) => (
            <TableRow key={source.id}>
              <TableCell>
                <div className="font-medium">{source.title || source.source_url}</div>
                <div className="text-xs text-muted-foreground">{source.source_url}</div>
              </TableCell>
              <TableCell className="capitalize">{source.platform}</TableCell>
              <TableCell className="capitalize">{source.source_type}</TableCell>
              <TableCell>
                <SourceStatusBadge status={source.status} />
              </TableCell>
              <TableCell>{formatDate(source.last_indexed_at)}</TableCell>
              <TableCell className="text-right">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-9 w-9 p-0 text-rose-300 hover:bg-rose-500/10 hover:text-rose-200"
                  disabled={deleteSource.isPending}
                  onClick={() => void handleDelete(source)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
