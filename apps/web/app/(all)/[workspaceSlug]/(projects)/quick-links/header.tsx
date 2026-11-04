/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { Link2 } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { Breadcrumbs, Header } from "@plane/ui";
// components
import { BreadcrumbLink } from "@/components/common/breadcrumb-link";
// hooks
import { useHome } from "@/hooks/store/use-home";

export const WorkspaceQuickLinksHeader = observer(function WorkspaceQuickLinksHeader() {
  const { t } = useTranslation();
  const {
    quickLinks: { toggleLinkModal, setLinkData },
  } = useHome();
  // Paradise KEP-82: admins pick Public in the same modal, so one Add button is enough.

  const handleAdd = () => {
    setLinkData(undefined);
    toggleLinkModal(true);
  };

  return (
    <Header>
      <Header.LeftItem>
        <Breadcrumbs>
          <Breadcrumbs.Item
            component={
              <BreadcrumbLink
                label={t("home.quick_links.title_plural")}
                icon={<Link2 className="size-4 text-secondary" />}
              />
            }
          />
        </Breadcrumbs>
      </Header.LeftItem>
      <Header.RightItem>
        <Button variant="primary" size="lg" onClick={handleAdd}>
          {t("home.quick_links.add")}
        </Button>
      </Header.RightItem>
    </Header>
  );
});
