/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Initiatives
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "react-router";
import { Link2, Plus, Target, Trash2, X } from "lucide-react";
// plane imports
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
// components
import { PageHead } from "@/components/core/page-title";
// hooks
import { useProject } from "@/hooks/store/use-project";
import { useUserPermissions } from "@/hooks/store/user";
// services
import { InitiativeService, type TInitiative, type TInitiativeStatus } from "@/services/initiative.service";

const initiativeService = new InitiativeService();

// `label` adalah KUNCI i18n, diterjemahkan saat dirender.
const STATUS: { value: TInitiativeStatus; label: string; cls: string }[] = [
  { value: "PLANNED", label: "initiatives_ui.status.planned", cls: "bg-layer-3 text-secondary" },
  { value: "ACTIVE", label: "initiatives_ui.status.active", cls: "bg-amber-500/10 text-amber-600" },
  { value: "ON_HOLD", label: "initiatives_ui.status.on_hold", cls: "bg-layer-3 text-tertiary" },
  { value: "COMPLETED", label: "initiatives_ui.status.completed", cls: "bg-green-500/10 text-green-600" },
];

const inputClass = "rounded border border-subtle bg-layer-1 px-2 py-1 text-xs outline-none focus:border-accent";

function InitiativesPage() {
  const { t } = useTranslation();
  const { workspaceSlug } = useParams();
  // store
  const { workspaceProjectIds, getProjectById } = useProject();
  const { allowPermissions } = useUserPermissions();
  // state
  const [initiatives, setInitiatives] = useState<TInitiative[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [newName, setNewName] = useState("");
  const [linkDrafts, setLinkDrafts] = useState<Record<string, string>>({});

  const isWorkspaceAdmin = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.WORKSPACE);

  const fetchInitiatives = useCallback(async () => {
    if (!workspaceSlug) return;
    try {
      const res = await initiativeService.list(workspaceSlug);
      setInitiatives(res ?? []);
    } catch {
      // biarkan kosong
    } finally {
      setIsLoading(false);
    }
  }, [workspaceSlug]);

  useEffect(() => {
    void fetchInitiatives();
  }, [fetchInitiatives]);

  const handleCreate = async () => {
    if (!newName.trim() || !workspaceSlug) return;
    try {
      await initiativeService.create(workspaceSlug, { name: newName.trim() });
      setNewName("");
      await fetchInitiatives();
      setToast({ type: TOAST_TYPE.SUCCESS, title: t("initiatives_ui.saved"), message: t("initiatives_ui.created") });
    } catch (err) {
      const message = (err as { error?: string })?.error ?? t("initiatives_ui.create_failed");
      setToast({ type: TOAST_TYPE.ERROR, title: t("initiatives_ui.failed"), message });
    }
  };

  const handleStatusChange = async (item: TInitiative, statusValue: TInitiativeStatus) => {
    if (!workspaceSlug) return;
    try {
      await initiativeService.update(workspaceSlug, item.id, { status: statusValue });
      await fetchInitiatives();
    } catch {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("initiatives_ui.failed"),
        message: t("initiatives_ui.status_failed"),
      });
    }
  };

  const handleDelete = async (item: TInitiative) => {
    if (!workspaceSlug) return;
    if (!window.confirm(t("initiatives_ui.confirm_delete", { name: item.name }))) return;
    try {
      await initiativeService.remove(workspaceSlug, item.id);
      await fetchInitiatives();
    } catch {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("initiatives_ui.failed"),
        message: t("initiatives_ui.delete_failed"),
      });
    }
  };

  const handleLink = async (item: TInitiative) => {
    const projectId = linkDrafts[item.id];
    if (!projectId || !workspaceSlug) return;
    try {
      await initiativeService.linkProject(workspaceSlug, item.id, projectId);
      setLinkDrafts((prev) => ({ ...prev, [item.id]: "" }));
      await fetchInitiatives();
    } catch (err) {
      const message = (err as { error?: string })?.error ?? t("initiatives_ui.link_failed");
      setToast({ type: TOAST_TYPE.ERROR, title: t("initiatives_ui.failed"), message });
    }
  };

  const handleUnlink = async (item: TInitiative, projectId: string) => {
    if (!workspaceSlug) return;
    try {
      await initiativeService.unlinkProject(workspaceSlug, item.id, projectId);
      await fetchInitiatives();
    } catch {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("initiatives_ui.failed"),
        message: t("initiatives_ui.unlink_failed"),
      });
    }
  };

  if (!workspaceSlug) return <></>;

  const availableProjects = (item: TInitiative) =>
    (workspaceProjectIds ?? []).filter((pid) => !item.project_ids.includes(pid));

  return (
    <div className="h-full w-full overflow-y-auto px-6 py-5">
      <PageHead title="Initiatives" />
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-1 border-b border-subtle pb-3">
          <div className="flex items-center gap-2">
            <Target className="size-5 text-secondary" />
            <h2 className="text-lg font-semibold text-primary">Initiatives</h2>
          </div>
          <p className="text-sm text-tertiary">{t("initiatives_ui.description")}</p>
        </div>

        {isWorkspaceAdmin && (
          <div className="flex items-center gap-2">
            <input
              type="text"
              placeholder={t("initiatives_ui.name_placeholder")}
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void handleCreate();
              }}
              className={`${inputClass} w-80`}
            />
            <button
              type="button"
              onClick={handleCreate}
              className="bg-accent text-xs flex items-center gap-1 rounded px-2.5 py-1 font-medium text-on-color"
            >
              <Plus className="size-3.5" /> {t("initiatives_ui.create")}
            </button>
          </div>
        )}

        {isLoading ? (
          <p className="text-sm text-tertiary">{t("chat_ui.loading")}</p>
        ) : initiatives.length === 0 ? (
          <p className="text-sm text-tertiary">{t("initiatives_ui.empty")}</p>
        ) : (
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            {initiatives.map((item) => {
              const pct = item.issues_total > 0 ? Math.round((item.issues_completed / item.issues_total) * 100) : 0;
              const statusInfo = STATUS.find((s) => s.value === item.status) ?? STATUS[0];
              return (
                <div key={item.id} className="flex flex-col gap-2.5 rounded-md border border-subtle px-4 py-3">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-semibold text-primary">{item.name}</p>
                    <div className="flex shrink-0 items-center gap-2">
                      {isWorkspaceAdmin ? (
                        <select
                          value={item.status}
                          onChange={(e) => void handleStatusChange(item, e.target.value as TInitiativeStatus)}
                          className={`rounded px-1.5 py-0.5 text-[11px] font-medium outline-none ${statusInfo.cls}`}
                        >
                          {STATUS.map((s) => (
                            <option key={s.value} value={s.value}>
                              {t(s.label)}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <span className={`rounded px-1.5 py-0.5 text-[11px] font-medium ${statusInfo.cls}`}>
                          {t(statusInfo.label)}
                        </span>
                      )}
                      {isWorkspaceAdmin && (
                        <button
                          type="button"
                          onClick={() => handleDelete(item)}
                          aria-label={t("initiatives_ui.delete_named", { name: item.name })}
                        >
                          <Trash2 className="hover:text-red-500 size-4 text-tertiary" />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Progress */}
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-layer-3">
                      <div className="h-full rounded-full bg-[#ED1F24]" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="text-xs shrink-0 text-tertiary">
                      {item.issues_completed}/{item.issues_total} · {pct}%
                    </span>
                  </div>

                  {/* Divisi tertaut */}
                  <div className="flex flex-wrap items-center gap-1.5">
                    {item.project_ids.map((pid) => {
                      const proj = getProjectById(pid);
                      if (!proj) return null;
                      return (
                        <span
                          key={pid}
                          className="flex items-center gap-1 rounded-full border border-subtle px-2 py-0.5 text-[11px] text-secondary"
                        >
                          {proj.name}
                          {isWorkspaceAdmin && (
                            <button
                              type="button"
                              onClick={() => handleUnlink(item, pid)}
                              aria-label={t("initiatives_ui.unlink_named", { name: proj.name })}
                            >
                              <X className="hover:text-red-500 size-3 text-tertiary" />
                            </button>
                          )}
                        </span>
                      );
                    })}
                    {isWorkspaceAdmin && availableProjects(item).length > 0 && (
                      <span className="flex items-center gap-1">
                        <select
                          value={linkDrafts[item.id] ?? ""}
                          onChange={(e) => setLinkDrafts((prev) => ({ ...prev, [item.id]: e.target.value }))}
                          className={`${inputClass} text-[11px]`}
                        >
                          <option value="">{t("initiatives_ui.link_placeholder")}</option>
                          {availableProjects(item).map((pid) => {
                            const proj = getProjectById(pid);
                            if (!proj) return null;
                            return (
                              <option key={pid} value={pid}>
                                {proj.name}
                              </option>
                            );
                          })}
                        </select>
                        <button
                          type="button"
                          onClick={() => handleLink(item)}
                          aria-label={t("initiatives_ui.link_division")}
                          className="rounded border border-subtle p-1 text-secondary hover:bg-layer-2"
                        >
                          <Link2 className="size-3.5" />
                        </button>
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default observer(InitiativesPage);
