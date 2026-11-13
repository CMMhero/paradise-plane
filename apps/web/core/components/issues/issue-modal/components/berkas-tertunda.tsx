/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: daftar berkas yang akan dilampirkan sesudah work item dibuat
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Paperclip, X } from "lucide-react";
import { useTranslation } from "@plane/i18n";

type TBerkasTertundaProps = {
  berkas: File[];
  onHapus: (file: File) => void;
};

const formatUkuran = (byte: number) =>
  byte >= 1024 * 1024 ? `${(byte / (1024 * 1024)).toFixed(1)} MB` : `${Math.max(1, Math.round(byte / 1024))} KB`;

/** Baris berkas yang menunggu dilampirkan. Kosong = tidak merender apa pun. */
export function BerkasTertunda(props: TBerkasTertundaProps) {
  const { berkas, onHapus } = props;
  const { t } = useTranslation();

  if (berkas.length === 0) return null;

  return (
    <ul className="mt-2 flex flex-wrap gap-1.5" aria-live="polite">
      {berkas.map((file) => (
        <li
          key={`${file.name}:${file.size}:${file.lastModified}`}
          className="flex max-w-full items-center gap-1.5 rounded-md bg-layer-1 py-1 pr-1 pl-2 text-12 text-secondary"
        >
          <Paperclip className="size-3.5 shrink-0" aria-hidden />
          <span className="min-w-0 truncate">{file.name}</span>
          <span className="shrink-0 text-tertiary tabular-nums">{formatUkuran(file.size)}</span>
          <button
            type="button"
            onClick={() => onHapus(file)}
            className="grid size-5 shrink-0 place-items-center rounded-sm hover:bg-layer-2 sentuh:size-9"
            aria-label={t("navigasi_lampiran_ui.dismiss")}
          >
            <X className="size-3.5" />
          </button>
        </li>
      ))}
    </ul>
  );
}
