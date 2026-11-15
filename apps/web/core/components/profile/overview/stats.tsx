/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import Link from "next/link";
import { useParams } from "next/navigation";

// ui
import { useTranslation } from "@plane/i18n";
import { UserCirclePropertyIcon, CreateIcon, LayerStackIcon } from "@plane/propel/icons";
import type { IUserProfileData } from "@plane/types";
import { Card, ECardSpacing, ECardDirection } from "@plane/ui";
// types

type Props = {
  userProfile: IUserProfileData | undefined;
};

export function ProfileStats({ userProfile }: Props) {
  const { workspaceSlug, userId } = useParams();

  const { t } = useTranslation();

  const overviewCards = [
    {
      icon: CreateIcon,
      route: "created",
      i18n_title: "profile.stats.created",
      value: userProfile?.created_issues,
    },
    {
      icon: UserCirclePropertyIcon,
      route: "assigned",
      i18n_title: "profile.stats.assigned",
      value: userProfile?.assigned_issues,
    },
    {
      icon: LayerStackIcon,
      route: "subscribed",
      i18n_title: "profile.stats.subscribed",
      value: userProfile?.subscribed_issues,
    },
  ];

  return (
    <div className="space-y-2">
      <h3 className="text-16 font-medium">{t("profile.stats.overview")}</h3>
      {/* Kustomisasi Paradise: kartu asli langsung digambar, hanya angkanya yang
          menunggu. Kerangka 80px terpisah lebih pendek dari kartu (85px, 104px
          kalau judulnya terlipat di tablet), jadi semua bagian di bawahnya
          turun saat data tiba. */}
      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-3" aria-busy={!userProfile}>
        {overviewCards.map((card) => (
          <Link key={card.route} href={`/${workspaceSlug}/profile/${userId}/${card.route}`}>
            <Card direction={ECardDirection.ROW} spacing={ECardSpacing.SM} className="h-full">
              <div className="hidden h-11 w-11 shrink-0 place-items-center rounded-sm bg-surface-2 sm:grid">
                <card.icon className="h-5 w-5" />
              </div>
              <div className="space-y-1">
                <p className="text-13 text-placeholder">{t(card.i18n_title)}</p>
                <p className="text-18 font-semibold">
                  {card.value ?? (
                    <span className="inline-block h-4 w-8 animate-pulse rounded-sm bg-layer-1 align-middle" />
                  )}
                </p>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
