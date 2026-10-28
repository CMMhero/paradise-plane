/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Custom Properties di sidebar work item
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { observer } from "mobx-react";
import { Shapes } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useMember } from "@/hooks/store/use-member";
// services
import {
  WorkItemTypesService,
  type TWorkItemType,
  type TWorkItemProperty,
  type TWorkItemPropertyValue,
} from "@/services/issue/issue_types.service";

export type TWorkItemAdditionalSidebarProperties = {
  workItemId: string;
  workItemTypeId: string | null;
  projectId: string;
  workspaceSlug: string;
  isEditable: boolean;
  isPeekView?: boolean;
};

const typesService = new WorkItemTypesService();

const inputClass = "w-full rounded border border-subtle bg-layer-1 px-2 py-1 text-xs outline-none focus:border-accent";

export const WorkItemAdditionalSidebarProperties = observer(function WorkItemAdditionalSidebarProperties(
  props: TWorkItemAdditionalSidebarProperties
) {
  const { t } = useTranslation();
  const { workItemId, workItemTypeId, projectId, workspaceSlug, isEditable } = props;
  // store
  const { updateIssue } = useIssueDetail();
  const {
    getUserDetails,
    project: { getProjectMemberIds },
  } = useMember();
  // state
  const [types, setTypes] = useState<TWorkItemType[]>([]);
  const [properties, setProperties] = useState<TWorkItemProperty[]>([]);
  const [values, setValues] = useState<Record<string, TWorkItemPropertyValue>>({});
  const [isReady, setIsReady] = useState(false);

  const memberIds = getProjectMemberIds(projectId, false) ?? [];

  // Muat daftar tipe project (sekali per project)
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const res = await typesService.listTypes(workspaceSlug, projectId);
        if (!cancelled) setTypes(res ?? []);
      } catch {
        // project tanpa fitur tipe: biarkan kosong
      } finally {
        if (!cancelled) setIsReady(true);
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [workspaceSlug, projectId]);

  // Muat definisi field + nilai saat tipe work item berubah
  const fetchPropertiesAndValues = useCallback(async () => {
    if (!workItemTypeId) {
      setProperties([]);
      setValues({});
      return;
    }
    try {
      const [props_, vals] = await Promise.all([
        typesService.listProperties(workspaceSlug, projectId, workItemTypeId),
        typesService.listValues(workspaceSlug, projectId, workItemId),
      ]);
      setProperties((props_ ?? []).filter((p) => p.is_active));
      const map: Record<string, TWorkItemPropertyValue> = {};
      for (const v of vals ?? []) map[v.property] = v;
      setValues(map);
    } catch {
      // gagal muat → sidebar tetap hidup tanpa blok custom
    }
  }, [workspaceSlug, projectId, workItemId, workItemTypeId]);

  useEffect(() => {
    void fetchPropertiesAndValues();
  }, [fetchPropertiesAndValues]);

  const handleTypeChange = async (typeId: string) => {
    try {
      await updateIssue(workspaceSlug, projectId, workItemId, { type_id: typeId || null });
    } catch {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("work_item_extra_ui.failed"),
        message: t("work_item_extra_ui.type_change_failed"),
      });
    }
  };

  const handleValueChange = async (prop: TWorkItemProperty, patch: Partial<TWorkItemPropertyValue>) => {
    try {
      const saved = await typesService.setValue(workspaceSlug, projectId, workItemId, {
        property: prop.id,
        ...patch,
      });
      setValues((prev) => ({ ...prev, [prop.id]: saved }));
    } catch (err: unknown) {
      const message = (err as { error?: string })?.error ?? t("work_item_extra_ui.value_save_failed");
      setToast({ type: TOAST_TYPE.ERROR, title: t("work_item_extra_ui.failed"), message });
    }
  };

  const selectedType = useMemo(() => types.find((tipe) => tipe.id === workItemTypeId), [types, workItemTypeId]);

  // Project tanpa tipe terdefinisi → tidak menampilkan apa pun (fitur senyap)
  if (!isReady || types.length === 0) return <></>;

  return (
    <div className="flex w-full flex-col gap-2 border-t border-subtle py-3">
      <div className="text-sm flex items-center gap-1.5 text-secondary">
        <Shapes className="size-4" />
        <span>{t("work_item_extra_ui.title")}</span>
      </div>

      {/* Selektor tipe */}
      <div className="flex items-center gap-2">
        <span className="text-xs w-24 shrink-0 text-tertiary">{t("work_item_extra_ui.type")}</span>
        <select
          value={workItemTypeId ?? ""}
          disabled={!isEditable}
          onChange={(e) => void handleTypeChange(e.target.value)}
          className={inputClass}
        >
          <option value="">{t("work_item_extra_ui.no_type")}</option>
          {types.map((tipe) => (
            <option key={tipe.id} value={tipe.id}>
              {tipe.name}
            </option>
          ))}
        </select>
      </div>

      {/* Field dinamis sesuai tipe */}
      {selectedType &&
        properties.map((prop) => {
          const val = values[prop.id];
          return (
            <div key={prop.id} className="flex items-center gap-2">
              <span className="text-xs w-24 shrink-0 truncate text-tertiary" title={prop.display_name}>
                {prop.display_name}
                {prop.is_required && <span className="text-red-500"> *</span>}
              </span>

              {prop.property_type === "TEXT" && (
                <input
                  type="text"
                  defaultValue={val?.value_text ?? ""}
                  disabled={!isEditable}
                  onBlur={(e) => {
                    const v = e.target.value.trim();
                    if (v && v !== (val?.value_text ?? "")) void handleValueChange(prop, { value_text: v });
                  }}
                  className={inputClass}
                />
              )}

              {prop.property_type === "DECIMAL" && (
                <input
                  type="number"
                  defaultValue={val?.value_number ?? ""}
                  disabled={!isEditable}
                  onBlur={(e) => {
                    const raw = e.target.value;
                    if (raw !== "" && Number(raw) !== val?.value_number)
                      void handleValueChange(prop, { value_number: Number(raw) });
                  }}
                  className={inputClass}
                />
              )}

              {prop.property_type === "BOOLEAN" && (
                <input
                  type="checkbox"
                  checked={val?.value_boolean ?? false}
                  disabled={!isEditable}
                  onChange={(e) => void handleValueChange(prop, { value_boolean: e.target.checked })}
                  className="size-3.5 accent-[#ED1F24]"
                />
              )}

              {prop.property_type === "DATETIME" && (
                <input
                  type="date"
                  defaultValue={val?.value_datetime ? val.value_datetime.slice(0, 10) : ""}
                  disabled={!isEditable}
                  onChange={(e) => {
                    if (e.target.value) void handleValueChange(prop, { value_datetime: `${e.target.value}T00:00:00Z` });
                  }}
                  className={inputClass}
                />
              )}

              {prop.property_type === "OPTION" && (
                <select
                  value={val?.value_uuid ?? ""}
                  disabled={!isEditable}
                  onChange={(e) => {
                    if (e.target.value) void handleValueChange(prop, { value_uuid: e.target.value });
                  }}
                  className={inputClass}
                >
                  <option value="">{t("work_item_extra_ui.select")}</option>
                  {prop.options
                    .filter((o) => o.is_active)
                    .map((o) => (
                      <option key={o.id} value={o.id}>
                        {o.name}
                      </option>
                    ))}
                </select>
              )}

              {prop.property_type === "MEMBER" && (
                <select
                  value={val?.value_uuid ?? ""}
                  disabled={!isEditable}
                  onChange={(e) => {
                    if (e.target.value) void handleValueChange(prop, { value_uuid: e.target.value });
                  }}
                  className={inputClass}
                >
                  <option value="">{t("work_item_extra_ui.select_member")}</option>
                  {memberIds.map((mid) => {
                    const m = getUserDetails(mid);
                    if (!m) return null;
                    return (
                      <option key={mid} value={mid}>
                        {m.display_name || `${m.first_name} ${m.last_name}`.trim()}
                      </option>
                    );
                  })}
                </select>
              )}
            </div>
          );
        })}
    </div>
  );
});
