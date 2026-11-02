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
import { ApiKeysTabs } from "@/components/common/section-tabs";
// hooks
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { useInstance } from "@/hooks/store";
// types
import type { Route } from "./+types/page";
// local
import { InstanceImageConfigForm } from "./form";

const InstanceImagePage = observer(function InstanceImagePage(_props: Route.ComponentProps) {
  const { s } = useGodmodeStrings();
  // store
  const { formattedConfig, fetchInstanceConfigurations } = useInstance();

  useSWR("INSTANCE_CONFIGURATIONS", () => fetchInstanceConfigurations());

  return (
    <PageWrapper
      header={{
        title: s.api_keys.title,
        description: s.api_keys.image_description,
      }}
    >
      <ApiKeysTabs />
      {formattedConfig ? (
        <InstanceImageConfigForm config={formattedConfig} />
      ) : (
        <Loader className="space-y-8">
          <Loader.Item height="50px" width="50%" />
          <Loader.Item height="50px" width="20%" />
        </Loader>
      )}
    </PageWrapper>
  );
});

export const meta: Route.MetaFunction = () => [{ title: "Image library - God Mode" }];

export default InstanceImagePage;
