/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import useSWR from "swr";
import { Loader } from "@plane/ui";
// components
import { PageWrapper } from "@/components/common/page-wrapper";
import { MenuTabs } from "@/components/common/section-tabs";
// hooks
import { godmodeStrings, useGodmodeStrings } from "@/app/i18n/godmode";
import { useInstance } from "@/hooks/store";
// types
import type { Route } from "./+types/page";
// local
import { InstanceAIForm } from "./form";

const InstanceAIPage = observer(function InstanceAIPage(_props: Route.ComponentProps) {
  const { s } = useGodmodeStrings();
  // store
  const { fetchInstanceConfigurations, formattedConfig } = useInstance();

  useSWR("INSTANCE_CONFIGURATIONS", () => fetchInstanceConfigurations());

  return (
    <PageWrapper
      header={{
        title: s.settings.tabs.integrations_ai.title,
        description: s.settings.tabs.integrations_ai.description,
      }}
    >
      <MenuTabs menu="integrations" />
      {formattedConfig ? (
        <InstanceAIForm config={formattedConfig} />
      ) : (
        <Loader className="space-y-8">
          <Loader.Item height="50px" width="40%" />
          <div className="grid w-2/3 grid-cols-2 gap-x-8 gap-y-4">
            <Loader.Item height="50px" />
            <Loader.Item height="50px" />
          </div>
          <Loader.Item height="50px" width="20%" />
        </Loader>
      )}
    </PageWrapper>
  );
});

export const meta: Route.MetaFunction = () => [
  { title: `${godmodeStrings.settings.tabs.integrations_ai.title} - God Mode` },
];

export default InstanceAIPage;
