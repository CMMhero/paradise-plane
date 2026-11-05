/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kartu pesan obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { AtSign, Phone, PhoneMissed, Users, Video } from "lucide-react";
import { Link } from "react-router";
import { useTranslation } from "@plane/i18n";
import { Button, getButtonStyling } from "@plane/propel/button";
import { cn } from "@plane/utils";
import type { TPesan } from "@/services/chat.service";
import { KartuTugas } from "./kartu-tugas";
import { warnaKartu } from "./warna";
import { URUTAN_ENTRI, bacaCatatanRilis, bacaLogPanggilan, formatDurasi } from "./muatan";
import type { TJenisEntri } from "./muatan";

/** Pesan kartu? `jenis` kosong (respons server lama) dihitung teks biasa. */
export const adalahKartu = (pesan: TPesan): boolean => !!pesan.jenis && pesan.jenis !== "teks";

const GAYA_ENTRI: Record<TJenisEntri, string> = {
  Added: "bg-success-subtle text-success-primary",
  Changed: "bg-accent-subtle text-accent-primary",
  Fixed: "bg-warning-subtle text-warning-primary",
};

const KUNCI_ENTRI: Record<TJenisEntri, string> = {
  Added: "chatkartu_ui.type_added",
  Changed: "chatkartu_ui.type_changed",
  Fixed: "chatkartu_ui.type_fixed",
};

function KartuChangelog({ pesan }: { pesan: TPesan }) {
  const { t } = useTranslation();
  const catatan = bacaCatatanRilis(pesan.muatan);
  // Dikelompokkan per jenis supaya "apa yang baru" terbaca dulu, apa pun
  // urutan penulisannya di berkas catatan rilis.
  const urut = URUTAN_ENTRI.flatMap((jenis) => catatan.entri.filter((e) => e.type === jenis));
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-baseline justify-between gap-3 border-b border-subtle pb-1.5">
        <p className="text-13 font-semibold text-primary">{t("chatkartu_ui.release", { version: catatan.versi })}</p>
        {catatan.tanggal ? <p className="shrink-0 text-12 text-tertiary">{catatan.tanggal}</p> : null}
      </div>
      <ul className="flex flex-col gap-1.5">
        {urut.map((e) => (
          <li key={`${e.type}-${e.text}`} className="flex items-start gap-2 text-13 text-secondary">
            <span
              className={`mt-px w-16 shrink-0 rounded-control px-1.5 py-px text-center text-11 font-medium ${GAYA_ENTRI[e.type]}`}
            >
              {t(KUNCI_ENTRI[e.type])}
            </span>
            <span className="min-w-0 [overflow-wrap:anywhere]">{e.text}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

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

const teks = (v: unknown) => (typeof v === "string" ? v : "");

/** Sebutan di kanal obrolan (`muatan.obrolan`), bukan di komentar work item. */
const bacaSebutObrolan = (muatan: unknown) => {
  const m = (muatan && typeof muatan === "object" ? muatan : {}) as Record<string, unknown>;
  const o = (m.obrolan && typeof m.obrolan === "object" ? m.obrolan : null) as Record<string, unknown> | null;
  const detail = (m.detail && typeof m.detail === "object" ? m.detail : {}) as Record<string, unknown>;
  if (!o || !teks(o.ruang_id)) return null;
  return {
    ruangId: teks(o.ruang_id),
    nama: teks(o.nama),
    aktor: teks(m.aktor),
    slug: teks(m.workspace_slug),
    cuplikan: teks(detail.komentar),
  };
};

function KartuSebutObrolan({
  sebut,
  namaOrang,
}: {
  sebut: NonNullable<ReturnType<typeof bacaSebutObrolan>>;
  namaOrang: (id: string) => string;
}) {
  const { t } = useTranslation();
  const pelaku = sebut.aktor ? namaOrang(sebut.aktor) : t("chatkartu_ui.someone");
  return (
    <div className="flex w-72 max-w-full flex-col gap-2">
      <p className="flex items-center gap-1.5 text-12 text-secondary">
        <AtSign className="size-3.5 shrink-0 text-accent-primary" />
        {t("chatkartu_ui.mentioned_in", { name: pelaku, channel: sebut.nama })}
      </p>
      {sebut.cuplikan ? (
        <p className="line-clamp-3 rounded-control border border-subtle bg-layer-2 px-2.5 py-2 text-13 [overflow-wrap:anywhere] text-primary">
          {sebut.cuplikan}
        </p>
      ) : null}
      <div>
        <Link to={`/${sebut.slug}/chat/?ruang=${sebut.ruangId}`} className={getButtonStyling("secondary", "base")}>
          {t("chatkartu_ui.open_chat")}
        </Link>
      </div>
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
};

/** Satu kartu, dipilih dari `pesan.jenis`. Jenis yang belum dikenal peramban
 * ini jatuh ke `isi` biasa, jadi server boleh menambah jenis lebih dulu. */
export function KartuPesan({ pesan, namaOrang, onTelepon, terang = false }: Props) {
  switch (pesan.jenis) {
    case "changelog":
      return <KartuChangelog pesan={pesan} />;
    case "panggilan":
      return <KartuPanggilan pesan={pesan} namaOrang={namaOrang} onTelepon={onTelepon} terang={terang} />;
    case "mention": {
      const sebut = bacaSebutObrolan(pesan.muatan);
      if (sebut) return <KartuSebutObrolan sebut={sebut} namaOrang={namaOrang} />;
      return <KartuTugas pesan={pesan} namaOrang={namaOrang} terang={terang} />;
    }
    case "tugas":
    case "project":
    case "persetujuan":
    case "komentar":
    case "pembaruan":
      return <KartuTugas pesan={pesan} namaOrang={namaOrang} terang={terang} />;
    default:
      return <p className={cn("text-13 whitespace-pre-wrap", warnaKartu(terang).utama)}>{pesan.isi}</p>;
  }
}
