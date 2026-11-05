/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kartu aktivitas work item di obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { Link } from "react-router";
import { useTranslation } from "@plane/i18n";
import { Button, getButtonStyling } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Avatar, TextArea } from "@plane/ui";
import { cn, getFileURL, renderFormattedDate } from "@plane/utils";
import { useMember } from "@/hooks/store/use-member";
import { PersetujuanService } from "@/services/persetujuan.service";
import type { TPesan } from "@/services/chat.service";
import { bacaKartuTugas } from "./muatan";
import type { TKartuTugas, TStatusPersetujuan } from "./muatan";
import { warnaKartu } from "./warna";

const persetujuanService = new PersetujuanService();

/** Kunci judul kartu per jenis. `{name}` = pelaku. */
const judulKartu = (jenis: TPesan["jenis"], kartu: TKartuTugas): string => {
  if (jenis === "persetujuan") {
    if (kartu.detail.verb === "approved") return "chatkartu_ui.approval_approved";
    if (kartu.detail.verb === "rejected") return "chatkartu_ui.approval_rejected";
    return "chatkartu_ui.approval_submitted";
  }
  const peta: Record<string, string> = {
    tugas: "chatkartu_ui.assigned",
    project: "chatkartu_ui.added_to_project",
    mention: "chatkartu_ui.mentioned",
    komentar: "chatkartu_ui.commented",
    pembaruan: "chatkartu_ui.updated",
  };
  return peta[jenis ?? ""] ?? "chatkartu_ui.updated";
};

const ChipStatus = ({ status }: { status: TStatusPersetujuan }) => {
  const { t } = useTranslation();
  if (status === "menunggu") return null;
  const setuju = status === "disetujui";
  return (
    <span
      className={`rounded-control px-1.5 py-px text-11 font-medium ${
        setuju ? "bg-success-subtle text-success-primary" : "bg-danger-subtle text-danger-primary"
      }`}
    >
      {t(setuju ? "chatkartu_ui.approved_label" : "chatkartu_ui.rejected_label")}
    </span>
  );
};

type Props = {
  pesan: TPesan;
  namaOrang: (id: string) => string;
  /** Kartu yang saya picu (saya pengirimnya): warna gelembung keluar, tanpa tombol keputusan. */
  terang?: boolean;
};

export const KartuTugas = observer(function KartuTugas({ pesan, namaOrang, terang = false }: Props) {
  const { t } = useTranslation();
  const {
    workspace: { getWorkspaceMemberDetails },
  } = useMember();
  const kartu = bacaKartuTugas(pesan.muatan);
  const warna = warnaKartu(terang);
  // Status lokal sesudah tombol ditekan; server juga memperbarui kartu ini
  // untuk semua penyetuju lain (tandai_persetujuan_diputuskan).
  const [keputusan, setKeputusan] = useState<TStatusPersetujuan | null>(null);
  const [menolak, setMenolak] = useState(false);
  const [alasan, setAlasan] = useState("");
  const [sibuk, setSibuk] = useState(false);

  const { tugas, project, persetujuan } = kartu;
  const tautan = tugas
    ? `/${kartu.slug}/projects/${project.id}/issues/${tugas.id}`
    : project.id
      ? `/${kartu.slug}/projects/${project.id}/issues`
      : "";
  const status = keputusan ?? persetujuan?.status ?? "menunggu";
  // Tombol hanya di kartu permintaan yang masih menunggu. Kartu ini memang
  // hanya dikirim ke calon penyetuju, dan server memeriksa ulang kewenangannya
  // (403 kalau bukan atasan pembuat), jadi tombol di sini bukan gerbang izin.
  const bolehPutuskan =
    !terang &&
    pesan.jenis === "persetujuan" &&
    kartu.detail.verb === "submitted" &&
    !!persetujuan &&
    status === "menunggu";

  const putuskan = async (aksi: "setujui" | "tolak") => {
    if (!persetujuan) return;
    setSibuk(true);
    try {
      await persetujuanService.putuskan(kartu.slug, persetujuan.projectId, persetujuan.id, aksi, alasan.trim());
      setKeputusan(aksi === "setujui" ? "disetujui" : "ditolak");
      setMenolak(false);
    } catch (e) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("chatkartu_ui.action_failed"),
        message: (e as { error?: string })?.error,
      });
    } finally {
      setSibuk(false);
    }
  };

  const pelaku = kartu.aktor ? namaOrang(kartu.aktor) : t("chatkartu_ui.someone");

  return (
    <div className="flex w-72 max-w-full flex-col gap-2">
      <p className={cn("text-12", warna.sekunder)}>{t(judulKartu(pesan.jenis, kartu), { name: pelaku })}</p>

      <div className={cn("flex flex-col gap-1 rounded-control border px-2.5 py-2", warna.kotak)}>
        {tugas ? (
          <>
            <p className={cn("text-12", warna.redup)}>
              {tugas.nomor}
              {project.nama ? ` · ${project.nama}` : ""}
            </p>
            <p className={cn("line-clamp-2 text-13 font-medium [overflow-wrap:anywhere]", warna.utama)}>
              {tugas.judul}
            </p>
            <div className={cn("flex flex-wrap items-center gap-1.5 text-12", warna.redup)}>
              {tugas.state ? (
                <span className={cn("rounded-control px-1.5 py-px", warna.chip)}>{tugas.state}</span>
              ) : null}
              {tugas.tenggat ? (
                <span>{t("chatkartu_ui.due", { date: renderFormattedDate(tugas.tenggat) })}</span>
              ) : null}
              <ChipStatus status={status} />
              {tugas.assignees.length > 0 ? (
                <span className="ml-auto flex -space-x-1.5">
                  {tugas.assignees.map((id) => {
                    const anggota = getWorkspaceMemberDetails(id)?.member;
                    return (
                      <Avatar
                        key={id}
                        name={anggota?.display_name}
                        src={getFileURL(anggota?.avatar_url ?? "")}
                        size={20}
                        shape="circle"
                      />
                    );
                  })}
                </span>
              ) : null}
            </div>
          </>
        ) : (
          <p className={cn("text-13 font-medium", warna.utama)}>{project.nama}</p>
        )}
        {kartu.detail.komentar ? (
          <p className={cn("line-clamp-3 border-l-2 pl-2 text-12", warna.garis, warna.sekunder)}>
            {kartu.detail.komentar}
          </p>
        ) : null}
      </div>

      {menolak ? (
        <div className="flex flex-col gap-1.5">
          {/* TextArea mengabaikan `rows` (tingginya mengikuti isi), jadi tinggi
              awal dua baris dipatok lewat min-height (2 baris + py-1.5 + border). */}
          <TextArea
            value={alasan}
            onChange={(e) => setAlasan(e.target.value)}
            placeholder={t("chatkartu_ui.reject_reason")}
            rows={2}
            className="min-h-[calc(2lh+0.75rem+2px)] resize-none border border-subtle px-2 py-1.5 text-13 text-primary focus:border-accent-strong"
          />
          <div className="flex justify-end gap-1.5">
            <Button variant="ghost" size="base" onClick={() => setMenolak(false)} disabled={sibuk}>
              {t("chatkartu_ui.cancel")}
            </Button>
            <Button
              variant="error-fill"
              size="base"
              onClick={() => void putuskan("tolak")}
              disabled={sibuk || !alasan.trim()}
            >
              {t("chatkartu_ui.reject")}
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex flex-wrap gap-1.5">
          {tautan ? (
            <Link to={tautan} className={getButtonStyling("secondary", "base")}>
              {t("chatkartu_ui.open")}
            </Link>
          ) : null}
          {bolehPutuskan ? (
            <>
              <Button variant="primary" size="base" onClick={() => void putuskan("setujui")} disabled={sibuk}>
                {t("chatkartu_ui.approve")}
              </Button>
              <Button variant="error-outline" size="base" onClick={() => setMenolak(true)} disabled={sibuk}>
                {t("chatkartu_ui.reject")}
              </Button>
            </>
          ) : null}
        </div>
      )}
    </div>
  );
});
