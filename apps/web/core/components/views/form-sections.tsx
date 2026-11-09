/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: bagian formulir view (workspace & departemen)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Satu kerangka untuk dua formulir view, supaya urutan dan gaya selalu sama:
 * judul, tempat (workspace/departemen), detail, siapa yang bisa melihat, tampilan,
 * filter, lalu tombol. Gaya hanya lewat token dan komponen propel/ui (KEP-64).
 */

import type { ReactNode } from "react";
import { useId } from "react";
import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { RadioGroup } from "@plane/propel/radio-group";
import { EViewAccess } from "@plane/types";
import { Logo } from "@plane/propel/emoji-icon-picker";
// components
import { ProjectDropdown } from "@/components/dropdowns/project/dropdown";
// hooks
import { useProject } from "@/hooks/store/use-project";

/** Kartu pilihan radio: pola yang sama dengan layar pilih departemen (`pilih-departemen.tsx`). */
const PILIHAN_KELAS =
  "border border-subtle px-3 py-2 has-[[data-checked]]:border-accent-strong has-[[data-checked]]:bg-accent-subtle";

type TSectionProps = {
  title: string;
  description?: string;
  children: ReactNode;
};

/** Satu kelompok isian berlabel. `fieldset` + `legend` supaya pembaca layar ikut mengelompokkan. */
export function ViewFormSection({ title, description, children }: TSectionProps) {
  return (
    <fieldset className="flex min-w-0 flex-col gap-2">
      <legend className="mb-2 flex flex-col gap-0.5">
        <span className="text-13 font-medium text-primary">{title}</span>
        {description && <span className="text-12 text-tertiary">{description}</span>}
      </legend>
      {children}
    </fieldset>
  );
}

type THeaderProps = { isEditing: boolean };

export function ViewFormHeader({ isEditing }: THeaderProps) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-1">
      <h3 className="text-16 font-semibold text-primary">
        {isEditing ? t("views_ui.edit_title") : t("views_ui.create_title")}
      </h3>
      <p className="text-13 text-secondary">{t("views_ui.subtitle")}</p>
    </div>
  );
}

type TVisibilityProps = {
  value: EViewAccess | undefined;
  onChange: (value: EViewAccess) => void;
  /** Teks "publik" berbeda untuk view workspace dan view departemen. */
  scope: "workspace" | "department";
  /** Server hanya mengizinkan pemilik mengganti akses (`_galat_izin_view`). */
  canChange: boolean;
};

export function ViewVisibilityField({ value, onChange, scope, canChange }: TVisibilityProps) {
  const { t } = useTranslation();
  return (
    <ViewFormSection
      title={t("views_ui.visibility_label")}
      description={canChange ? undefined : t("views_ui.visibility_owner_only")}
    >
      <RadioGroup
        name="view-access"
        aria-label={t("views_ui.visibility_label")}
        orientation="horizontal"
        className="grid grid-cols-1 gap-2 sm:grid-cols-2"
        value={String(value ?? EViewAccess.PUBLIC)}
        onValueChange={(next) => onChange(Number(next) as EViewAccess)}
        disabled={!canChange}
      >
        <RadioGroup.Item
          value={String(EViewAccess.PUBLIC)}
          label={t("views_ui.public_label")}
          description={
            scope === "workspace" ? t("views_ui.public_hint_workspace") : t("views_ui.public_hint_department")
          }
          className={PILIHAN_KELAS}
        />
        <RadioGroup.Item
          value={String(EViewAccess.PRIVATE)}
          label={t("views_ui.private_label")}
          description={t("views_ui.private_hint")}
          className={PILIHAN_KELAS}
        />
      </RadioGroup>
    </ViewFormSection>
  );
}

type TScopeProps = {
  /** `null` = view workspace, selain itu id departemen (project). */
  projectId: string | null;
  onChange?: (projectId: string | null) => void;
  /** Sesudah dibuat, view tidak bisa pindah tempat (kolom `project` hanya-baca di server). */
  isLocked?: boolean;
};

export const ViewScopeField = observer(function ViewScopeField({ projectId, onChange, isLocked = false }: TScopeProps) {
  const { t } = useTranslation();
  const { getProjectById, joinedProjectIds } = useProject();
  const dropdownId = useId();
  const project = projectId ? getProjectById(projectId) : undefined;

  if (isLocked || !onChange) {
    return (
      <ViewFormSection title={t("views_ui.scope_label")} description={t("views_ui.scope_locked")}>
        <div className="flex items-center gap-2 text-13 text-secondary">
          {project ? (
            <>
              {project.logo_props && <Logo logo={project.logo_props} size={14} />}
              <span className="truncate text-primary">{project.name}</span>
            </>
          ) : (
            <span className="text-primary">{t("views_ui.scope_workspace")}</span>
          )}
        </div>
      </ViewFormSection>
    );
  }

  const isDepartment = projectId !== null;
  // Memilih "Departemen" langsung memilih departemen pertama, jadi formulir tidak pernah
  // berada di keadaan "departemen tanpa departemen"; dropdown di bawah menggantinya.
  const firstProjectId = joinedProjectIds?.[0] ?? null;
  return (
    <ViewFormSection title={t("views_ui.scope_label")}>
      <RadioGroup
        name="view-scope"
        aria-label={t("views_ui.scope_label")}
        orientation="horizontal"
        className="grid grid-cols-1 gap-2 sm:grid-cols-2"
        value={isDepartment ? "department" : "workspace"}
        onValueChange={(next) => onChange(next === "workspace" ? null : (projectId ?? firstProjectId))}
      >
        <RadioGroup.Item
          value="workspace"
          label={t("views_ui.scope_workspace")}
          description={t("views_ui.scope_workspace_hint")}
          className={PILIHAN_KELAS}
        />
        <RadioGroup.Item
          value="department"
          label={t("views_ui.scope_department")}
          description={t("views_ui.scope_department_hint")}
          disabled={!firstProjectId}
          className={PILIHAN_KELAS}
        />
      </RadioGroup>
      {isDepartment && (
        <div className="flex items-center gap-2">
          <span id={dropdownId} className="text-12 text-tertiary">
            {t("views_ui.scope_department")}
          </span>
          <div className="h-7" aria-labelledby={dropdownId}>
            <ProjectDropdown
              value={projectId}
              onChange={(val) => onChange(val)}
              multiple={false}
              buttonVariant="border-with-text"
              placeholder={t("views_ui.scope_department_placeholder")}
            />
          </div>
        </div>
      )}
    </ViewFormSection>
  );
});

type TFooterProps = {
  isEditing: boolean;
  isSubmitting: boolean;
  onCancel: () => void;
  cancelTabIndex?: number;
  submitTabIndex?: number;
};

export function ViewFormFooter({ isEditing, isSubmitting, onCancel, cancelTabIndex, submitTabIndex }: TFooterProps) {
  const { t } = useTranslation();
  const submitLabel = isEditing
    ? isSubmitting
      ? t("common.updating")
      : t("views_ui.save_changes")
    : isSubmitting
      ? t("common.creating")
      : t("views_ui.create_title");
  return (
    <div className="flex items-center justify-end gap-2 border-t border-subtle px-5 py-4">
      <Button variant="secondary" size="lg" onClick={onCancel} tabIndex={cancelTabIndex}>
        {t("common.cancel")}
      </Button>
      <Button variant="primary" size="lg" type="submit" tabIndex={submitTabIndex} loading={isSubmitting}>
        {submitLabel}
      </Button>
    </div>
  );
}
