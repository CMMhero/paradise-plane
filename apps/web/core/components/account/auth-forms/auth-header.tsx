/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import useSWR from "swr";
import { useTranslation } from "@plane/i18n";
import type { IWorkspaceMemberInvitation } from "@plane/types";
// components
import { LogoSpinner } from "@/components/common/logo-spinner";
import { WorkspaceLogo } from "@/components/workspace/logo";
// helpers
import { EAuthModes, EAuthSteps } from "@/helpers/authentication.helper";
// services
import { WorkspaceService } from "@/services/workspace.service";

type TAuthHeader = {
  workspaceSlug: string | undefined;
  invitationId: string | undefined;
  invitationEmail: string | undefined;
  authMode: EAuthModes;
  currentAuthStep: EAuthSteps;
};

const Titles = {
  [EAuthModes.SIGN_IN]: {
    [EAuthSteps.EMAIL]: {
      header: "Sign in",
      subHeader: "Use your Space Paradise Perkasa account.",
    },
    [EAuthSteps.PASSWORD]: {
      header: "Sign in",
      subHeader: "Use your Space Paradise Perkasa account.",
    },
    [EAuthSteps.UNIQUE_CODE]: {
      header: "Sign in",
      subHeader: "Use your Space Paradise Perkasa account.",
    },
  },
  [EAuthModes.SIGN_UP]: {
    [EAuthSteps.EMAIL]: {
      header: "Create your account",
      subHeader: "Set up your Space Paradise Perkasa account.",
    },
    [EAuthSteps.PASSWORD]: {
      header: "Create your account",
      subHeader: "Set up your Space Paradise Perkasa account.",
    },
    [EAuthSteps.UNIQUE_CODE]: {
      header: "Create your account",
      subHeader: "Set up your Space Paradise Perkasa account.",
    },
  },
};

const workSpaceService = new WorkspaceService();

export const AuthHeader = observer(function AuthHeader(props: TAuthHeader) {
  const { workspaceSlug, invitationId, invitationEmail, authMode, currentAuthStep } = props;
  // plane imports
  const { t } = useTranslation();

  const { data: invitation, isLoading } = useSWR(
    workspaceSlug && invitationId ? `WORKSPACE_INVITATION_${workspaceSlug}_${invitationId}` : null,
    async () => workspaceSlug && invitationId && workSpaceService.getWorkspaceInvitation(workspaceSlug, invitationId),
    {
      revalidateOnFocus: false,
      shouldRetryOnError: false,
    }
  );

  const getHeaderSubHeader = (
    step: EAuthSteps,
    mode: EAuthModes,
    memberInvitation: IWorkspaceMemberInvitation | undefined,
    email: string | undefined
  ) => {
    if (memberInvitation && email && memberInvitation.email === email && memberInvitation.workspace) {
      const workspace = memberInvitation.workspace;
      return {
        header: (
          <span className="relative inline-flex items-center gap-2">
            {t("common.join")}{" "}
            <WorkspaceLogo logo={workspace?.logo_url} name={workspace?.name} classNames="size-9 flex-shrink-0" />{" "}
            {workspace.name}
          </span>
        ),
        subHeader:
          mode == EAuthModes.SIGN_UP
            ? "Create an account to start managing work with your team."
            : "Log in to start managing work with your team.",
      };
    }

    return Titles[mode][step];
  };

  const { header, subHeader } = getHeaderSubHeader(currentAuthStep, authMode, invitation || undefined, invitationEmail);

  if (isLoading)
    return (
      <div className="flex h-full w-full items-center justify-center">
        <LogoSpinner />
      </div>
    );

  return <AuthHeaderBase subHeader={subHeader} header={header} />;
});

type TAuthHeaderBase = {
  header: React.ReactNode;
  subHeader: string;
};

// Paradise: small "Internal task tracker" label, a large heading, then a plain
// line under it (was two equal-weight headings).
export function AuthHeaderBase({ header, subHeader }: TAuthHeaderBase) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col">
      <span className="text-13 font-medium text-accent-primary">{t("login_ui.eyebrow")}</span>
      <h1 className="mt-2 text-32 leading-tight font-semibold tracking-tight text-primary">{header}</h1>
      <p className="mt-2 text-14 text-secondary">{subHeader}</p>
    </div>
  );
}
