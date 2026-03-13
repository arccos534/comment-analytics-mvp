import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDate } from "@/lib/utils";
import { Source } from "@/types/source";

import { SourceStatusBadge } from "./source-status-badge";

export function SourceTable({ sources }: { sources: Source[] }) {
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
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
