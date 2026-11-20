/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: halaman Persetujuan workspace
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Keputusan user 2026-11-20: satu halaman untuk semua departemen yang diawasi.
 * Tab Persetujuan per departemen (`/projects/:id/persetujuan`) tetap ada.
 */

import { observer } from "mobx-react";
import { useParams } from "react-router";
// plane imports
import { useTranslation } from "@plane/i18n";
// components
import { PageHead } from "@/components/core/page-title";
import { AntreanPersetujuanWorkspace } from "@/components/issues/workspace-approvals/root";

function PersetujuanWorkspacePage() {
  const { t } = useTranslation();
  const { workspaceSlug } = useParams();
  if (!workspaceSlug) return <></>;

  return (
    <>
      <PageHead title={t("persetujuan_p29.title")} />
      <AntreanPersetujuanWorkspace workspaceSlug={workspaceSlug} />
    </>
  );
}

export default observer(PersetujuanWorkspacePage);
