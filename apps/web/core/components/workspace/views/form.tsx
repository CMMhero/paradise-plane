/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ReactNode } from "react";
import { observer } from "mobx-react";
import { Controller, useForm } from "react-hook-form";
// plane imports
import { ISSUE_DISPLAY_FILTERS_BY_PAGE } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import type { IIssueDisplayFilterOptions, IIssueDisplayProperties, IWorkspaceView, IIssueFilters } from "@plane/types";
import { EViewAccess, EIssueLayoutTypes, EIssuesStoreType } from "@plane/types";
import { Input, TextArea } from "@plane/ui";
import { getComputedDisplayFilters, getComputedDisplayProperties } from "@plane/utils";
// components
import { DisplayFiltersSelection, FiltersDropdown } from "@/components/issues/issue-layouts/filters";
import {
  ViewFormFooter,
  ViewFormHeader,
  ViewFormSection,
  ViewScopeField,
  ViewVisibilityField,
} from "@/components/views/form-sections";
import { ViewLogoPicker } from "@/components/views/logo-picker";
import { WorkspaceLevelWorkItemFiltersHOC } from "@/components/work-item-filters/filters-hoc/workspace-level";
import { WorkItemFiltersRow } from "@/components/work-item-filters/filters-row";
// hooks
import { useUser } from "@/hooks/store/user";

type Props = {
  handleFormSubmit: (values: Partial<IWorkspaceView>) => Promise<void>;
  handleClose: () => void;
  data?: IWorkspaceView;
  preLoadedData?: Partial<IWorkspaceView>;
  workspaceSlug: string;
  /** Kustomisasi Paradise: pemilih workspace/departemen saat membuat view dari halaman Views workspace. */
  scopeSlot?: ReactNode;
};

const DEFAULT_VALUES: Partial<IWorkspaceView> = {
  name: "",
  description: "",
  access: EViewAccess.PUBLIC,
  display_properties: getComputedDisplayProperties(),
  display_filters: getComputedDisplayFilters({
    layout: EIssueLayoutTypes.SPREADSHEET,
    order_by: "-created_at",
  }),
};

export const WorkspaceViewForm = observer(function WorkspaceViewForm(props: Props) {
  const { handleFormSubmit, handleClose, data, preLoadedData, workspaceSlug, scopeSlot } = props;
  // i18n
  const { t } = useTranslation();
  // store hooks
  const { data: currentUser } = useUser();
  // form info
  const defaultValues = {
    ...DEFAULT_VALUES,
    ...preLoadedData,
    ...data,
  };
  const {
    formState: { errors, isSubmitting },
    handleSubmit,
    control,
    reset,
    getValues,
    setValue,
    watch,
  } = useForm<IWorkspaceView>({
    defaultValues,
  });
  // derived values
  // Server hanya mengizinkan pemilik mengganti akses; view baru selalu milik pembuatnya.
  const canChangeAccess = !data || data.owned_by === currentUser?.id;
  const workItemFilters: IIssueFilters = {
    richFilters: getValues("rich_filters"),
    displayFilters: getValues("display_filters"),
    displayProperties: getValues("display_properties"),
    kanbanFilters: undefined,
  };

  const handleCreateUpdateView = async (formData: Partial<IWorkspaceView>) => {
    await handleFormSubmit(formData);
    reset({
      ...defaultValues,
    });
  };

  return (
    <form onSubmit={handleSubmit(handleCreateUpdateView)}>
      <div className="flex flex-col gap-6 p-5">
        <ViewFormHeader isEditing={!!data} />
        {scopeSlot ?? <ViewScopeField projectId={null} isLocked />}
        <ViewFormSection title={t("views_ui.details_label")}>
          <div className="flex w-full items-start gap-2">
            <ViewLogoPicker value={watch("logo_props")} onChange={(logo) => setValue("logo_props", logo)} />
            <div className="w-full flex-grow space-y-1">
              <Controller
                control={control}
                name="name"
                rules={{
                  required: t("form.title.required"),
                  maxLength: {
                    value: 255,
                    message: t("form.title.max_length", { length: 255 }),
                  },
                }}
                render={({ field: { value, onChange, ref } }) => (
                  <Input
                    id="name"
                    name="name"
                    type="name"
                    value={value}
                    onChange={onChange}
                    ref={ref}
                    hasError={Boolean(errors.name)}
                    placeholder={t("views_ui.name_placeholder")}
                    aria-label={t("views_ui.name_placeholder")}
                    className="w-full text-14"
                    // oxlint-disable-next-line jsx-a11y/no-autofocus -- dialog dibuka untuk mengetik nama; fokus tetap di dalam dialog
                    autoFocus
                  />
                )}
              />
              <span className="text-11 text-danger-primary">{errors?.name?.message}</span>
            </div>
          </div>
          <Controller
            name="description"
            control={control}
            render={({ field: { value, onChange } }) => (
              <TextArea
                id="description"
                name="description"
                value={value}
                placeholder={t("views_ui.description_placeholder")}
                aria-label={t("views_ui.description_placeholder")}
                onChange={onChange}
                className="min-h-20 w-full resize-none text-14"
                hasError={Boolean(errors?.description)}
              />
            )}
          />
        </ViewFormSection>
        <Controller
          control={control}
          name="access"
          render={({ field: { value, onChange } }) => (
            <ViewVisibilityField value={value} onChange={onChange} scope="workspace" canChange={canChangeAccess} />
          )}
        />
        <ViewFormSection title={t("views_ui.display_label")} description={t("views_ui.display_workspace_hint")}>
          <div className="flex flex-wrap items-center gap-2">
            <Controller
              control={control}
              name="display_filters"
              render={({ field: { onChange: onDisplayFiltersChange, value: displayFilters } }) => (
                <Controller
                  control={control}
                  name="display_properties"
                  render={({ field: { onChange: onDisplayPropertiesChange, value: displayProperties } }) => (
                    <FiltersDropdown title={t("common.display")}>
                      <DisplayFiltersSelection
                        layoutDisplayFiltersOptions={ISSUE_DISPLAY_FILTERS_BY_PAGE.my_issues.layoutOptions.spreadsheet}
                        displayFilters={displayFilters ?? {}}
                        handleDisplayFiltersUpdate={(updatedDisplayFilter: Partial<IIssueDisplayFilterOptions>) => {
                          onDisplayFiltersChange({
                            ...displayFilters,
                            ...updatedDisplayFilter,
                          });
                        }}
                        displayProperties={displayProperties ?? {}}
                        handleDisplayPropertiesUpdate={(updatedDisplayProperties: Partial<IIssueDisplayProperties>) => {
                          onDisplayPropertiesChange({
                            ...displayProperties,
                            ...updatedDisplayProperties,
                          });
                        }}
                      />
                    </FiltersDropdown>
                  )}
                />
              )}
            />
          </div>
        </ViewFormSection>
        <ViewFormSection title={t("views_ui.filters_label")} description={t("views_ui.filters_hint")}>
          <Controller
            control={control}
            name="rich_filters"
            render={({ field: { onChange: onFiltersChange } }) => (
              <WorkspaceLevelWorkItemFiltersHOC
                entityId={data?.id}
                entityType={EIssuesStoreType.GLOBAL}
                filtersToShowByLayout={ISSUE_DISPLAY_FILTERS_BY_PAGE.my_issues.filters}
                initialWorkItemFilters={workItemFilters}
                isTemporary
                updateFilters={(updateFilters) => onFiltersChange(updateFilters)}
                showOnMount
                workspaceSlug={workspaceSlug}
              >
                {({ filter: workspaceViewWorkItemsFilter }) =>
                  workspaceViewWorkItemsFilter && (
                    <WorkItemFiltersRow filter={workspaceViewWorkItemsFilter} variant="modal" />
                  )
                }
              </WorkspaceLevelWorkItemFiltersHOC>
            )}
          />
        </ViewFormSection>
      </div>
      <ViewFormFooter isEditing={!!data} isSubmitting={isSubmitting} onCancel={handleClose} />
    </form>
  );
});
