/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Paradise KEP-82: who sees a public quick link. Admin only, shown when visibility is Public.
import { useTranslation } from "@plane/i18n";
import type { TSharedQuickLinkAudience, TSharedQuickLinkDivision } from "@plane/types";
import { Checkbox } from "@plane/ui";

export type TQuickLinkAudienceValue = {
  audience: TSharedQuickLinkAudience;
  divisionIds: string[];
  departmentIds: string[];
};

export const DEFAULT_AUDIENCE: TQuickLinkAudienceValue = { audience: "semua", divisionIds: [], departmentIds: [] };

const toggle = (ids: string[], id: string): string[] =>
  ids.includes(id) ? ids.filter((item) => item !== id) : [...ids, id];

/** A department inside a chosen division is already covered by it, so it is not sent. */
export const audiencePayload = (value: TQuickLinkAudienceValue, divisions: TSharedQuickLinkDivision[]) => {
  const isForUnits = value.audience === "organisasi";
  return {
    cakupan: value.audience,
    divisi_ids: isForUnits ? value.divisionIds : [],
    departemen_ids: isForUnits
      ? value.departmentIds.filter(
          (id) => !divisions.some((d) => value.divisionIds.includes(d.id) && d.departemen.some((dep) => dep.id === id))
        )
      : [],
  };
};

export const isAudienceEmpty = (value: TQuickLinkAudienceValue) =>
  value.audience === "organisasi" && value.divisionIds.length === 0 && value.departmentIds.length === 0;

type Props = {
  value: TQuickLinkAudienceValue;
  onChange: (value: TQuickLinkAudienceValue) => void;
  divisions: TSharedQuickLinkDivision[];
  hasError: boolean;
};

export function QuickLinkAudience({ value, onChange, divisions, hasError }: Props) {
  const { t } = useTranslation();
  const { audience, divisionIds, departmentIds } = value;
  return (
    <fieldset className="space-y-2">
      <legend className="mb-2 text-14 font-medium text-secondary">{t("quick_links_ui.audience")}</legend>
      <label className="flex cursor-pointer items-center gap-2 text-13">
        <Checkbox
          shape="circle"
          checked={audience === "semua"}
          onChange={() => onChange({ ...value, audience: "semua" })}
        />
        {t("quick_links_ui.audience_everyone")}
      </label>
      <label className="flex cursor-pointer items-center gap-2 text-13">
        <Checkbox
          shape="circle"
          checked={audience === "organisasi"}
          onChange={() => onChange({ ...value, audience: "organisasi" })}
        />
        {t("quick_links_ui.audience_units")}
      </label>
      {audience === "organisasi" && (
        <div className="ml-6 space-y-2">
          {divisions.length === 0 ? (
            <p className="text-12 text-tertiary">{t("quick_links_ui.audience_no_units")}</p>
          ) : (
            <>
              <p className="text-12 text-tertiary">{t("quick_links_ui.audience_hint")}</p>
              <div className="max-h-56 space-y-2 overflow-y-auto rounded-md border-[0.5px] border-subtle p-3">
                {divisions.map((division) => {
                  const isDivisionChosen = divisionIds.includes(division.id);
                  return (
                    <div key={division.id} className="space-y-1">
                      <label className="flex cursor-pointer items-center gap-2 text-13 font-medium">
                        <Checkbox
                          checked={isDivisionChosen}
                          onChange={() => onChange({ ...value, divisionIds: toggle(divisionIds, division.id) })}
                        />
                        {division.nama}
                        <span className="text-11 text-placeholder">{division.kode}</span>
                      </label>
                      {division.departemen.map((department) => (
                        <label
                          key={department.id}
                          className="ml-6 flex cursor-pointer items-center gap-2 text-13 text-secondary"
                        >
                          <Checkbox
                            checked={isDivisionChosen || departmentIds.includes(department.id)}
                            disabled={isDivisionChosen}
                            onChange={() => onChange({ ...value, departmentIds: toggle(departmentIds, department.id) })}
                          />
                          {department.nama}
                          <span className="text-11 text-placeholder">{department.kode}</span>
                        </label>
                      ))}
                    </div>
                  );
                })}
              </div>
            </>
          )}
          {hasError && <span className="text-11 text-danger-primary">{t("quick_links_ui.audience_required")}</span>}
        </div>
      )}
    </fieldset>
  );
}
