/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// components
import { godmodeStrings, useGodmodeStrings } from "@/app/i18n/godmode";
import { PageWrapper } from "@/components/common/page-wrapper";
import { MenuTabs } from "@/components/common/section-tabs";
// hooks
import { useInstance } from "@/hooks/store";
// local imports
import { GeneralConfigurationForm } from "./form";
// types
import type { Route } from "./+types/page";

function GeneralPage() {
  const { s } = useGodmodeStrings();
  const { instance, instanceAdmins } = useInstance();

  return (
    <PageWrapper header={s.settings.tabs.general_instance}>
      <MenuTabs menu="general" />
      {instance && instanceAdmins && <GeneralConfigurationForm instance={instance} instanceAdmins={instanceAdmins} />}
    </PageWrapper>
  );
}

export const meta: Route.MetaFunction = () => [
  { title: `${godmodeStrings.settings.tabs.general_instance.title} - God Mode` },
];

export default observer(GeneralPage);
