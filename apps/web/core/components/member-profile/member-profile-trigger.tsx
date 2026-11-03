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

import { useState } from "react";
import type { ReactNode } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Popover } from "@plane/propel/popover";
import { Avatar } from "@plane/ui";
import { cn, getFileURL } from "@plane/utils";
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
};

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
  const showPresence = isModuleEnabled("chat") && currentUser?.id !== userId;
  return (
    <div className="flex items-center gap-3">
      <DenganKehadiran userId={showPresence ? userId : null}>
        <Avatar
          src={getFileURL(user?.avatar_url ?? "")}
          name={user?.display_name}
          size={40}
          className="text-18"
          showTooltip={false}
        />
      </DenganKehadiran>
      <div className="min-w-0">
        <p className="truncate text-14 font-semibold text-primary">{fullName}</p>
        <p className="flex items-center gap-1.5 truncate text-12 text-secondary">
          <span className="truncate">@{user?.display_name}</span>
          {currentUser?.id === userId ? (
            <span className="rounded-sm bg-layer-1 px-1 text-11 text-tertiary">{t("profil_ui.you")}</span>
          ) : null}
          {showPresence ? (
            <span className="text-11 text-tertiary">
              · <StatusKehadiranTeks userId={userId} />
            </span>
          ) : null}
          {profile && !profile.is_active ? (
            <span className="rounded-sm bg-danger-subtle px-1 text-11 text-danger-primary">
              {t("profil_ui.deactivated")}
            </span>
          ) : null}
        </p>
      </div>
    </div>
  );
});

export const MemberProfileTrigger = observer(function MemberProfileTrigger({
  userId,
  children,
  className,
  side = "bottom",
  align = "start",
}: Props) {
  const { t } = useTranslation();
  const { workspaceSlug } = useParams();
  const { getUserDetails } = useMember();
  const [isOpen, setIsOpen] = useState(false);

  const user = userId ? getUserDetails(userId) : undefined;
  const slug = workspaceSlug?.toString();
  if (!userId || !slug || !user || !isListableMember(user)) return <>{children}</>;

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <Popover.Button
        nativeButton={false}
        render={<span />}
        // base-ui memberi role="button" + tabIndex sendiri saat nativeButton=false.
        aria-label={t("profil_ui.open_profile", { name: user.display_name })}
        className={cn("inline-flex max-w-full cursor-pointer items-center rounded-sm outline-none", className)}
        onClick={(e) => {
          // Jangan biarkan klik membuka kartu work item / mengikuti tautan induk.
          e.stopPropagation();
          e.preventDefault();
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") e.stopPropagation();
        }}
      >
        {children}
      </Popover.Button>
      <Popover.Panel
        side={side}
        align={align}
        // z-index harus di positioner (elemen yang benar-benar diposisikan), bukan
        // di popup: dengan z di popup, kartu tertutup peek overview work item (z-25).
        positionerClassName="z-40"
        className="w-72 rounded-popover border-[0.5px] border-strong bg-surface-1 p-4 shadow-raised-200"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex flex-col gap-3">
          <CardHeader workspaceSlug={slug} userId={userId} />
          <MemberProfileDetails workspaceSlug={slug} userId={userId} onNavigate={() => setIsOpen(false)} />
        </div>
      </Popover.Panel>
    </Popover>
  );
});
