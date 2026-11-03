/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { Input } from "@plane/ui";
import { cn } from "@plane/utils";
import type { TQuickAddIssueForm } from "../root";

export const GanttQuickAddIssueForm = observer(function GanttQuickAddIssueForm(props: TQuickAddIssueForm) {
  const { ref, projectDetail, hasError, register, onSubmit, isEpic } = props;
  const { t } = useTranslation();
  return (
    <div className={cn("shadow-raised-200", hasError && "border border-danger-strong/20 bg-danger-subtle")}>
      <form
        ref={ref}
        onSubmit={onSubmit}
        className="flex w-full items-center gap-x-3 border-[0.5px] border-subtle bg-surface-1 px-3"
      >
        <div className="flex w-full items-center gap-3">
          <div className="text-11 font-medium text-placeholder">{projectDetail?.identifier ?? "..."}</div>
          <Input
            type="text"
            autoComplete="off"
            placeholder={isEpic ? t("epic.title.label") : t("issue.title.label")}
            {...register("name", {
              required: isEpic ? t("epic.title.required") : t("issue.title.required"),
            })}
            mode="true-transparent"
            className="w-full px-2 py-3 leading-5 font-medium text-secondary"
          />
        </div>
      </form>
      <div className="bg-surface-1 px-3 py-2 text-11 text-secondary italic">
        {isEpic ? t("epic.add.press_enter") : t("issue.add.press_enter")}
      </div>
    </div>
  );
});
