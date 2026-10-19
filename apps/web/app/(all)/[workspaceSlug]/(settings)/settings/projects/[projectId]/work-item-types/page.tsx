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

const FIELD_TYPES: { value: TPropertyType; label: string }[] = [
  { value: "TEXT", label: "Teks" },
  { value: "DECIMAL", label: "Angka" },
  { value: "BOOLEAN", label: "Ya/Tidak" },
  { value: "DATETIME", label: "Tanggal" },
  { value: "OPTION", label: "Pilihan (dropdown)" },
  { value: "MEMBER", label: "Anggota" },
];

const inputClass = "rounded border border-subtle bg-layer-1 px-2 py-1 text-xs outline-none focus:border-accent";

const toastError = (err: unknown, fallback: string) => {
  const message = (err as { error?: string })?.error ?? fallback;
  setToast({ type: TOAST_TYPE.ERROR, title: "Gagal", message });
};

type TTypeCardProps = {
  workspaceSlug: string;
  projectId: string;
  type: TWorkItemType;
  onChanged: () => void;
};

const TypeCard = observer(function TypeCard({ workspaceSlug, projectId, type, onChanged }: TTypeCardProps) {
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
      toastError(err, "Gagal menambah field.");
    }
  };

  const handleDeleteField = async (propertyId: string) => {
    try {
      await typesService.deleteProperty(workspaceSlug, projectId, type.id, propertyId);
      await fetchProperties();
    } catch (err) {
      toastError(err, "Gagal menghapus field.");
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
      toastError(err, "Gagal menambah opsi.");
    }
  };

  const handleDeleteOption = async (propertyId: string, optionId: string) => {
    try {
      await typesService.deleteOption(workspaceSlug, projectId, propertyId, optionId);
      await fetchProperties();
    } catch (err) {
      toastError(err, "Gagal menghapus opsi.");
    }
  };

  const handleDeleteType = async () => {
    if (!window.confirm(`Hapus tipe "${type.name}" beserta semua field-nya?`)) return;
    try {
      await typesService.deleteType(workspaceSlug, projectId, type.id);
      onChanged();
    } catch (err) {
      toastError(err, "Gagal menghapus tipe.");
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
        <button type="button" onClick={handleDeleteType} aria-label={`Hapus tipe ${type.name}`}>
          <Trash2 className="hover:text-red-500 size-4 text-tertiary" />
        </button>
      </div>

      {isOpen && (
        <div className="flex flex-col gap-2 border-t border-subtle px-3 py-2.5">
          {properties.length === 0 && <p className="text-xs text-tertiary">Belum ada field custom untuk tipe ini.</p>}

          {properties.map((prop) => (
            <div key={prop.id} className="rounded bg-layer-2 px-2.5 py-1.5">
              <div className="flex items-center justify-between">
                <div className="text-xs flex items-center gap-2">
                  <span className="font-medium text-primary">{prop.display_name}</span>
                  <span className="rounded bg-layer-3 px-1.5 py-0.5 text-[10px] text-secondary">
                    {FIELD_TYPES.find((f) => f.value === prop.property_type)?.label ?? prop.property_type}
                  </span>
                  {prop.is_required && <span className="text-red-500 text-[10px]">wajib</span>}
                </div>
                <button
                  type="button"
                  onClick={() => handleDeleteField(prop.id)}
                  aria-label={`Hapus field ${prop.display_name}`}
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
                        aria-label={`Hapus opsi ${o.name}`}
                      >
                        <Trash2 className="hover:text-red-500 size-3 text-tertiary" />
                      </button>
                    </span>
                  ))}
                  <input
                    type="text"
                    placeholder="opsi baru…"
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
              placeholder="nama field baru"
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
                  {f.label}
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
              wajib
            </label>
            <button
              type="button"
              onClick={handleAddField}
              className="bg-accent text-xs flex items-center gap-1 rounded px-2 py-1 font-medium text-on-color"
            >
              <Plus className="size-3.5" /> Field
            </button>
          </div>
        </div>
      )}
    </div>
  );
});

function WorkItemTypesSettingsPage() {
  const { workspaceSlug, projectId } = useParams();
  // store
  const { currentProjectDetails } = useProject();
  const { workspaceUserInfo, allowPermissions } = useUserPermissions();
  // state
  const [types, setTypes] = useState<TWorkItemType[]>([]);
  const [newTypeName, setNewTypeName] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  const canAdmin = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.PROJECT);
  const pageTitle = currentProjectDetails?.name ? `${currentProjectDetails.name} - Work Item Types` : undefined;

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
      setToast({ type: TOAST_TYPE.SUCCESS, title: "Tersimpan", message: "Tipe work item dibuat." });
    } catch (err) {
      toastError(err, "Gagal membuat tipe.");
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
            <h3 className="text-xl font-medium text-primary">Work Item Types</h3>
          </div>
          <p className="text-sm text-tertiary">
            Definisikan tipe work item (mis. Pembelian, Komplain, Bug) dengan field custom per tipe untuk project ini.
          </p>
        </div>

        {/* Form tambah tipe */}
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="nama tipe baru (mis. Pembelian)"
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
            <Plus className="size-3.5" /> Tambah Tipe
          </button>
        </div>

        {/* Daftar tipe */}
        {isLoading ? (
          <p className="text-sm text-tertiary">Memuat…</p>
        ) : types.length === 0 ? (
          <p className="text-sm text-tertiary">
            Belum ada tipe. Buat tipe pertama untuk mengaktifkan field custom di project ini.
          </p>
        ) : (
          <div className="flex flex-col gap-2">
            {types.map((t) => (
              <TypeCard
                key={t.id}
                workspaceSlug={workspaceSlug}
                projectId={projectId}
                type={t}
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
