/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useTranslation } from "@plane/i18n";
import { observer } from "mobx-react";
import { Controller, useForm } from "react-hook-form";
import { Box, PenTool, Rocket, Monitor, RefreshCw } from "lucide-react";
// plane imports
import { Button } from "@plane/propel/button";
import { CheckIcon, ViewsIcon } from "@plane/propel/icons";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TUserProfile } from "@plane/types";
import { EOnboardingSteps } from "@plane/types";
// hooks
import { useUserProfile } from "@/hooks/store/user";
// local components
import { CommonOnboardingHeader } from "../common";
import type { TProfileSetupFormValues } from "../profile/root";

type Props = {
  handleStepChange: (step: EOnboardingSteps, skipInvites?: boolean) => void;
};

// `id` is the value stored on the profile; `labelKey` is the i18n key shown to the user.
const ROLES = [
  { id: "product-manager", labelKey: "onboarding_ui.role_product_manager", icon: Box },
  { id: "engineering-manager", labelKey: "onboarding_ui.role_engineering_manager", icon: ViewsIcon },
  { id: "designer", labelKey: "onboarding_ui.role_designer", icon: PenTool },
  { id: "developer", labelKey: "onboarding_ui.role_developer", icon: Monitor },
  { id: "founder-executive", labelKey: "onboarding_ui.role_founder_executive", icon: Rocket },
  { id: "operations-manager", labelKey: "onboarding_ui.role_operations_manager", icon: RefreshCw },
  { id: "others", labelKey: "onboarding_ui.role_other", icon: Box },
] as const;

const defaultValues = {
  role: "",
};

export const RoleSetupStep = observer(function RoleSetupStep({ handleStepChange }: Props) {
  const { t } = useTranslation();
  // store hooks
  const { data: profile, updateUserProfile } = useUserProfile();
  // form info
  const {
    handleSubmit,
    control,
    formState: { errors, isSubmitting, isValid },
  } = useForm<TProfileSetupFormValues>({
    defaultValues: {
      ...defaultValues,
      role: profile?.role,
    },
    mode: "onChange",
  });

  // handle submit
  const handleSubmitUserPersonalization = async (formData: TProfileSetupFormValues) => {
    const profileUpdatePayload: Partial<TUserProfile> = {
      role: formData.role,
    };
    try {
      // Promise.all dibuang: isinya tinggal satu promise sejak baris keduanya
      // dikomentari upstream.
      await updateUserProfile(profileUpdatePayload);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("success"),
        message: t("onboarding_ui.profile_saved"),
      });
    } catch {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("error"),
        message: t("onboarding_ui.profile_save_failed"),
      });
    }
  };

  const onSubmit = async (formData: TProfileSetupFormValues) => {
    if (!profile) return;
    await handleSubmitUserPersonalization(formData);
    handleStepChange(EOnboardingSteps.ROLE_SETUP);
  };

  const handleSkip = () => {
    handleStepChange(EOnboardingSteps.ROLE_SETUP);
  };

  const isButtonDisabled = isSubmitting || !isValid;

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-10">
      {/* Header */}
      <CommonOnboardingHeader
        title={t("onboarding_ui.role_title")}
        description={t("shared_ui.onboarding_role_description")}
      />
      {/* Role Selection */}
      <div className="flex flex-col gap-3">
        <p className="text-body-sm-semibold text-placeholder">{t("onboarding_ui.select_one")}</p>
        <Controller
          control={control}
          name="role"
          rules={{
            required: t("common.errors.required"),
          }}
          render={({ field: { value, onChange } }) => (
            <div className="flex flex-col gap-3">
              {ROLES.map((role) => {
                const Icon = role.icon;
                const isSelected = value === role.id;

                return (
                  <button
                    key={role.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      e.preventDefault();
                      onChange(role.id);
                    }}
                    className={`flex w-full items-center justify-between rounded-lg border px-3 py-2 transition-all duration-200 ${
                      isSelected
                        ? "border-accent-strong bg-accent-subtle text-accent-primary"
                        : "border-subtle text-tertiary hover:border-strong"
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      <Icon className="size-3.5" />
                      <span className="text-body-sm-semibold">{t(role.labelKey)}</span>
                    </div>
                    {isSelected && (
                      <>
                        <button
                          className={`flex size-4 items-center justify-center rounded-sm border-2 border-accent-strong bg-accent-primary`}
                        >
                          <CheckIcon className="h-3 w-3 text-on-color" />
                        </button>
                      </>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        />
        {errors.role && <span className="text-13 text-danger-primary">{errors.role.message}</span>}
      </div>
      {/* Action Buttons */}
      <div className="space-y-3">
        <Button variant="primary" type="submit" className="w-full" size="xl" disabled={isButtonDisabled}>
          {t("common.continue")}
        </Button>
        <Button variant="ghost" onClick={handleSkip} className="w-full text-tertiary" size="xl">
          {t("onboarding_ui.skip")}
        </Button>
      </div>
    </form>
  );
});
