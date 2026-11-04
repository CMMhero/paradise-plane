/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Paradise KEP-82: one modal for every quick link. Private = only you (anyone can add).
// Public = shown to everyone or chosen divisions/departments (Super Admin / workspace admin only).
// Switching visibility on an existing link moves it: the new copy is saved first, then the old one removed.
import { useEffect, useState } from "react";
import { observer } from "mobx-react";
import { useForm } from "react-hook-form";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TLink, TLinkEditableFields, TLogoProps, TSharedQuickLink } from "@plane/types";
import { Checkbox, EModalWidth, ModalCore } from "@plane/ui";
import { useHome } from "@/hooks/store/use-home";
import { DEFAULT_AUDIENCE, QuickLinkAudience, audiencePayload, isAudienceEmpty } from "./quick-link-audience";
import type { TQuickLinkAudienceValue } from "./quick-link-audience";
import { EMPTY_QUICK_LINK_FORM, QuickLinkFields } from "./quick-link-fields";
import type { TQuickLinkFormValues } from "./quick-link-fields";
import type { TLinkOperations } from "./use-links";

export type TLinkOperationsModal = Exclude<TLinkOperations, "remove">;

type TVisibility = "private" | "public";

export type TLinkCreateEditModal = {
  workspaceSlug: string;
  linkOperations: TLinkOperationsModal;
};

type TEditedLink = { url: string; title?: string | null; metadata?: TLink["metadata"] | null };

const toFormValues = (link?: TEditedLink): TQuickLinkFormValues => ({
  url: link?.url ?? "",
  title: link?.title ?? "",
  logo_props: link?.metadata?.logo_props ?? null,
});

const toAudience = (link?: TSharedQuickLink): TQuickLinkAudienceValue =>
  link
    ? { audience: link.cakupan, divisionIds: link.divisi_ids, departmentIds: link.departemen_ids }
    : DEFAULT_AUDIENCE;

const sameLogo = (a: TLogoProps | null | undefined, b: TLogoProps | null | undefined) =>
  JSON.stringify(a ?? null) === JSON.stringify(b ?? null);

const errorMessage = (error: unknown): string | undefined =>
  (error as { data?: { error?: string } } | undefined)?.data?.error;

export const LinkCreateUpdateModal = observer(function LinkCreateUpdateModal(props: TLinkCreateEditModal) {
  const { workspaceSlug, linkOperations } = props;
  const { t } = useTranslation();
  const {
    quickLinks: {
      isLinkModalOpen,
      toggleLinkModal,
      linkData,
      sharedLinkModal,
      closeSharedLinkModal,
      getSharedLinks,
      createLink,
      removeLink,
      createSharedLink,
      updateSharedLink,
      removeSharedLink,
    },
  } = useHome();
  const shared = getSharedLinks(workspaceSlug);
  const canManagePublic = Boolean(shared?.boleh_kelola);
  const divisions = shared?.organisasi ?? [];

  const isOpen = isLinkModalOpen || sharedLinkModal.isOpen;
  // Exactly one source is open at a time; the personal one wins if both somehow are.
  const personalLink = isLinkModalOpen ? linkData : undefined;
  const sharedLink = !isLinkModalOpen && sharedLinkModal.isOpen ? sharedLinkModal.link : undefined;
  const editedLink: TEditedLink | undefined = personalLink ?? sharedLink;
  const initialVisibility: TVisibility = sharedLinkModal.isOpen && !isLinkModalOpen ? "public" : "private";

  const {
    formState: { errors, isSubmitting },
    handleSubmit,
    control,
    reset,
  } = useForm<TQuickLinkFormValues>({ defaultValues: EMPTY_QUICK_LINK_FORM });
  const [visibility, setVisibility] = useState<TVisibility>("private");
  const [audience, setAudience] = useState<TQuickLinkAudienceValue>(DEFAULT_AUDIENCE);
  const [hasAudienceError, setHasAudienceError] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    reset(toFormValues(editedLink));
    setVisibility(initialVisibility);
    setAudience(toAudience(sharedLink));
    setHasAudienceError(false);
    // Reset only when the modal opens or switches link, not on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, personalLink?.id, sharedLink?.id]);

  const handleClose = () => {
    toggleLinkModal(false);
    closeSharedLinkModal();
  };

  const savePublic = async (fields: Partial<TLinkEditableFields>) => {
    const payload = { ...fields, ...audiencePayload(audience, divisions) };
    if (sharedLink) await updateSharedLink(workspaceSlug, sharedLink.id, payload);
    else await createSharedLink(workspaceSlug, payload);
    if (personalLink) await removeLink(workspaceSlug, personalLink.id);
    setToast({ type: TOAST_TYPE.SUCCESS, title: t("quick_links_ui.saved") });
    handleClose();
  };

  const savePrivate = async (fields: Partial<TLinkEditableFields>) => {
    if (personalLink) return linkOperations.update(personalLink.id, fields);
    if (!sharedLink) return linkOperations.create(fields);
    // Public -> private: becomes the admin's own link, gone for everyone else.
    await createLink(workspaceSlug, fields);
    await removeSharedLink(workspaceSlug, sharedLink.id);
    setToast({ type: TOAST_TYPE.SUCCESS, title: t("quick_links_ui.saved") });
    handleClose();
  };

  const handleFormSubmit = async (values: TQuickLinkFormValues) => {
    if (visibility === "public" && isAudienceEmpty(audience)) {
      setHasAudienceError(true);
      return;
    }
    const url = values.url.trim();
    const fields: Partial<TLinkEditableFields> = {
      url: url.startsWith("http") ? url : `https://${url}`,
      title: values.title.trim(),
    };
    // Moving a link creates a new row, so its icon always goes along. Otherwise only send a change.
    const isMoving = Boolean(editedLink) && visibility !== initialVisibility;
    if (isMoving || !sameLogo(values.logo_props, editedLink?.metadata?.logo_props))
      fields.logo_props = values.logo_props;
    try {
      if (visibility === "public") await savePublic(fields);
      else await savePrivate(fields);
    } catch (error) {
      // linkOperations already toasted its own failures; this covers the shared endpoints.
      if (visibility === "public" || sharedLink)
        setToast({
          type: TOAST_TYPE.ERROR,
          title: t("quick_links_ui.save_failed"),
          message: errorMessage(error) ?? t("quick_links_ui.save_failed_message"),
        });
    }
  };

  const heading = editedLink ? t("quick_links_ui.edit_link") : t("home.quick_links.add");

  return (
    <ModalCore isOpen={isOpen} handleClose={handleClose} width={EModalWidth.XL}>
      <form onSubmit={handleSubmit(handleFormSubmit)}>
        <div className="space-y-5 p-5">
          <h3 className="text-18 font-medium text-secondary">{heading}</h3>
          <QuickLinkFields control={control} errors={errors} siteTitle={editedLink?.metadata?.title} />
          {canManagePublic && (
            <fieldset className="space-y-2">
              <legend className="mb-2 text-14 font-medium text-secondary">{t("quick_links_ui.visibility")}</legend>
              <label className="flex cursor-pointer items-start gap-2 text-13">
                <Checkbox shape="circle" checked={visibility === "private"} onChange={() => setVisibility("private")} />
                <span>
                  {t("quick_links_ui.visibility_private")}
                  <span className="block text-11 text-tertiary">{t("quick_links_ui.visibility_private_hint")}</span>
                </span>
              </label>
              <label className="flex cursor-pointer items-start gap-2 text-13">
                <Checkbox shape="circle" checked={visibility === "public"} onChange={() => setVisibility("public")} />
                <span>
                  {t("quick_links_ui.visibility_public")}
                  <span className="block text-11 text-tertiary">{t("quick_links_ui.visibility_public_hint")}</span>
                </span>
              </label>
            </fieldset>
          )}
          {canManagePublic && visibility === "public" && (
            <QuickLinkAudience
              value={audience}
              onChange={(next) => {
                setAudience(next);
                setHasAudienceError(false);
              }}
              divisions={divisions}
              hasError={hasAudienceError}
            />
          )}
        </div>
        <div className="flex items-center justify-end gap-2 border-t-[0.5px] border-subtle px-5 py-4">
          <Button variant="secondary" size="lg" onClick={handleClose}>
            {t("Cancel")}
          </Button>
          <Button variant="primary" size="lg" type="submit" loading={isSubmitting}>
            {editedLink ? t("update") : t("add")}
          </Button>
        </div>
      </form>
    </ModalCore>
  );
});
