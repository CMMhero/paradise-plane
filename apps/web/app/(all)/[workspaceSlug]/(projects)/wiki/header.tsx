/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kepala Wiki
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { Library } from "lucide-react";
import { Breadcrumbs, Header } from "@plane/ui";
// components
import { BreadcrumbLink } from "@/components/common/breadcrumb-link";

/**
 * Kepala Wiki, sengaja hanya berisi namanya.
 *
 * Wiki dulu menumpang halaman daftar Pages project, dan kepalanya membawa serta
 * tombol "buat halaman" beserta breadcrumb project. Orang yang datang untuk
 * MEMBACA materi tidak sedang membuat halaman, dan pemilik instance benar
 * ketika bilang Wiki tidak seharusnya terlihat seperti project biasa.
 */
export const WikiHeader = observer(function WikiHeader() {
  return (
    <Header>
      <Header.LeftItem>
        <Breadcrumbs>
          <Breadcrumbs.Item
            component={<BreadcrumbLink label="Wiki" icon={<Library className="h-4 w-4 text-tertiary" />} />}
          />
        </Breadcrumbs>
      </Header.LeftItem>
    </Header>
  );
});
