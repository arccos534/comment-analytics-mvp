import { Badge } from "@/components/ui/badge";
import { SourceStatus } from "@/types/source";

const variantMap: Record<SourceStatus, "default" | "success" | "warning" | "destructive" | "info"> = {
  pending: "warning",
  valid: "info",
  invalid: "destructive",
  indexing: "info",
  ready: "success",
  failed: "destructive"
};

export function SourceStatusBadge({ status }: { status: SourceStatus }) {
  return <Badge variant={variantMap[status]}>{status}</Badge>;
}
