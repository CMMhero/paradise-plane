/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: indikator kehadiran obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ReactNode } from "react";
import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";
import { useSambungKehadiran, useStatusKehadiran, type TStatusKehadiran } from "@/hooks/use-kehadiran";
import { useParadiseModules } from "@/hooks/use-paradise-module";

/** Warna titik. Offline = cincin kosong, bukan abu-abu penuh, supaya tidak
 * bergantung pada warna saja untuk dibedakan dari away. */
const GAYA: Record<TStatusKehadiran, string> = {
  online: "bg-success-primary",
  away: "bg-warning-primary",
  offline: "border-2 border-strong bg-surface-1",
};

/** Titik status saja. Teks statusnya ikut dibacakan pembaca layar. */
export function TitikKehadiran({ userId, className }: { userId: string | null | undefined; className?: string }) {
  const { t } = useTranslation();
  const status = useStatusKehadiran(userId);
  const label = t(`chatux_kelola_ui.presence_${status}`);
  return (
    <span title={label} className={cn("inline-block size-2.5 shrink-0 rounded-full", GAYA[status], className)}>
      <span className="sr-only">{label}</span>
    </span>
  );
}

/** Avatar dengan titik kehadiran di pojok kanan bawah. */
export function DenganKehadiran({ userId, children }: { userId: string | null | undefined; children: ReactNode }) {
  // Tanpa orang (mis. catatan untuk diri sendiri): avatar polos, tanpa titik.
  if (!userId) return <>{children}</>;
  return (
    <span className="relative inline-flex shrink-0">
      {children}
      <TitikKehadiran
        userId={userId}
        className="absolute -right-0.5 -bottom-0.5 size-3 outline-2 outline-(color:--bg-surface-1)"
      />
    </span>
  );
}

/** Teks status ("Online", "Away", "Offline") untuk kepala percakapan. */
export function StatusKehadiranTeks({ userId }: { userId: string | null | undefined }) {
  const { t } = useTranslation();
  const status = useStatusKehadiran(userId);
  return <>{t(`chatux_kelola_ui.presence_${status}`)}</>;
}

/** Dipasang sekali di lapisan workspace: membuka soket kehadiran tab ini. */
export const SambunganKehadiran = observer(function SambunganKehadiran({ workspaceSlug }: { workspaceSlug: string }) {
  const { isModuleEnabled } = useParadiseModules();
  useSambungKehadiran(workspaceSlug, isModuleEnabled("chat"));
  return null;
});
