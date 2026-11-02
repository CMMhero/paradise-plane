/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: modul yang dimatikan dari God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ReactNode } from "react";
import { observer } from "mobx-react";
import { useLocation, useNavigate, useParams } from "react-router";
import { useTranslation } from "@plane/i18n";
import { EmptyStateDetailed } from "@plane/propel/empty-state";
import { useParadiseModules } from "@/hooks/use-paradise-module";
import { moduleForPath } from "@/lib/paradise-modules";

/**
 * Satu gerbang untuk semua halaman modul. Menu yang hilang belum cukup:
 * bookmark, tautan di notifikasi, dan Power K masih bisa membuka URL-nya.
 * Dipasang sekali di layout workspace, jadi halaman baru di bawah pola yang
 * sama ikut terjaga tanpa perlu diingat.
 */
export const ParadiseModuleGate = observer(function ParadiseModuleGate({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  const { workspaceSlug } = useParams();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { isModuleEnabled } = useParadiseModules();

  const module = moduleForPath(pathname);
  if (!module || isModuleEnabled(module)) return <>{children}</>;

  return (
    <div className="grid h-full w-full place-items-center bg-surface-1">
      <EmptyStateDetailed
        title={t("module_gate_ui.title")}
        description={t("module_gate_ui.description")}
        assetKey="no-access"
        assetClassName="size-40"
        actions={[{ label: t("module_gate_ui.back_home"), onClick: () => navigate(`/${workspaceSlug ?? ""}/`) }]}
      />
    </div>
  );
});
