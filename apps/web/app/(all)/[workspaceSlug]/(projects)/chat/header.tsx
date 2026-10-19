/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { MessageSquare } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
// ui
import { Breadcrumbs, Header } from "@plane/ui";
// components
import { BreadcrumbLink } from "@/components/common/breadcrumb-link";

export const ChatHeader = observer(function ChatHeader() {
  const { t } = useTranslation();

  return (
    <Header>
      <Header.LeftItem>
        <Breadcrumbs>
          <Breadcrumbs.Item
            component={
              <BreadcrumbLink label={t("chat_nav")} icon={<MessageSquare className="h-4 w-4 text-tertiary" />} />
            }
          />
        </Breadcrumbs>
      </Header.LeftItem>
    </Header>
  );
});
