/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import { useTranslation } from "@plane/i18n";
import { ModuleIcon, PageIcon, ViewsIcon, WorkItemsIcon } from "@plane/propel/icons";
import type { ISvgIcons } from "@plane/propel/icons";
// types
import type { TTourSteps } from "./root";

const sidebarOptions: {
  key: TTourSteps;
  // Same keys as the sidebar navigation, so the tour uses the app's own wording.
  labelKey: string;
  Icon: React.FC<ISvgIcons>;
}[] = [
  { key: "work-items", labelKey: "sidebar.work_items", Icon: WorkItemsIcon },
  { key: "modules", labelKey: "sidebar.modules", Icon: ModuleIcon },
  { key: "views", labelKey: "sidebar.views", Icon: ViewsIcon },
  { key: "pages", labelKey: "sidebar.pages", Icon: PageIcon },
];

type Props = {
  step: TTourSteps;
  setStep: React.Dispatch<React.SetStateAction<TTourSteps>>;
};

export function TourSidebar({ step, setStep }: Props) {
  const { t } = useTranslation();
  return (
    <div className="col-span-3 hidden bg-surface-2 p-8 lg:block">
      <h3 className="text-16 font-medium">
        {t("onboarding_ui.tour_sidebar_title")}
        <br />
        {t("onboarding_ui.tour_sidebar_subtitle")}
      </h3>
      <div className="mt-8 space-y-5">
        {sidebarOptions.map((option) => (
          // <button>, bukan <h5 role="button">: elemen aslinya sudah bertingkah
          // seperti tombol tapi tak bisa dijangkau keyboard. Tombol asli dapat
          // fokus dan Enter/Space gratis dari browser.
          <button
            type="button"
            key={option.key}
            className={`flex w-full cursor-pointer items-center gap-2 border-l-[3px] py-0.5 pr-2 pl-3 text-left text-13 font-medium capitalize ${
              step === option.key ? "border-accent-strong text-accent-primary" : "border-transparent text-secondary"
            }`}
            onClick={() => setStep(option.key)}
          >
            <option.Icon className="h-4 w-4" aria-hidden="true" />
            {t(option.labelKey)}
          </button>
        ))}
      </div>
    </div>
  );
}
