/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { CloseIcon, PlaneLockup } from "@plane/propel/icons";
// assets
import IssuesTour from "@/app/assets/onboarding/issues.webp?url";
import ModulesTour from "@/app/assets/onboarding/modules.webp?url";
import PagesTour from "@/app/assets/onboarding/pages.webp?url";
import ViewsTour from "@/app/assets/onboarding/views.webp?url";
// hooks
import { useUser } from "@/hooks/store/user";
// local imports
import { TourSidebar } from "./sidebar";

export type TOnboardingTourProps = {
  onComplete: () => void;
};

// Cycles were removed from Paradise (KEP-53), so the tour no longer has a Cycles step.
export type TTourSteps = "welcome" | "work-items" | "modules" | "views" | "pages";

// `titleKey` / `descriptionKey` are i18n keys, resolved at render time.
const TOUR_STEPS: {
  key: TTourSteps;
  titleKey: string;
  descriptionKey: string;
  image: string;
  prevStep?: TTourSteps;
  nextStep?: TTourSteps;
}[] = [
  {
    key: "work-items",
    titleKey: "onboarding_ui.tour_work_items_title",
    descriptionKey: "onboarding_ui.tour_work_items_description",
    image: IssuesTour,
    nextStep: "modules",
  },
  {
    key: "modules",
    titleKey: "onboarding_ui.tour_modules_title",
    descriptionKey: "onboarding_ui.tour_modules_description",
    image: ModulesTour,
    prevStep: "work-items",
    nextStep: "views",
  },
  {
    key: "views",
    titleKey: "onboarding_ui.tour_views_title",
    descriptionKey: "onboarding_ui.tour_views_description",
    image: ViewsTour,
    prevStep: "modules",
    nextStep: "pages",
  },
  {
    key: "pages",
    titleKey: "onboarding_ui.tour_pages_title",
    descriptionKey: "onboarding_ui.tour_pages_description",
    image: PagesTour,
    prevStep: "views",
  },
];

export const TourRoot = observer(function TourRoot(props: TOnboardingTourProps) {
  const { onComplete } = props;
  const { t } = useTranslation();
  // states
  const [step, setStep] = useState<TTourSteps>("welcome");
  // store hooks
  const { data: currentUser } = useUser();

  const currentStepIndex = TOUR_STEPS.findIndex((tourStep) => tourStep.key === step);
  const currentStep = TOUR_STEPS[currentStepIndex];

  return (
    <>
      {step === "welcome" ? (
        <div className="w-4/5 overflow-hidden rounded-[10px] bg-surface-1 md:w-1/2 lg:w-2/5">
          <div className="h-full overflow-hidden">
            <div className="grid h-64 place-items-center bg-accent-primary">
              <PlaneLockup className="h-10 w-auto text-on-color" />
            </div>
            <div className="flex flex-col overflow-y-auto p-6">
              <h3 className="font-semibold sm:text-18">
                {t("onboarding_ui.tour_welcome_title", {
                  name: [currentUser?.first_name, currentUser?.last_name].filter(Boolean).join(" "),
                })}
              </h3>
              <p className="mt-3 text-13 text-secondary">{t("onboarding_ui.tour_welcome_description")}</p>
              <div className="flex h-full items-end">
                <div className="mt-12 flex items-center gap-6">
                  <Button
                    variant="primary"
                    onClick={() => {
                      setStep("work-items");
                    }}
                  >
                    {t("onboarding_ui.tour_start")}
                  </Button>
                  <button
                    type="button"
                    className="bg-transparent text-11 font-medium text-accent-primary outline-subtle-1"
                    onClick={() => {
                      onComplete();
                    }}
                  >
                    {t("onboarding_ui.tour_skip")}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="relative grid h-3/5 w-4/5 grid-cols-10 overflow-hidden rounded-[10px] bg-surface-1 sm:h-3/4 md:w-1/2 lg:w-3/5">
          <button
            type="button"
            className="fixed top-[19%] right-[9%] z-10 translate-x-1/2 -translate-y-1/2 cursor-pointer rounded-control border border-strong bg-surface-1 p-1 sm:top-[11.5%] md:right-[24%] lg:right-[19%]"
            onClick={onComplete}
          >
            <CloseIcon className="border-strong- h-3 w-3 text-primary" />
          </button>
          <TourSidebar step={step} setStep={setStep} />
          <div className="col-span-10 h-full overflow-hidden lg:col-span-7">
            <div
              className={`flex h-1/2 items-end overflow-hidden bg-accent-primary sm:h-3/5 ${
                currentStepIndex % 2 === 0 ? "justify-end" : "justify-start"
              }`}
            >
              <img
                src={currentStep?.image}
                className="h-full w-full object-cover"
                alt={currentStep ? t(currentStep.titleKey) : ""}
              />
            </div>
            <div className="flex h-1/2 flex-col overflow-y-auto p-4 sm:h-2/5">
              <h3 className="font-semibold sm:text-18">{currentStep ? t(currentStep.titleKey) : ""}</h3>
              <p className="mt-3 text-13 text-secondary">{currentStep ? t(currentStep.descriptionKey) : ""}</p>
              <div className="mt-3 flex h-full items-end justify-between gap-4">
                <div className="flex items-center gap-4">
                  {currentStep?.prevStep && (
                    <Button variant="secondary" onClick={() => setStep(currentStep.prevStep ?? "welcome")}>
                      {t("common.back")}
                    </Button>
                  )}
                  {currentStep?.nextStep && (
                    <Button variant="primary" onClick={() => setStep(currentStep.nextStep ?? "work-items")}>
                      {t("common.next")}
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
});
