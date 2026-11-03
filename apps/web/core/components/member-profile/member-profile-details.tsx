/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kartu profil anggota
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Isi profil anggota: kontak, penempatan, dan aksi cepat. Satu komponen dipakai
 * dua tempat, kartu popover (`MemberProfileTrigger`) dan sidebar halaman profil
 * (`/[workspaceSlug]/profile/[userId]`), supaya keduanya tidak pernah berbeda isi.
 */

import { observer } from "mobx-react";
import { Link } from "react-router";
import { Building2, Mail, MessageSquare, Phone, SquareKanban } from "lucide-react";
// plane imports
import { getButtonStyling } from "@plane/propel/button";
import { Tooltip } from "@plane/propel/tooltip";
import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";
// hooks
import { useUser } from "@/hooks/store/user";
import { useParadiseModules } from "@/hooks/use-paradise-module";
// services
import type { TMemberPlacement } from "@/services/member-profile.service";
// local
import { useMemberProfile } from "./use-member-profile";

const TINGKAT_DIKENAL = new Set([10, 20, 30, 40]);

type Props = {
  workspaceSlug: string;
  userId: string;
  /** Sembunyikan "View work" saat sudah berada di halaman profil orang itu. */
  showViewWork?: boolean;
  onNavigate?: () => void;
  className?: string;
};

function PlacementLine({ placement }: { placement: TMemberPlacement }) {
  const { t } = useTranslation();
  const unit = placement.departemen ?? placement.divisi;
  const divisi = placement.departemen ? placement.divisi : null;
  const level = TINGKAT_DIKENAL.has(placement.tingkat) ? t(`profil_ui.level_${placement.tingkat}`) : null;
  return (
    <span className="min-w-0">
      {unit ? <span className="font-medium text-primary">{unit.nama}</span> : null}
      {divisi ? <span className="text-tertiary"> · {divisi.nama}</span> : null}
      {level ? <span className="block text-11 text-secondary">{level}</span> : null}
    </span>
  );
}

/** Data yang belum diisi pemiliknya: cukup "Not set" redup. Ikon baris sudah
 * menunjukkan datanya apa (lihat `DetailRow`). */
function NotSet() {
  const { t } = useTranslation();
  return <span className="block truncate text-tertiary">{t("profil_ui.not_set")}</span>;
}

/** Satu baris data profil. Nama datanya TIDAK pernah ditulis sebagai teks: ikon
 * yang mewakilinya, dan namanya muncul sebagai tooltip saat ikon disorot (juga
 * jadi label pembaca layar). Semua baris kartu profil wajib lewat sini. */
function DetailRow({ icon: Icon, label, children }: { icon: typeof Mail; label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2.5 text-13">
      <Tooltip tooltipContent={label} position="left">
        <span className="mt-0.5 shrink-0 cursor-help text-tertiary">
          <Icon className="size-3.5" aria-hidden />
          <span className="sr-only">{label}</span>
        </span>
      </Tooltip>
      <div className="min-w-0 flex-1 break-words">{children}</div>
    </div>
  );
}

export const MemberProfileDetails = observer(function MemberProfileDetails({
  workspaceSlug,
  userId,
  showViewWork = true,
  onNavigate,
  className,
}: Props) {
  const { t } = useTranslation();
  const { data: currentUser } = useUser();
  const { profile, error, isLoading } = useMemberProfile(workspaceSlug, userId);
  const isSelf = currentUser?.id === userId;
  const { isModuleEnabled } = useParadiseModules();
  const isChatEnabled = isModuleEnabled("chat");

  if (error) return <p className={cn("text-12 text-tertiary", className)}>{t("profil_ui.load_failed")}</p>;
  if (isLoading || !profile)
    return (
      <div className={cn("space-y-2", className)} aria-busy>
        <div className="h-3 w-3/4 animate-pulse rounded-sm bg-layer-1" />
        <div className="h-3 w-1/2 animate-pulse rounded-sm bg-layer-1" />
      </div>
    );

  const placements = profile.penempatan.filter((p) => p.departemen || p.divisi);

  return (
    <div className={cn("flex flex-col gap-3", className)}>
      <div className="flex flex-col gap-2">
        <DetailRow icon={Building2} label={t("profil_ui.placement")}>
          {placements.length > 0 ? (
            <span className="flex flex-col gap-1">
              {placements.map((p) => (
                <PlacementLine key={`${p.departemen?.id ?? ""}-${p.divisi?.id ?? ""}`} placement={p} />
              ))}
            </span>
          ) : (
            <NotSet />
          )}
        </DetailRow>
        {profile.email ? (
          <DetailRow icon={Mail} label={t("profil_ui.email")}>
            <a href={`mailto:${profile.email}`} className="text-primary hover:underline">
              {profile.email}
            </a>
          </DetailRow>
        ) : null}
        {/* null = peminta tidak berhak melihat kontak; "" = belum diisi. Baris
            tetap tampil saat kosong supaya orang tahu ekstensinya memang belum ada,
            bukan tersembunyi. */}
        {profile.phone_extension !== null ? (
          <DetailRow icon={Phone} label={t("profil_ui.phone_extension")}>
            {profile.phone_extension ? (
              <a href={`tel:${profile.phone_extension.replace(/\s/g, "")}`} className="text-primary hover:underline">
                {profile.phone_extension}
              </a>
            ) : (
              <NotSet />
            )}
          </DetailRow>
        ) : null}
      </div>
      <div className="flex flex-wrap gap-2">
        {!isSelf && profile.is_active && isChatEnabled ? (
          <Link
            to={`/${workspaceSlug}/chat?dengan=${userId}`}
            onClick={onNavigate}
            className={cn(getButtonStyling("primary", "sm"), "inline-flex items-center gap-1.5")}
          >
            <MessageSquare className="size-3.5" aria-hidden />
            {t("profil_ui.send_message")}
          </Link>
        ) : null}
        {showViewWork ? (
          <Link
            to={`/${workspaceSlug}/profile/${userId}`}
            onClick={onNavigate}
            className={cn(getButtonStyling("secondary", "sm"), "inline-flex items-center gap-1.5")}
          >
            <SquareKanban className="size-3.5" aria-hidden />
            {t("profil_ui.view_work")}
          </Link>
        ) : null}
      </div>
    </div>
  );
});
