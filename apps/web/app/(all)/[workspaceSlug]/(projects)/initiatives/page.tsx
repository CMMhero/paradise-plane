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
import { Badge } from "@plane/propel/badge";
import type { TBadgeVariant } from "@plane/propel/badge";
import { Button } from "@plane/propel/button";
import { IconButton } from "@plane/propel/icon-button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { CustomSearchSelect, CustomSelect, Input } from "@plane/ui";
// components
import { TintedIconBox, tintHueFromKey } from "@/components/common/tint";
import { PageHead } from "@/components/core/page-title";
// hooks
import { useProject } from "@/hooks/store/use-project";
import { useUserPermissions } from "@/hooks/store/user";
// services
import { InitiativeService, type TInitiative, type TInitiativeStatus } from "@/services/initiative.service";

const initiativeService = new InitiativeService();

// `label` adalah KUNCI i18n, diterjemahkan saat dirender.
const STATUS: { value: TInitiativeStatus; label: string; variant: TBadgeVariant }[] = [
  { value: "PLANNED", label: "initiatives_ui.status.planned", variant: "brand" },
  { value: "ACTIVE", label: "initiatives_ui.status.active", variant: "warning" },
  { value: "ON_HOLD", label: "initiatives_ui.status.on_hold", variant: "neutral" },
  { value: "COMPLETED", label: "initiatives_ui.status.completed", variant: "success" },
];

const inputClass =
  "rounded-field border border-subtle bg-layer-1 px-2 py-1 text-12 outline-none focus:border-accent-strong";

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
    // oxlint-disable-next-line react/set-state-in-effect -- initial data load triggers state updates by design
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
            <h2 className="text-16 font-semibold text-primary">Initiatives</h2>
          </div>
          <p className="text-13 text-tertiary">{t("initiatives_ui.description")}</p>
        </div>

        {isWorkspaceAdmin && (
          <div className="flex items-center gap-2">
            <Input
              type="text"
              placeholder={t("initiatives_ui.name_placeholder")}
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void handleCreate();
              }}
              className={`${inputClass} w-80`}
            />
            <Button variant="primary" size="base" prependIcon={<Plus />} onClick={handleCreate}>
              {t("initiatives_ui.create")}
            </Button>
          </div>
        )}

        {isLoading ? (
          <p className="text-13 text-tertiary">{t("chat_ui.loading")}</p>
        ) : initiatives.length === 0 ? (
          <p className="text-13 text-tertiary">{t("initiatives_ui.empty")}</p>
        ) : (
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            {initiatives.map((item) => {
              const pct = item.issues_total > 0 ? Math.round((item.issues_completed / item.issues_total) * 100) : 0;
              const statusInfo = STATUS.find((s) => s.value === item.status) ?? STATUS[0];
              return (
                <div
                  key={item.id}
                  className="flex flex-col gap-2.5 rounded-card border border-subtle bg-layer-1 px-4 py-3"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex min-w-0 items-center gap-2">
                      <TintedIconBox hue={tintHueFromKey(item.id)}>
                        <Target />
                      </TintedIconBox>
                      <p className="text-13 font-semibold text-primary">{item.name}</p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      {isWorkspaceAdmin ? (
                        <CustomSelect
                          value={item.status}
                          onChange={(v: TInitiativeStatus) => void handleStatusChange(item, v)}
                          customButton={<Badge variant={statusInfo.variant}>{t(statusInfo.label)}</Badge>}
                          placement="bottom-end"
                        >
                          {STATUS.map((s) => (
                            <CustomSelect.Option key={s.value} value={s.value}>
                              {t(s.label)}
                            </CustomSelect.Option>
                          ))}
                        </CustomSelect>
                      ) : (
                        <Badge variant={statusInfo.variant}>{t(statusInfo.label)}</Badge>
                      )}
                      {isWorkspaceAdmin && (
                        <IconButton
                          variant="ghost"
                          size="base"
                          icon={Trash2}
                          onClick={() => handleDelete(item)}
                          aria-label={t("initiatives_ui.delete_named", { name: item.name })}
                        />
                      )}
                    </div>
                  </div>

                  {/* Progress */}
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 flex-1 overflow-hidden rounded-control bg-layer-1">
                      <div className="h-full rounded-control bg-accent-primary" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="shrink-0 text-12 text-tertiary">
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
                          className="flex items-center gap-1 rounded-control border border-subtle px-2 py-0.5 text-11 text-secondary"
                        >
                          {proj.name}
                          {isWorkspaceAdmin && (
                            <button
                              type="button"
                              onClick={() => handleUnlink(item, pid)}
                              aria-label={t("initiatives_ui.unlink_named", { name: proj.name })}
                            >
                              <X className="size-3 text-tertiary hover:text-danger-primary" />
                            </button>
                          )}
                        </span>
                      );
                    })}
                    {isWorkspaceAdmin && availableProjects(item).length > 0 && (
                      <span className="flex items-center gap-1">
                        <CustomSearchSelect
                          value={linkDrafts[item.id] ?? ""}
                          onChange={(v: string) => setLinkDrafts((prev) => ({ ...prev, [item.id]: v }))}
                          label={
                            getProjectById(linkDrafts[item.id] ?? "")?.name ?? t("initiatives_ui.link_placeholder")
                          }
                          options={availableProjects(item).flatMap((pid) => {
                            const proj = getProjectById(pid);
                            return proj ? [{ value: pid, query: proj.name, content: proj.name }] : [];
                          })}
                          placement="bottom-start"
                        />
                        <IconButton
                          variant="secondary"
                          size="sm"
                          icon={Link2}
                          onClick={() => handleLink(item)}
                          aria-label={t("initiatives_ui.link_division")}
                        />
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
