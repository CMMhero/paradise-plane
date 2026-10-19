/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Time Tracking
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useState } from "react";
import { observer } from "mobx-react";
import { Clock, Plus, Trash2 } from "lucide-react";
// plane imports
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
// hooks
import { useUser } from "@/hooks/store/user";
// services
import { IssueWorkLogService, type TIssueWorkLog } from "@/services/issue/issue_worklog.service";

type TIssueWorklogProperty = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
  disabled: boolean;
};

const worklogService = new IssueWorkLogService();

const formatDuration = (minutes: number): string => {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h > 0 && m > 0) return `${h}j ${m}m`;
  if (h > 0) return `${h}j`;
  return `${m}m`;
};

const displayName = (log: TIssueWorkLog): string => {
  const d = log.logged_by_detail;
  if (!d) return "Anggota";
  return d.display_name || [d.first_name, d.last_name].filter(Boolean).join(" ") || "Anggota";
};

export const IssueWorklogProperty = observer(function IssueWorklogProperty(props: TIssueWorklogProperty) {
  const { workspaceSlug, projectId, issueId, disabled } = props;
  // store
  const { data: currentUser } = useUser();
  // state
  const [logs, setLogs] = useState<TIssueWorkLog[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [hours, setHours] = useState("");
  const [minutes, setMinutes] = useState("");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchLogs = useCallback(async () => {
    if (!workspaceSlug || !projectId || !issueId) return;
    try {
      const res = await worklogService.list(workspaceSlug, projectId, issueId);
      setLogs(res.work_logs ?? []);
      setTotal(res.total_duration ?? 0);
    } catch {
      // senyap: sidebar tak boleh crash kalau gagal muat
    } finally {
      setIsLoading(false);
    }
  }, [workspaceSlug, projectId, issueId]);

  useEffect(() => {
    void fetchLogs();
  }, [fetchLogs]);

  const handleAdd = async () => {
    const duration = (parseInt(hours || "0", 10) || 0) * 60 + (parseInt(minutes || "0", 10) || 0);
    if (duration <= 0) {
      setToast({ type: TOAST_TYPE.ERROR, title: "Durasi kosong", message: "Isi jam atau menit lebih dari 0." });
      return;
    }
    setIsSubmitting(true);
    try {
      await worklogService.create(workspaceSlug, projectId, issueId, { duration, description: description.trim() });
      setHours("");
      setMinutes("");
      setDescription("");
      await fetchLogs();
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: "Tercatat",
        message: `Waktu ${formatDuration(duration)} ditambahkan.`,
      });
    } catch (err: unknown) {
      const message = (err as { error?: string })?.error ?? "Gagal menyimpan catatan waktu.";
      setToast({ type: TOAST_TYPE.ERROR, title: "Gagal", message });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (log: TIssueWorkLog) => {
    try {
      await worklogService.remove(workspaceSlug, projectId, issueId, log.id);
      await fetchLogs();
      setToast({ type: TOAST_TYPE.SUCCESS, title: "Dihapus", message: "Catatan waktu dihapus." });
    } catch (err: unknown) {
      const message = (err as { error?: string })?.error ?? "Gagal menghapus.";
      setToast({ type: TOAST_TYPE.ERROR, title: "Gagal", message });
    }
  };

  if (isLoading) return <></>;

  return (
    <div className="flex w-full flex-col gap-2 border-t border-subtle py-3">
      <div className="flex items-center justify-between">
        <div className="text-sm flex items-center gap-1.5 text-secondary">
          <Clock className="size-4" />
          <span>Pelacakan Waktu</span>
        </div>
        {total > 0 && (
          <span className="text-xs rounded bg-layer-3 px-1.5 py-0.5 font-medium text-primary">
            {formatDuration(total)}
          </span>
        )}
      </div>

      {logs.length > 0 && (
        <div className="flex flex-col gap-1">
          {logs.map((log) => {
            const canDelete = !disabled && currentUser?.id === log.logged_by;
            return (
              <div
                key={log.id}
                className="group flex items-start justify-between gap-2 rounded px-1 py-1 hover:bg-layer-2"
              >
                <div className="min-w-0">
                  <div className="text-xs flex items-center gap-1.5">
                    <span className="font-medium text-primary">{formatDuration(log.duration)}</span>
                    <span className="text-tertiary">·</span>
                    <span className="truncate text-tertiary">{displayName(log)}</span>
                  </div>
                  {log.description && <p className="text-xs truncate text-tertiary">{log.description}</p>}
                </div>
                {canDelete && (
                  <button
                    type="button"
                    onClick={() => handleDelete(log)}
                    className="opacity-0 transition group-hover:opacity-100"
                    aria-label="Hapus catatan waktu"
                  >
                    <Trash2 className="hover:text-red-500 size-3.5 text-tertiary" />
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}

      {!disabled && (
        <div className="flex items-center gap-1.5">
          <input
            type="number"
            min={0}
            placeholder="jam"
            value={hours}
            onChange={(e) => setHours(e.target.value)}
            className="text-xs focus:border-accent w-14 rounded border border-subtle bg-layer-1 px-1.5 py-1 outline-none"
          />
          <input
            type="number"
            min={0}
            max={59}
            placeholder="menit"
            value={minutes}
            onChange={(e) => setMinutes(e.target.value)}
            className="text-xs focus:border-accent w-16 rounded border border-subtle bg-layer-1 px-1.5 py-1 outline-none"
          />
          <input
            type="text"
            placeholder="keterangan (opsional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="text-xs focus:border-accent min-w-0 flex-1 rounded border border-subtle bg-layer-1 px-1.5 py-1 outline-none"
          />
          <button
            type="button"
            disabled={isSubmitting}
            onClick={handleAdd}
            className="bg-accent text-xs flex items-center gap-1 rounded px-2 py-1 font-medium text-on-color disabled:opacity-50"
            aria-label="Tambah catatan waktu"
          >
            <Plus className="size-3.5" />
          </button>
        </div>
      )}
    </div>
  );
});
