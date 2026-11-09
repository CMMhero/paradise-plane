/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: tab Materials project departemen (KEP-97)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Materi Wiki departemen dikelola dari project departemennya. Halaman ini
 * dijaga modul Wiki di God Mode (`ParadiseModuleGate`, pola `materials` di
 * `lib/paradise-modules.ts`); isinya dan izinnya milik Wiki.
 */

import { observer } from "mobx-react";
import { useParams } from "react-router";
import { useTranslation } from "@plane/i18n";
// components
import { PageHead } from "@/components/core/page-title";
import { MateriDepartemen } from "@/app/(all)/[workspaceSlug]/(projects)/wiki/materi-departemen";

function MateriDepartemenPage() {
  const { t } = useTranslation();
  const { workspaceSlug, projectId } = useParams();
  if (!workspaceSlug || !projectId) return <></>;

  return (
    <>
      <PageHead title={t("wiki_ui.tab.title")} />
      <MateriDepartemen workspaceSlug={workspaceSlug} projectId={projectId} />
    </>
  );
}

export default observer(MateriDepartemenPage);
