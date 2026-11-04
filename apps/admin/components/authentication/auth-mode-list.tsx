/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: authentication method cards, split across tabs
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Methods (codes, passwords) and Providers (Google, GitHub, GitLab, Gitea) are
 * two tabs now, but one rule still spans both: at least one method must stay on.
 * So both tabs build the full list and only render their own slice.
 */

import { useCallback, useRef, useState } from "react";
import { observer } from "mobx-react";
import { useTheme } from "next-themes";
import useSWR from "swr";
import { setPromiseToast, setToast, TOAST_TYPE } from "@plane/propel/toast";
import type {
  TInstanceAuthenticationModeKeys,
  TInstanceAuthenticationModes,
  TInstanceConfigurationKeys,
} from "@plane/types";
import { resolveGeneralTheme } from "@plane/utils";
// components
import { AuthenticationMethodCard } from "@/components/authentication/authentication-method-card";
// helpers
import { canDisableAuthMethod } from "@/helpers/authentication";
// hooks
import { useAuthenticationModes } from "@/hooks/oauth";
import { useInstance } from "@/hooks/store";

type Props = {
  /** Which cards this tab shows. */
  modes: TInstanceAuthenticationModeKeys[];
};

export const AuthModeList = observer(function AuthModeList({ modes }: Props) {
  const { resolvedTheme: resolvedThemeAdmin } = useTheme();
  const resolvedTheme = resolveGeneralTheme(resolvedThemeAdmin);
  // Ref to the latest modes for validation (avoids a circular dependency)
  const authenticationModesRef = useRef<TInstanceAuthenticationModes[]>([]);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const { fetchInstanceConfigurations, formattedConfig, updateInstanceConfigurations } = useInstance();

  useSWR("INSTANCE_CONFIGURATIONS", () => fetchInstanceConfigurations());

  const updateConfig = useCallback(
    (key: TInstanceConfigurationKeys, value: string): void => {
      if (value === "0") {
        const currentAuthModes = authenticationModesRef.current;
        const isAuthMethodKey = currentAuthModes.some((method) => method.enabledConfigKey === key);
        if (isAuthMethodKey && !canDisableAuthMethod(key, currentAuthModes, formattedConfig)) {
          setToast({
            type: TOAST_TYPE.ERROR,
            title: "Cannot disable authentication",
            message:
              "At least one authentication method must remain enabled. Please enable another method before disabling this one.",
          });
          return;
        }
      }

      setIsSubmitting(true);
      const updateConfigPromise = updateInstanceConfigurations({ [key]: value });
      setPromiseToast(updateConfigPromise, {
        loading: "Saving configuration",
        success: { title: "Success", message: () => "Configuration saved successfully" },
        error: { title: "Error", message: () => "Failed to save configuration" },
      });
      void updateConfigPromise
        .then(() => {
          setIsSubmitting(false);
          return undefined;
        })
        .catch((err) => {
          console.error(err);
          setIsSubmitting(false);
        });
    },
    [formattedConfig, updateInstanceConfigurations]
  );

  const authenticationModes = useAuthenticationModes({ disabled: isSubmitting, updateConfig, resolvedTheme });
  authenticationModesRef.current = authenticationModes;

  return (
    <div className="space-y-3">
      {authenticationModes
        .filter((method) => modes.includes(method.key))
        .map((method) => (
          <AuthenticationMethodCard
            key={method.key}
            name={method.name}
            description={method.description}
            icon={method.icon}
            config={method.config}
            disabled={isSubmitting}
            unavailable={method.unavailable}
          />
        ))}
    </div>
  );
});
