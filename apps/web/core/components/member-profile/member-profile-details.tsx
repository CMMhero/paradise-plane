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
import useSWR, { type SWRConfiguration } from "swr";
import { MessageSquare, SquareKanban } from "lucide-react";
// plane imports
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { getButtonStyling } from "@plane/propel/button";
import { MemberProfileFields, MemberProfileSkeleton } from "@plane/propel/member-profile-card";
import type { TMemberProfilePlacement } from "@plane/propel/member-profile-card";
import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";
// hooks
import { useUser, useUserPermissions } from "@/hooks/store/user";
import { useParadiseModules } from "@/hooks/use-paradise-module";
import { UserService } from "@/services/user.service";
// local
import { useMemberProfile } from "./use-member-profile";

const TINGKAT_DIKENAL = new Set([10, 20, 30, 35, 40]);

// Sama dengan kunci SWR di `use-aturan-tugas.ts`, jadi status Super Admin diambil sekali per sesi.
const OPSI_STATUS_SUPER_ADMIN: SWRConfiguration = {
  revalidateIfStale: false,
  revalidateOnFocus: false,
};
const userService = new UserService();

type Props = {
  workspaceSlug: string;
  userId: string;
  /** Sembunyikan "View work" saat sudah berada di halaman profil orang itu. */
  showViewWork?: boolean;
  onNavigate?: () => void;
  className?: string;
};

export const MemberProfileDetails = observer(function MemberProfileDetails({
  workspaceSlug,
  userId,
  showViewWork = true,
  onNavigate,
  className,
}: Props) {
  const { t } = useTranslation();
  const { data: currentUser } = useUser();
  const { allowPermissions } = useUserPermissions();
  const { data: statusAdmin } = useSWR(
    currentUser?.id ? "STATUS_SUPER_ADMIN" : null,
    () => userService.currentUserInstanceAdminStatus(),
    OPSI_STATUS_SUPER_ADMIN
  );
  const { profile, error, isLoading } = useMemberProfile(workspaceSlug, userId);
  const isSelf = currentUser?.id === userId;
  const { isModuleEnabled } = useParadiseModules();
  const isChatEnabled = isModuleEnabled("chat");
  // "View work" hanya untuk admin workspace dan Super Admin instance.
  const bisaLihatKerja =
    showViewWork &&
    (!!statusAdmin?.is_instance_admin ||
      allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.WORKSPACE, workspaceSlug));

  if (error) return <p className={cn("text-12 text-tertiary", className)}>{t("profil_ui.load_failed")}</p>;
  if (isLoading || !profile) return <MemberProfileSkeleton className={className} />;

  // Direktur dan sekretaris jabatannya melekat pada perusahaan, bukan pada divisi atau
  // departemen, jadi barisnya tanpa tempat tetap harus tampil sebagai jenjang.
  const placements: TMemberProfilePlacement[] = profile.penempatan
    .map((p) => ({
      key: `${p.departemen?.id ?? ""}-${p.divisi?.id ?? ""}-${p.tingkat}`,
      division: p.divisi,
      department: p.departemen,
      levelLabel: TINGKAT_DIKENAL.has(p.tingkat) ? t(`profil_ui.level_${p.tingkat}`) : null,
    }))
    .filter((p) => p.department || p.division || p.levelLabel);

  return (
    <div className={cn("flex flex-col gap-3", className)}>
      <MemberProfileFields
        labels={{
          placement: t("profil_ui.org_placement"),
          morePlacements: (count) => t("profil_ui.more_placements", { count }),
          email: t("profil_ui.email"),
          phoneExtension: t("profil_ui.phone_extension"),
          notSet: t("profil_ui.not_set"),
        }}
        placements={placements}
        email={profile.email}
        phoneExtension={profile.phone_extension}
      />
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
        {bisaLihatKerja ? (
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
