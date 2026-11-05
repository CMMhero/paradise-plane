/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kartu profil anggota
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Bungkus nama/avatar anggota mana pun supaya klik membuka kartu profilnya.
 *
 *   <MemberProfileTrigger userId={id}>
 *     <ButtonAvatars userIds={id} />
 *   </MemberProfileTrigger>
 *
 * Aturan yang dijaga di sini, bukan di tiap pemakai:
 * - Akun terhapus (KEP-50), bot, dan id yang tidak dikenal workspace dirender
 *   apa adanya tanpa kartu: tidak ada profil yang bisa dibuka.
 * - Klik tidak bocor ke induk (kartu kanban, baris tabel, tautan work item).
 * - Data profil baru diminta saat kartu dibuka (lihat `useMemberProfile`).
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// plane imports
import { useTranslation } from "@plane/i18n";
import { MemberProfileBadge, MemberProfileHeader, MemberProfilePopover } from "@plane/propel/member-profile-card";
import { Avatar } from "@plane/ui";
import { getFileURL } from "@plane/utils";
// components
import { DenganKehadiran, StatusKehadiranTeks } from "@/components/chat/titik-kehadiran";
// hooks
import { useMember } from "@/hooks/store/use-member";
import { useUser } from "@/hooks/store/user";
import { useParadiseModules } from "@/hooks/use-paradise-module";
// store
import { isListableMember } from "@/store/member/utils";
// local
import { MemberProfileDetails } from "./member-profile-details";
import { useMemberProfile } from "./use-member-profile";

type Props = {
  userId: string | null | undefined;
  children: ReactNode;
  className?: string;
  /** Default "bottom". */
  side?: "top" | "bottom" | "left" | "right";
  align?: "start" | "center" | "end";
  /** Buka kartu saat pointer singgah (mention), selain lewat klik. Default mati. */
  openOnHover?: boolean;
};

/** Jeda sebelum kartu hover terbuka / tertutup, supaya lewat sekilas tidak memunculkannya. */
const HOVER_OPEN_DELAY_MS = 350;
const HOVER_CLOSE_DELAY_MS = 150;

const CardHeader = observer(function CardHeader({ workspaceSlug, userId }: { workspaceSlug: string; userId: string }) {
  const { t } = useTranslation();
  const { getUserDetails } = useMember();
  const { isModuleEnabled } = useParadiseModules();
  const { data: currentUser } = useUser();
  // Sudah ada di cache SWR karena MemberProfileDetails memintanya dengan kunci yang sama.
  const { profile } = useMemberProfile(workspaceSlug, userId);
  const user = getUserDetails(userId);
  const fullName = [user?.first_name, user?.last_name].filter(Boolean).join(" ") || user?.display_name;
  // Kehadiran datang dari soket obrolan; tanpa modul chat statusnya tidak bermakna.
  const showPresence = isModuleEnabled("chat");
  return (
    <MemberProfileHeader
      avatar={
        <DenganKehadiran userId={showPresence ? userId : null}>
          <Avatar
            src={getFileURL(user?.avatar_url ?? "")}
            name={user?.display_name}
            size={40}
            className="text-18"
            showTooltip={false}
          />
        </DenganKehadiran>
      }
      fullName={fullName ?? ""}
      handle={user?.display_name ?? ""}
      badges={
        <>
          {currentUser?.id === userId ? <MemberProfileBadge>{t("profil_ui.you")}</MemberProfileBadge> : null}
          {showPresence ? (
            <span className="text-11 text-tertiary">
              · <StatusKehadiranTeks userId={userId} />
            </span>
          ) : null}
          {profile && !profile.is_active ? (
            <MemberProfileBadge tone="danger">{t("profil_ui.deactivated")}</MemberProfileBadge>
          ) : null}
        </>
      }
    />
  );
});

export const MemberProfileTrigger = observer(function MemberProfileTrigger({
  userId,
  children,
  className,
  side = "bottom",
  align = "start",
  openOnHover = false,
}: Props) {
  const { t } = useTranslation();
  const { workspaceSlug } = useParams();
  const { getUserDetails } = useMember();
  const [isOpen, setIsOpen] = useState(false);
  const hoverTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearHoverTimer = useCallback(() => {
    if (hoverTimer.current) clearTimeout(hoverTimer.current);
    hoverTimer.current = null;
  }, []);
  // Satu pemasa untuk buka dan tutup: pointer pindah dari pemicu ke kartu membatalkan penutupan.
  const hoverTo = useCallback(
    (next: boolean) => {
      clearHoverTimer();
      hoverTimer.current = setTimeout(() => setIsOpen(next), next ? HOVER_OPEN_DELAY_MS : HOVER_CLOSE_DELAY_MS);
    },
    [clearHoverTimer]
  );
  useEffect(() => clearHoverTimer, [clearHoverTimer]);

  const user = userId ? getUserDetails(userId) : undefined;
  const slug = workspaceSlug?.toString();
  if (!userId || !slug || !user || !isListableMember(user)) return <>{children}</>;

  return (
    <MemberProfilePopover
      open={isOpen}
      onOpenChange={setIsOpen}
      ariaLabel={t("profil_ui.open_profile", { name: user.display_name })}
      triggerClassName={className}
      side={side}
      align={align}
      hoverHandlers={
        openOnHover ? { onMouseEnter: () => hoverTo(true), onMouseLeave: () => hoverTo(false) } : undefined
      }
      card={
        <>
          <CardHeader workspaceSlug={slug} userId={userId} />
          <MemberProfileDetails workspaceSlug={slug} userId={userId} onNavigate={() => setIsOpen(false)} />
        </>
      }
    >
      {children}
    </MemberProfilePopover>
  );
});
