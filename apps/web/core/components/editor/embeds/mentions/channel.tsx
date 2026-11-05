/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Hash, Lock } from "lucide-react";
import { Link } from "react-router";
// plane imports
import { useTranslation } from "@plane/i18n";
import { HoverCard } from "@plane/propel/popover";
// components
import { KanalPreviewCard } from "@/components/rujukan-preview";
// local imports
import { useInfoKanal } from "./use-info-rujukan";

const CHIP_CLASS = "not-prose inline rounded-sm bg-accent-subtle-active px-1 py-0.5 text-accent-primary no-underline";

type Props = {
  id: string;
};

// Paradise (KEP-91): chip #kanal. Kanal privat yang tak boleh dilihat penonton tampil terkunci, tanpa nama.
export function EditorChannelMention({ id }: Props) {
  const { t } = useTranslation();
  const { slug, info, isLoading } = useInfoKanal(id);

  if (isLoading || !info) {
    return <span className="not-prose inline rounded-sm bg-layer-1 px-1 py-0.5 text-tertiary">#…</span>;
  }

  if (!info.boleh) {
    return (
      <HoverCard content={<KanalPreviewCard id={id} />}>
        <span className="not-prose inline-flex items-center gap-0.5 rounded-sm bg-layer-1 px-1 py-0.5 text-tertiary no-underline">
          <Lock className="size-3" />
          {t("rujukan_ui.private_channel")}
        </span>
      </HoverCard>
    );
  }

  return (
    <HoverCard content={<KanalPreviewCard id={id} />}>
      <Link to={`/${slug}/chat/?ruang=${id}`} className={CHIP_CLASS} aria-label={t("rujukan_ui.open_channel")}>
        <Hash className="mr-0.5 inline size-3 align-[-1px]" />
        <span className="hover:underline">{info.nama}</span>
      </Link>
    </HoverCard>
  );
}
