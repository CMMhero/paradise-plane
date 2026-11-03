/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React from "react";
import { observer } from "mobx-react";
// plane constants
import { ISSUE_DISPLAY_PROPERTIES, isDisplayPropertyAvailable } from "@plane/constants";
// plane i18n
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
// types
import type { IIssueDisplayProperties } from "@plane/types";
// helpers
import { shouldRenderColumn } from "@/helpers/issue-filter.helper";
// components
import { FilterHeader } from "../helpers/filter-header";

type Props = {
  displayProperties: IIssueDisplayProperties;
  displayPropertiesToRender: (keyof IIssueDisplayProperties)[];
  handleUpdate: (updatedDisplayProperties: Partial<IIssueDisplayProperties>) => void;
  cycleViewDisabled?: boolean;
  moduleViewDisabled?: boolean;
  isEpic?: boolean;
};

export const FilterDisplayProperties = observer(function FilterDisplayProperties(props: Props) {
  const {
    displayProperties,
    displayPropertiesToRender,
    handleUpdate,
    cycleViewDisabled = false,
    moduleViewDisabled = false,
    isEpic = false,
  } = props;
  // hooks
  const { t } = useTranslation();
  // states
  const [previewEnabled, setPreviewEnabled] = React.useState(true);

  // Filter out "cycle" and "module" keys if cycleViewDisabled or moduleViewDisabled is true
  // Also filter out display properties that should not be rendered
  const filteredDisplayProperties = ISSUE_DISPLAY_PROPERTIES.filter((property) => {
    if (!displayPropertiesToRender.includes(property.key)) return false;
    if (!isDisplayPropertyAvailable(property.key)) return false;
    // Kustomisasi Paradise: aturan yang sama dengan kolom spreadsheet (mis. project tanpa estimasi).
    if (!shouldRenderColumn(property.key)) return false;
    switch (property.key) {
      case "cycle":
        return !cycleViewDisabled;
      case "modules":
        return !moduleViewDisabled;
      default:
        return true;
    }
  }).map((property) => {
    if (isEpic && property.key === "sub_issue_count") {
      return Object.assign({}, property, { titleTranslationKey: "issue.display.properties.work_item_count" });
    }
    return property;
  });

  return (
    <>
      <FilterHeader
        title={t("issue.display.properties.label")}
        isPreviewEnabled={previewEnabled}
        handleIsPreviewEnabled={() => setPreviewEnabled(!previewEnabled)}
      />
      {previewEnabled && (
        <div className="mt-1 flex flex-wrap items-center gap-2">
          {filteredDisplayProperties.map((displayProperty) => (
            <>
              <Button
                key={displayProperty.key}
                size="chip"
                shape="pill"
                variant={displayProperties?.[displayProperty.key] ? "primary" : "secondary"}
                onClick={() =>
                  handleUpdate({
                    [displayProperty.key]: !displayProperties?.[displayProperty.key],
                  })
                }
              >
                {t(displayProperty.titleTranslationKey)}
              </Button>
            </>
          ))}
        </div>
      )}
    </>
  );
});
