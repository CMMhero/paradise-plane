/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { Input } from "@plane/ui";
import type { TQuickAddIssueForm } from "../root";

export const SpreadsheetQuickAddIssueForm = observer(function SpreadsheetQuickAddIssueForm(props: TQuickAddIssueForm) {
  const { ref, projectDetail, register, onSubmit, isEpic } = props;
  const { t } = useTranslation();
  return (
    <div className="pb-2">
      <form
        ref={ref}
        onSubmit={onSubmit}
        className="z-10 flex items-center gap-x-5 border-[0.5px] border-t-0 border-subtle bg-surface-1 px-4 shadow-raised-200"
      >
        <h4 className="w-20 text-11 leading-5 text-placeholder">{projectDetail?.identifier ?? "..."}</h4>
        <Input
          type="text"
          autoComplete="off"
          placeholder={isEpic ? t("epic.title.label") : t("issue.title.label")}
          {...register("name", {
            required: isEpic ? t("epic.title.required") : t("issue.title.required"),
          })}
          mode="true-transparent"
          className="w-full px-0 py-3 leading-5 text-secondary"
        />
      </form>
      <p className="mt-3 ml-3 text-11 text-secondary italic">
        {isEpic ? t("epic.add.press_enter") : t("issue.add.press_enter")}
      </p>
    </div>
  );
});
