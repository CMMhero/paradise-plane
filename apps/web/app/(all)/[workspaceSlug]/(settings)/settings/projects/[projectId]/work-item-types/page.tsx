/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Settings Work Item Types & Custom Properties
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "react-router";
import { ChevronDown, ChevronRight, Plus, Shapes, Trash2 } from "lucide-react";
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
  WorkItemTypesService,
  type TWorkItemType,
  type TWorkItemProperty,
  type TPropertyType,
} from "@/services/issue/issue_types.service";

const typesService = new WorkItemTypesService();

// `label` adalah KUNCI i18n, diterjemahkan saat dirender.
const FIELD_TYPES: { value: TPropertyType; label: string }[] = [
  { value: "TEXT", label: "work_item_types_ui.field_type.text" },
  { value: "DECIMAL", label: "work_item_types_ui.field_type.number" },
  { value: "BOOLEAN", label: "work_item_types_ui.field_type.boolean" },
  { value: "DATETIME", label: "work_item_types_ui.field_type.date" },
  { value: "OPTION", label: "work_item_types_ui.field_type.option" },
  { value: "MEMBER", label: "work_item_types_ui.field_type.member" },
];

const labelField = (nilai: TPropertyType, t: (key: string) => string): string => {
  const label = FIELD_TYPES.find((f) => f.value === nilai)?.label;
  return label ? t(label) : nilai;
};

const inputClass = "rounded border border-subtle bg-layer-1 px-2 py-1 text-xs outline-none focus:border-accent";

const toastError = (err: unknown, fallback: string, t: (key: string) => string) => {
  const message = (err as { error?: string })?.error ?? fallback;
  setToast({ type: TOAST_TYPE.ERROR, title: t("work_item_types_ui.failed"), message });
};

type TTypeCardProps = {
  workspaceSlug: string;
  projectId: string;
  type: TWorkItemType;
  onChanged: () => void;
};

const TypeCard = observer(function TypeCard({ workspaceSlug, projectId, type, onChanged }: TTypeCardProps) {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const [properties, setProperties] = useState<TWorkItemProperty[]>([]);
  const [fieldName, setFieldName] = useState("");
  const [fieldType, setFieldType] = useState<TPropertyType>("TEXT");
  const [fieldRequired, setFieldRequired] = useState(false);
  const [optionDrafts, setOptionDrafts] = useState<Record<string, string>>({});

  const fetchProperties = useCallback(async () => {
    try {
      const res = await typesService.listProperties(workspaceSlug, projectId, type.id);
      setProperties(res ?? []);
    } catch {
      // biarkan kosong bila gagal
    }
  }, [workspaceSlug, projectId, type.id]);

  useEffect(() => {
    if (isOpen) void fetchProperties();
  }, [isOpen, fetchProperties]);

  const handleAddField = async () => {
    if (!fieldName.trim()) return;
    try {
      await typesService.createProperty(workspaceSlug, projectId, type.id, {
        display_name: fieldName.trim(),
        property_type: fieldType,
        is_required: fieldRequired,
      });
      setFieldName("");
      setFieldRequired(false);
      await fetchProperties();
    } catch (err) {
      toastError(err, t("work_item_types_ui.add_field_failed"), t);
    }
  };

  const handleDeleteField = async (propertyId: string) => {
    try {
      await typesService.deleteProperty(workspaceSlug, projectId, type.id, propertyId);
      await fetchProperties();
    } catch (err) {
      toastError(err, t("work_item_types_ui.delete_field_failed"), t);
    }
  };

  const handleAddOption = async (propertyId: string) => {
    const name = (optionDrafts[propertyId] ?? "").trim();
    if (!name) return;
    try {
      await typesService.createOption(workspaceSlug, projectId, propertyId, { name });
      setOptionDrafts((prev) => ({ ...prev, [propertyId]: "" }));
      await fetchProperties();
    } catch (err) {
      toastError(err, t("work_item_types_ui.add_option_failed"), t);
    }
  };

  const handleDeleteOption = async (propertyId: string, optionId: string) => {
    try {
      await typesService.deleteOption(workspaceSlug, projectId, propertyId, optionId);
      await fetchProperties();
    } catch (err) {
      toastError(err, t("work_item_types_ui.delete_option_failed"), t);
    }
  };

  const handleDeleteType = async () => {
    if (!window.confirm(t("work_item_types_ui.confirm_delete_type", { name: type.name }))) return;
    try {
      await typesService.deleteType(workspaceSlug, projectId, type.id);
      onChanged();
    } catch (err) {
      toastError(err, t("work_item_types_ui.delete_type_failed"), t);
    }
  };

  return (
    <div className="rounded-md border border-subtle">
      <div className="flex items-center justify-between px-3 py-2">
        <button type="button" className="flex flex-1 items-center gap-2 text-left" onClick={() => setIsOpen((v) => !v)}>
          {isOpen ? (
            <ChevronDown className="size-4 text-tertiary" />
          ) : (
            <ChevronRight className="size-4 text-tertiary" />
          )}
          <span className="text-sm font-medium text-primary">{type.name}</span>
          {type.description && <span className="text-xs truncate text-tertiary">— {type.description}</span>}
        </button>
        <button
          type="button"
          onClick={handleDeleteType}
          aria-label={t("work_item_types_ui.delete_type", { name: type.name })}
        >
          <Trash2 className="hover:text-red-500 size-4 text-tertiary" />
        </button>
      </div>

      {isOpen && (
        <div className="flex flex-col gap-2 border-t border-subtle px-3 py-2.5">
          {properties.length === 0 && <p className="text-xs text-tertiary">{t("work_item_types_ui.no_fields")}</p>}

          {properties.map((prop) => (
            <div key={prop.id} className="rounded bg-layer-2 px-2.5 py-1.5">
              <div className="flex items-center justify-between">
                <div className="text-xs flex items-center gap-2">
                  <span className="font-medium text-primary">{prop.display_name}</span>
                  <span className="rounded bg-layer-3 px-1.5 py-0.5 text-[10px] text-secondary">
                    {labelField(prop.property_type, t)}
                  </span>
                  {prop.is_required && (
                    <span className="text-red-500 text-[10px]">{t("work_item_types_ui.required")}</span>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => handleDeleteField(prop.id)}
                  aria-label={t("work_item_types_ui.delete_field", { name: prop.display_name })}
                >
                  <Trash2 className="hover:text-red-500 size-3.5 text-tertiary" />
                </button>
              </div>

              {prop.property_type === "OPTION" && (
                <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                  {prop.options.map((o) => (
                    <span
                      key={o.id}
                      className="flex items-center gap-1 rounded-full border border-subtle px-2 py-0.5 text-[11px]"
                    >
                      {o.name}
                      <button
                        type="button"
                        onClick={() => handleDeleteOption(prop.id, o.id)}
                        aria-label={t("work_item_types_ui.delete_option", { name: o.name })}
                      >
                        <Trash2 className="hover:text-red-500 size-3 text-tertiary" />
                      </button>
                    </span>
                  ))}
                  <input
                    type="text"
                    placeholder={t("work_item_types_ui.new_option")}
                    value={optionDrafts[prop.id] ?? ""}
                    onChange={(e) => setOptionDrafts((prev) => ({ ...prev, [prop.id]: e.target.value }))}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") void handleAddOption(prop.id);
                    }}
                    className={`${inputClass} w-28`}
                  />
                </div>
              )}
            </div>
          ))}

          {/* Form tambah field */}
          <div className="flex flex-wrap items-center gap-1.5 pt-1">
            <input
              type="text"
              placeholder={t("work_item_types_ui.new_field_name")}
              value={fieldName}
              onChange={(e) => setFieldName(e.target.value)}
              className={`${inputClass} w-40`}
            />
            <select
              value={fieldType}
              onChange={(e) => setFieldType(e.target.value as TPropertyType)}
              className={inputClass}
            >
              {FIELD_TYPES.map((f) => (
                <option key={f.value} value={f.value}>
                  {t(f.label)}
                </option>
              ))}
            </select>
            <label className="text-xs flex items-center gap-1 text-secondary">
              <input
                type="checkbox"
                checked={fieldRequired}
                onChange={(e) => setFieldRequired(e.target.checked)}
                className="size-3"
              />
              {t("work_item_types_ui.required")}
            </label>
            <button
              type="button"
              onClick={handleAddField}
              className="bg-accent text-xs flex items-center gap-1 rounded px-2 py-1 font-medium text-on-color"
            >
              <Plus className="size-3.5" /> {t("work_item_types_ui.field")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
});

function WorkItemTypesSettingsPage() {
  const { t } = useTranslation();
  const { workspaceSlug, projectId } = useParams();
  // store
  const { currentProjectDetails } = useProject();
  const { workspaceUserInfo, allowPermissions } = useUserPermissions();
  // state
  const [types, setTypes] = useState<TWorkItemType[]>([]);
  const [newTypeName, setNewTypeName] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  const canAdmin = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.PROJECT);
  const pageTitle = currentProjectDetails?.name
    ? t("work_item_types_ui.page_title", { name: currentProjectDetails.name })
    : undefined;

  const fetchTypes = useCallback(async () => {
    if (!workspaceSlug || !projectId) return;
    try {
      const res = await typesService.listTypes(workspaceSlug, projectId);
      setTypes(res ?? []);
    } catch {
      // kosong bila gagal
    } finally {
      setIsLoading(false);
    }
  }, [workspaceSlug, projectId]);

  useEffect(() => {
    void fetchTypes();
  }, [fetchTypes]);

  const handleAddType = async () => {
    if (!newTypeName.trim() || !workspaceSlug || !projectId) return;
    try {
      await typesService.createType(workspaceSlug, projectId, { name: newTypeName.trim() });
      setNewTypeName("");
      await fetchTypes();
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("work_item_types_ui.saved"),
        message: t("work_item_types_ui.type_created"),
      });
    } catch (err) {
      toastError(err, t("work_item_types_ui.create_type_failed"), t);
    }
  };

  if (workspaceUserInfo && !canAdmin) {
    return <NotAuthorizedView section="settings" isProjectView />;
  }
  if (!workspaceSlug || !projectId) return <></>;

  return (
    <SettingsContentWrapper>
      <PageHead title={pageTitle} />
      <div className="flex w-full flex-col gap-4">
        <div className="flex flex-col gap-1 border-b border-subtle pb-3">
          <div className="flex items-center gap-2">
            <Shapes className="size-5 text-secondary" />
            <h3 className="text-xl font-medium text-primary">{t("work_item_types_ui.title")}</h3>
          </div>
          <p className="text-sm text-tertiary">{t("work_item_types_ui.description")}</p>
        </div>

        {/* Form tambah tipe */}
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder={t("work_item_types_ui.new_type_placeholder")}
            value={newTypeName}
            onChange={(e) => setNewTypeName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void handleAddType();
            }}
            className={`${inputClass} w-64`}
          />
          <button
            type="button"
            onClick={handleAddType}
            className="bg-accent text-xs flex items-center gap-1 rounded px-2.5 py-1 font-medium text-on-color"
          >
            <Plus className="size-3.5" /> {t("work_item_types_ui.add_type")}
          </button>
        </div>

        {/* Daftar tipe */}
        {isLoading ? (
          <p className="text-sm text-tertiary">{t("chat_ui.loading")}</p>
        ) : types.length === 0 ? (
          <p className="text-sm text-tertiary">{t("work_item_types_ui.no_types")}</p>
        ) : (
          <div className="flex flex-col gap-2">
            {types.map((tipe) => (
              <TypeCard
                key={tipe.id}
                workspaceSlug={workspaceSlug}
                projectId={projectId}
                type={tipe}
                onChanged={fetchTypes}
              />
            ))}
          </div>
        )}
      </div>
    </SettingsContentWrapper>
  );
}

export default observer(WorkItemTypesSettingsPage);
