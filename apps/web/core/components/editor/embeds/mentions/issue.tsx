/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Lock } from "lucide-react";
import { Link } from "react-router";
// plane imports
import { useTranslation } from "@plane/i18n";
import { HoverCard } from "@plane/propel/popover";
// components
import { TugasPreviewCard } from "@/components/rujukan-preview";
// local imports
import { useInfoTugas } from "./use-info-rujukan";

type Props = {
  id: string;
};

// Paradise (KEP-91): chip work item "PRJ-12 judul". Tanpa akses: kunci + pesan, tanpa nomor maupun judul.
export function EditorIssueMention({ id }: Props) {
  const { t } = useTranslation();
  const { slug, info, isLoading } = useInfoTugas(id);

  if (isLoading || !info) {
    return <span className="not-prose inline rounded-sm bg-layer-1 px-1 py-0.5 text-tertiary">#…</span>;
  }

  if (!info.boleh) {
    return (
      <HoverCard content={<TugasPreviewCard id={id} />}>
        <span className="not-prose inline-flex items-center gap-0.5 rounded-sm bg-layer-1 px-1 py-0.5 text-tertiary no-underline">
          <Lock className="size-3" />
          {t("rujukan_ui.work_item_no_access")}
        </span>
      </HoverCard>
    );
  }

  return (
    <HoverCard content={<TugasPreviewCard id={id} />}>
      <Link
        to={`/${slug}/browse/${info.nomor}/`}
        className="not-prose inline rounded-sm bg-accent-subtle-active px-1 py-0.5 text-accent-primary no-underline"
      >
        <span className="font-medium hover:underline">{info.nomor}</span>
        {info.judul && <span className="ml-1 hover:underline">{info.judul}</span>}
      </Link>
    </HoverCard>
  );
}
