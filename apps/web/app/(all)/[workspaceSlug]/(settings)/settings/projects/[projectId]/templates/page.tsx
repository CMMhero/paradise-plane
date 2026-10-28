/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Settings Templates & Recurring Work Items
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "react-router";
import { CalendarClock, FileStack, Play, Plus, Trash2 } from "lucide-react";
// plane imports
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
// components
import { NotAuthorizedView } from "@/components/auth-screens/not-authorized-view";
import { PageHead } from "@/components/core/page-title";
import { SettingsContentWrapper } from "@/components/settings/content-wrapper";
// hooks
import { useProject } from "@/hooks/store/use-project";
import { useUserPermissions } from "@/hooks/store/user";
// services
import {
  IssueTemplatesService,
  type TIssueTemplate,
  type TRecurringIssue,
  type TRecurringInterval,
} from "@/services/issue/issue_templates.service";

const templatesService = new IssueTemplatesService();

// `label` adalah KUNCI i18n, diterjemahkan saat dirender.
const INTERVALS: { value: TRecurringInterval; label: string }[] = [
  { value: "DAILY", label: "templates_ui.interval.daily" },
  { value: "WEEKLY", label: "templates_ui.interval.weekly" },
  { value: "MONTHLY", label: "templates_ui.interval.monthly" },
];

const labelInterval = (nilai: TRecurringInterval, t: (key: string) => string): string => {
  const label = INTERVALS.find((i) => i.value === nilai)?.label;
  return label ? t(label) : nilai;
};

const PRIORITIES = ["none", "low", "medium", "high", "urgent"];

const inputClass = "rounded border border-subtle bg-layer-1 px-2 py-1 text-xs outline-none focus:border-accent";

const toastError = (err: unknown, fallback: string, t: (key: string) => string) => {
  const message = (err as { error?: string })?.error ?? fallback;
  setToast({ type: TOAST_TYPE.ERROR, title: t("templates_ui.failed"), message });
};

function TemplatesSettingsPage() {
  const { t, currentLocale } = useTranslation();
  const { workspaceSlug, projectId } = useParams();
  // store
  const { currentProjectDetails } = useProject();
  const { workspaceUserInfo, allowPermissions } = useUserPermissions();
  // state
  const [templates, setTemplates] = useState<TIssueTemplate[]>([]);
  const [recurrences, setRecurrences] = useState<TRecurringIssue[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  // form template baru
  const [name, setName] = useState("");
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState("none");
  // form recurring per template: interval draft
  const [intervalDrafts, setIntervalDrafts] = useState<Record<string, TRecurringInterval>>({});

  const canAdmin = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.PROJECT);
  const pageTitle = currentProjectDetails?.name
    ? t("templates_ui.page_title", { name: currentProjectDetails.name })
    : undefined;

  const fetchAll = useCallback(async () => {
    if (!workspaceSlug || !projectId) return;
    try {
      const [tpl, rec] = await Promise.all([
        templatesService.listTemplates(workspaceSlug, projectId),
        templatesService.listRecurring(workspaceSlug, projectId),
      ]);
      setTemplates(tpl ?? []);
      setRecurrences(rec ?? []);
    } catch {
      // biarkan kosong bila gagal
    } finally {
      setIsLoading(false);
    }
  }, [workspaceSlug, projectId]);

  useEffect(() => {
    void fetchAll();
  }, [fetchAll]);

  const handleAddTemplate = async () => {
    if (!name.trim() || !title.trim() || !workspaceSlug || !projectId) return;
    try {
      await templatesService.createTemplate(workspaceSlug, projectId, {
        name: name.trim(),
        title: title.trim(),
        priority,
      });
      setName("");
      setTitle("");
      setPriority("none");
      await fetchAll();
      setToast({ type: TOAST_TYPE.SUCCESS, title: t("templates_ui.saved"), message: t("templates_ui.created") });
    } catch (err) {
      toastError(err, t("templates_ui.create_failed"), t);
    }
  };

  const handleDeleteTemplate = async (tpl: TIssueTemplate) => {
    if (!workspaceSlug || !projectId) return;
    if (!window.confirm(t("templates_ui.confirm_delete", { name: tpl.name }))) return;
    try {
      await templatesService.deleteTemplate(workspaceSlug, projectId, tpl.id);
      await fetchAll();
    } catch (err) {
      toastError(err, t("templates_ui.delete_failed"), t);
    }
  };

  const handleApply = async (tpl: TIssueTemplate) => {
    if (!workspaceSlug || !projectId) return;
    try {
      await templatesService.applyTemplate(workspaceSlug, projectId, tpl.id);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("templates_ui.applied_title"),
        message: t("templates_ui.applied_message", { name: tpl.name }),
      });
    } catch (err) {
      toastError(err, t("templates_ui.apply_failed"), t);
    }
  };

  const handleAddRecurring = async (tpl: TIssueTemplate) => {
    if (!workspaceSlug || !projectId) return;
    const interval = intervalDrafts[tpl.id] ?? "WEEKLY";
    try {
      await templatesService.createRecurring(workspaceSlug, projectId, {
        template: tpl.id,
        interval,
        next_run_at: new Date().toISOString(),
      });
      await fetchAll();
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("templates_ui.recurring_active"),
        message: t("templates_ui.recurring_installed"),
      });
    } catch (err) {
      toastError(err, t("templates_ui.recurring_install_failed"), t);
    }
  };

  const handleToggleRecurring = async (rec: TRecurringIssue) => {
    if (!workspaceSlug || !projectId) return;
    try {
      await templatesService.updateRecurring(workspaceSlug, projectId, rec.id, { is_active: !rec.is_active });
      await fetchAll();
    } catch (err) {
      toastError(err, t("templates_ui.recurring_toggle_failed"), t);
    }
  };

  const handleDeleteRecurring = async (rec: TRecurringIssue) => {
    if (!workspaceSlug || !projectId) return;
    try {
      await templatesService.deleteRecurring(workspaceSlug, projectId, rec.id);
      await fetchAll();
    } catch (err) {
      toastError(err, t("templates_ui.recurring_delete_failed"), t);
    }
  };

  if (workspaceUserInfo && !canAdmin) {
    return <NotAuthorizedView section="settings" isProjectView />;
  }
  if (!workspaceSlug || !projectId) return <></>;

  const recurrencesOf = (templateId: string) => recurrences.filter((r) => r.template === templateId);

  return (
    <SettingsContentWrapper>
      <PageHead title={pageTitle} />
      <div className="flex w-full flex-col gap-4">
        <div className="flex flex-col gap-1 border-b border-subtle pb-3">
          <div className="flex items-center gap-2">
            <FileStack className="size-5 text-secondary" />
            <h3 className="text-xl font-medium text-primary">{t("templates_ui.title")}</h3>
          </div>
          <p className="text-sm text-tertiary">{t("templates_ui.description")}</p>
        </div>

        {/* Form template baru */}
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="text"
            placeholder={t("templates_ui.name_placeholder")}
            value={name}
            onChange={(e) => setName(e.target.value)}
            className={`${inputClass} w-56`}
          />
          <input
            type="text"
            placeholder={t("templates_ui.title_placeholder")}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className={`${inputClass} w-64`}
          />
          <select value={priority} onChange={(e) => setPriority(e.target.value)} className={inputClass}>
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {t("templates_ui.priority_option", { value: p })}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={handleAddTemplate}
            className="bg-accent text-xs flex items-center gap-1 rounded px-2.5 py-1 font-medium text-on-color"
          >
            <Plus className="size-3.5" /> {t("templates_ui.add")}
          </button>
        </div>

        {/* Daftar template */}
        {isLoading ? (
          <p className="text-sm text-tertiary">{t("chat_ui.loading")}</p>
        ) : templates.length === 0 ? (
          <p className="text-sm text-tertiary">{t("templates_ui.empty")}</p>
        ) : (
          <div className="flex flex-col gap-2">
            {templates.map((tpl) => {
              const recs = recurrencesOf(tpl.id);
              return (
                <div key={tpl.id} className="rounded-md border border-subtle px-3 py-2">
                  <div className="flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-sm truncate font-medium text-primary">{tpl.name}</p>
                      <p className="text-xs truncate text-tertiary">
                        {t("templates_ui.summary_line", { title: tpl.title, priority: tpl.priority })}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <button
                        type="button"
                        onClick={() => handleApply(tpl)}
                        title={t("templates_ui.apply_now_hint")}
                        className="text-xs flex items-center gap-1 rounded border border-subtle px-2 py-1 text-secondary hover:bg-layer-2"
                      >
                        <Play className="size-3" /> {t("templates_ui.apply_now")}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteTemplate(tpl)}
                        aria-label={t("templates_ui.delete_named", { name: tpl.name })}
                      >
                        <Trash2 className="hover:text-red-500 size-4 text-tertiary" />
                      </button>
                    </div>
                  </div>

                  {/* Jadwal berulang */}
                  <div className="mt-2 flex flex-col gap-1 border-t border-subtle pt-2">
                    {recs.map((rec) => (
                      <div key={rec.id} className="text-xs flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <CalendarClock className="size-3.5 text-tertiary" />
                          <span className="text-secondary">
                            {labelInterval(rec.interval, t)} · {t("templates_ui.next")}:{" "}
                            {new Date(rec.next_run_at).toLocaleString(currentLocale)}
                          </span>
                          <span
                            className={`rounded px-1.5 py-0.5 text-[10px] ${rec.is_active ? "bg-green-500/10 text-green-600" : "bg-layer-3 text-tertiary"}`}
                          >
                            {rec.is_active ? t("templates_ui.active") : t("templates_ui.inactive")}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => handleToggleRecurring(rec)}
                            className="text-xs text-secondary underline-offset-2 hover:underline"
                          >
                            {rec.is_active ? t("templates_ui.turn_off") : t("templates_ui.turn_on")}
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDeleteRecurring(rec)}
                            aria-label={t("templates_ui.delete_schedule")}
                          >
                            <Trash2 className="hover:text-red-500 size-3.5 text-tertiary" />
                          </button>
                        </div>
                      </div>
                    ))}

                    <div className="flex items-center gap-1.5">
                      <select
                        value={intervalDrafts[tpl.id] ?? "WEEKLY"}
                        onChange={(e) =>
                          setIntervalDrafts((prev) => ({ ...prev, [tpl.id]: e.target.value as TRecurringInterval }))
                        }
                        className={inputClass}
                      >
                        {INTERVALS.map((i) => (
                          <option key={i.value} value={i.value}>
                            {t(i.label)}
                          </option>
                        ))}
                      </select>
                      <button
                        type="button"
                        onClick={() => handleAddRecurring(tpl)}
                        className="text-xs flex items-center gap-1 rounded border border-subtle px-2 py-1 text-secondary hover:bg-layer-2"
                      >
                        <Plus className="size-3" /> {t("templates_ui.recurring")}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </SettingsContentWrapper>
  );
}

export default observer(TemplatesSettingsPage);
