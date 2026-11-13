/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ReactNode } from "react";
import { observer } from "mobx-react";
import { Controller, useForm } from "react-hook-form";
// plane imports
import { ETabIndices, ISSUE_DISPLAY_FILTERS_BY_PAGE } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import type {
  IIssueDisplayFilterOptions,
  IIssueDisplayProperties,
  IProjectView,
  EIssueLayoutTypes,
  IIssueFilters,
} from "@plane/types";
import { EViewAccess, EIssuesStoreType } from "@plane/types";
import { Input, TextArea } from "@plane/ui";
import { getComputedDisplayFilters, getComputedDisplayProperties, getTabIndex } from "@plane/utils";
// components
import { DisplayFiltersSelection, FiltersDropdown } from "@/components/issues/issue-layouts/filters";
import { WorkItemFiltersRow } from "@/components/work-item-filters/filters-row";
// hooks
import { useProject } from "@/hooks/store/use-project";
import { useUser } from "@/hooks/store/user";
import { usePlatformOS } from "@/hooks/use-platform-os";
// local imports
import { LayoutDropDown } from "../dropdowns/layout";
import { ProjectLevelWorkItemFiltersHOC } from "../work-item-filters/filters-hoc/project-level";
import { ViewFormFooter, ViewFormHeader, ViewFormSection, ViewScopeField, ViewVisibilityField } from "./form-sections";
import { ViewLogoPicker } from "./logo-picker";

type Props = {
  data?: IProjectView | null;
  handleClose: () => void;
  handleFormSubmit: (values: IProjectView) => Promise<void>;
  preLoadedData?: Partial<IProjectView> | null;
  projectId: string;
  workspaceSlug: string;
  /**
   * Kustomisasi Paradise: bagian "Tempat". Halaman Views workspace memberi pemilih
   * workspace/departemen; tanpa ini departemennya ditampilkan hanya-baca.
   */
  scopeSlot?: ReactNode;
};

const DEFAULT_VALUES: Partial<IProjectView> = {
  name: "",
  description: "",
  access: EViewAccess.PUBLIC,
  display_properties: getComputedDisplayProperties(),
  display_filters: { ...getComputedDisplayFilters(), group_by: "state" },
};

export const ProjectViewForm = observer(function ProjectViewForm(props: Props) {
  const { handleFormSubmit, handleClose, data, preLoadedData, projectId, workspaceSlug, scopeSlot } = props;
  // i18n
  const { t } = useTranslation();
  // store hooks
  const { getProjectById } = useProject();
  const { data: currentUser } = useUser();
  const { isMobile } = usePlatformOS();
  // form info
  const defaultValues = {
    ...DEFAULT_VALUES,
    ...preLoadedData,
    ...data,
  };
  const {
    control,
    formState: { errors, isSubmitting },
    getValues,
    handleSubmit,
    reset,
    setValue,
    watch,
  } = useForm<IProjectView>({
    defaultValues,
  });
  // derived values
  const projectDetails = getProjectById(projectId);
  // Server hanya mengizinkan pemilik mengganti akses; view baru selalu milik pembuatnya.
  const canChangeAccess = !data || data.owned_by === currentUser?.id;
  const workItemFilters: IIssueFilters = {
    richFilters: getValues("rich_filters"),
    displayFilters: getValues("display_filters"),
    displayProperties: getValues("display_properties"),
    kanbanFilters: undefined,
  };
  const { getIndex } = getTabIndex(ETabIndices.PROJECT_VIEW, isMobile);

  const handleCreateUpdateView = async (formData: IProjectView) => {
    await handleFormSubmit({
      name: formData.name,
      description: formData.description,
      logo_props: formData.logo_props,
      rich_filters: formData.rich_filters,
      display_filters: formData.display_filters,
      display_properties: formData.display_properties,
      access: formData.access,
    } as IProjectView);

    reset({
      ...defaultValues,
    });
  };

  return (
    <form onSubmit={handleSubmit(handleCreateUpdateView)}>
      <div className="flex flex-col gap-6 p-5">
        <ViewFormHeader isEditing={!!data} />
        {scopeSlot ?? <ViewScopeField projectId={projectId} isLocked />}
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
                render={({ field: { value, onChange } }) => (
                  <Input
                    id="name"
                    type="name"
                    name="name"
                    value={value}
                    onChange={onChange}
                    hasError={Boolean(errors.name)}
                    placeholder={t("views_ui.name_placeholder")}
                    aria-label={t("views_ui.name_placeholder")}
                    className="w-full text-14"
                    tabIndex={getIndex("name")}
                    // oxlint-disable-next-line jsx-a11y/no-autofocus -- dialog dibuka untuk mengetik nama; fokus tetap di dalam dialog
                    autoFocus
                  />
                )}
              />
              <span className="text-11 text-danger-primary">{errors?.name?.message?.toString()}</span>
            </div>
          </div>
          <Controller
            name="description"
            control={control}
            render={({ field: { value, onChange } }) => (
              <TextArea
                id="description"
                name="description"
                placeholder={t("views_ui.description_placeholder")}
                aria-label={t("views_ui.description_placeholder")}
                className="min-h-20 w-full resize-none text-14"
                hasError={Boolean(errors?.description)}
                value={value}
                onChange={onChange}
                tabIndex={getIndex("descriptions")}
              />
            )}
          />
        </ViewFormSection>
        <Controller
          control={control}
          name="access"
          render={({ field: { value, onChange } }) => (
            <ViewVisibilityField value={value} onChange={onChange} scope="department" canChange={canChangeAccess} />
          )}
        />
        <ViewFormSection title={t("views_ui.display_label")}>
          <div className="flex flex-wrap items-center gap-2">
            <Controller
              control={control}
              name="display_filters"
              render={({ field: { onChange: onDisplayFiltersChange, value: displayFilters } }) => (
                <>
                  <LayoutDropDown
                    onChange={(selectedValue: EIssueLayoutTypes) =>
                      onDisplayFiltersChange({
                        ...displayFilters,
                        layout: selectedValue,
                      })
                    }
                    value={displayFilters.layout}
                  />
                  <Controller
                    control={control}
                    name="display_properties"
                    render={({ field: { onChange: onDisplayPropertiesChange, value: displayProperties } }) => (
                      <FiltersDropdown title={t("common.display")}>
                        <DisplayFiltersSelection
                          layoutDisplayFiltersOptions={
                            ISSUE_DISPLAY_FILTERS_BY_PAGE.issues.layoutOptions[displayFilters.layout]
                          }
                          displayFilters={displayFilters ?? {}}
                          handleDisplayFiltersUpdate={(updatedDisplayFilter: Partial<IIssueDisplayFilterOptions>) => {
                            onDisplayFiltersChange({
                              ...displayFilters,
                              ...updatedDisplayFilter,
                            });
                          }}
                          displayProperties={displayProperties ?? {}}
                          handleDisplayPropertiesUpdate={(
                            updatedDisplayProperties: Partial<IIssueDisplayProperties>
                          ) => {
                            onDisplayPropertiesChange({
                              ...displayProperties,
                              ...updatedDisplayProperties,
                            });
                          }}
                          cycleViewDisabled={!projectDetails?.cycle_view}
                          moduleViewDisabled={!projectDetails?.module_view}
                        />
                      </FiltersDropdown>
                    )}
                  />
                </>
              )}
            />
          </div>
        </ViewFormSection>
        <ViewFormSection title={t("views_ui.filters_label")} description={t("views_ui.filters_hint")}>
          <Controller
            control={control}
            name="rich_filters"
            render={({ field: { onChange: onFiltersChange } }) => (
              <ProjectLevelWorkItemFiltersHOC
                entityId={data?.id}
                entityType={EIssuesStoreType.PROJECT_VIEW}
                filtersToShowByLayout={ISSUE_DISPLAY_FILTERS_BY_PAGE.issues.filters}
                initialWorkItemFilters={workItemFilters}
                isTemporary
                updateFilters={(updateFilters) => onFiltersChange(updateFilters)}
                projectId={projectId}
                showOnMount
                workspaceSlug={workspaceSlug}
              >
                {({ filter: projectViewWorkItemsFilter }) =>
                  projectViewWorkItemsFilter && (
                    <WorkItemFiltersRow filter={projectViewWorkItemsFilter} variant="modal" />
                  )
                }
              </ProjectLevelWorkItemFiltersHOC>
            )}
          />
        </ViewFormSection>
      </div>
      <ViewFormFooter
        isEditing={!!data}
        isSubmitting={isSubmitting}
        onCancel={handleClose}
        cancelTabIndex={getIndex("cancel")}
        submitTabIndex={getIndex("submit")}
      />
    </form>
  );
});
