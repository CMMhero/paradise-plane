/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: tab Persetujuan per divisi
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Keputusan user 2026-10-16: antrean persetujuan tinggal di dalam tiap divisi
 * (sebelah Issues/Intake), bukan halaman workspace tersendiri. Atasan membuka
 * divisinya → tab Persetujuan → putuskan. Staf melihat pengajuannya + tombol
 * ajukan-ulang di divisi yang sama.
 */

import { observer } from "mobx-react";
import { useParams } from "react-router";
// plane imports
import { useTranslation } from "@plane/i18n";
// components
import { PageHead } from "@/components/core/page-title";
import { AntreanPersetujuan } from "@/components/issues/approval-queue";

function PersetujuanDivisiPage() {
  const { t } = useTranslation();
  const { workspaceSlug, projectId } = useParams();
  if (!workspaceSlug || !projectId) return <></>;

  return (
    <div className="h-full w-full overflow-y-auto px-6 py-5">
      <PageHead title={t("sidebar.persetujuan")} />
      <AntreanPersetujuan workspaceSlug={workspaceSlug} projectId={projectId} />
    </div>
  );
}

export default observer(PersetujuanDivisiPage);
