/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kartu pesan obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Phone, PhoneMissed, Users, Video } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { cn } from "@plane/utils";
import type { TPesan } from "@/services/chat.service";
import { KartuTugas } from "./kartu-tugas";
import { warnaKartu } from "./warna";
import { bacaLogPanggilan, formatDurasi } from "./muatan";

/** Pesan kartu? `jenis` kosong (respons server lama) dihitung teks biasa. */
export const adalahKartu = (pesan: TPesan): boolean => !!pesan.jenis && pesan.jenis !== "teks";

function KartuPanggilan({
  pesan,
  namaOrang,
  onTelepon,
  terang,
}: {
  pesan: TPesan;
  namaOrang: (id: string) => string;
  onTelepon?: (video: boolean) => void;
  terang: boolean;
}) {
  const { t } = useTranslation();
  const warna = warnaKartu(terang);
  const log = bacaLogPanggilan(pesan.muatan);
  const terlewat = log.status === "tak_terjawab";
  const Ikon = terlewat ? PhoneMissed : log.konferensi ? Users : log.video ? Video : Phone;
  const judul = terlewat
    ? t("chatkartu_ui.missed_call")
    : log.konferensi
      ? t("chatkartu_ui.group_call")
      : log.video
        ? t("chatkartu_ui.video_call")
        : t("chatkartu_ui.voice_call");
  const keterangan =
    log.status === "berlangsung"
      ? t("chatkartu_ui.call_ongoing")
      : log.status === "selesai" && log.durasi !== null
        ? formatDurasi(log.durasi)
        : "";

  return (
    <div className="flex items-center gap-3">
      <span
        className={cn(
          "grid size-8 shrink-0 place-items-center rounded-full",
          terlewat ? "bg-danger-subtle text-danger-primary" : warna.ikon
        )}
      >
        <Ikon className="size-4" />
      </span>
      <div className="min-w-0 flex-1">
        <p className={cn("text-13 font-medium", warna.utama)}>{judul}</p>
        <p className={cn("truncate text-12", warna.redup)}>
          {[log.oleh ? t("chatkartu_ui.started_by", { name: namaOrang(log.oleh) }) : "", keterangan]
            .filter(Boolean)
            .join(" · ")}
        </p>
      </div>
      {onTelepon && log.status !== "berlangsung" ? (
        <Button variant="secondary" size="base" onClick={() => onTelepon(log.video)}>
          {t("chatkartu_ui.call_back")}
        </Button>
      ) : null}
    </div>
  );
}

type Props = {
  pesan: TPesan;
  namaOrang: (id: string) => string;
  /** Telepon balik di percakapan yang sedang dibuka. Kosong = tombol disembunyikan. */
  onTelepon?: (video: boolean) => void;
  /** Kartu yang saya picu: digambar di atas warna gelembung keluar saya. */
  terang?: boolean;
  /** Pembaca kartu; menentukan kalimat penugasan. */
  sayaId?: string;
};

/** Satu kartu, dipilih dari `pesan.jenis`. Jenis yang belum dikenal peramban
 * ini jatuh ke `isi` biasa, jadi server boleh menambah jenis lebih dulu. */
export function KartuPesan({ pesan, namaOrang, onTelepon, terang = false, sayaId }: Props) {
  switch (pesan.jenis) {
    case "panggilan":
      return <KartuPanggilan pesan={pesan} namaOrang={namaOrang} onTelepon={onTelepon} terang={terang} />;
    case "mention":
    case "tugas":
    case "persetujuan":
    case "komentar":
    case "pembaruan":
      return <KartuTugas pesan={pesan} namaOrang={namaOrang} terang={terang} sayaId={sayaId} />;
    default:
      return <p className={cn("text-13 whitespace-pre-wrap", warnaKartu(terang).utama)}>{pesan.isi}</p>;
  }
}
