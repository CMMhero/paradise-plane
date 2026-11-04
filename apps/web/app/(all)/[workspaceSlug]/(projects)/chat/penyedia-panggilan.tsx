/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: panggilan di lapisan workspace
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useRef } from "react";
import type { ReactNode } from "react";
import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { getFileURL } from "@plane/utils";
import { tampilkanNotifPeramban } from "@/components/notifikasi/peramban";
import { useMember } from "@/hooks/store/use-member";
import { useUser } from "@/hooks/store/user";
import { useKehadiranTersambung } from "@/hooks/use-kehadiran";
import { useSuaraNotifikasi } from "@/hooks/use-suara-notifikasi";
import { usePanggilan, type TKabarPanggilan, type TPanggilan } from "./panggilan";
import { PanggilanLayar } from "./panggilan-layar";
import { PanggilanMasuk } from "./panggilan-masuk";

type TNilai = TPanggilan & {
  /** Jalur sinyal DM (soket kehadiran) sedang terbuka. */
  siap: boolean;
};

const KonteksPanggilan = createContext<TNilai | null>(null);

/** Panggilan milik tab ini. Hanya bisa dipakai di bawah `PenyediaPanggilan`. */
export function usePanggilanWorkspace(): TNilai {
  const nilai = useContext(KonteksPanggilan);
  if (!nilai) throw new Error("usePanggilanWorkspace dipakai di luar PenyediaPanggilan");
  return nilai;
}

/** Tag kartu peramban yang SAMA untuk "masuk" dan "terlewat": kartu terlewat
 * menggantikan kartu masuk di Pusat Tindakan, bukan menumpuk di bawahnya. */
const TAG_NOTIF = "panggilan-masuk";

/**
 * Dipasang SEKALI di lapisan workspace, membungkus seluruh halaman.
 *
 * Panggilan dulu hidup di halaman Obrolan dan ikut mati saat orangnya pindah
 * halaman. Di sini ia bertahan selama tab berada di workspace ini, dan
 * panggilan masuk tampil (kartu, nada dering, kartu peramban) di halaman mana
 * pun. Halaman Obrolan tinggal memakai konteksnya untuk tombol telepon dan
 * ajakan konferensi kanal.
 */
export const PenyediaPanggilan = observer(function PenyediaPanggilan({
  workspaceSlug,
  children,
}: {
  workspaceSlug: string;
  children: ReactNode;
}) {
  const { t } = useTranslation();
  const { data: currentUser } = useUser();
  const {
    workspace: { getWorkspaceMemberDetails },
  } = useMember();
  const { mulaiDering, hentikanDering } = useSuaraNotifikasi();
  const siap = useKehadiranTersambung();

  const namaOrang = useCallback(
    (id: string | null | undefined) =>
      (id ? getWorkspaceMemberDetails(id)?.member?.display_name : undefined) ?? t("chat_ui.member"),
    [getWorkspaceMemberDetails, t]
  );
  const avatarOrang = useCallback(
    (id: string | null | undefined) =>
      (id ? getFileURL(getWorkspaceMemberDetails(id)?.member?.avatar_url ?? "") : undefined) || undefined,
    [getWorkspaceMemberDetails]
  );

  const onKabar = useCallback(
    (kabar: TKabarPanggilan) => {
      const nama = namaOrang(kabar.lawan);
      const teks = {
        terlewat: [t("chat_ui.call_ring.missed_title"), t("chat_ui.call_ring.missed_body", { name: nama })],
        tak_terjawab: [t("chat_ui.call_ring.no_answer_title"), t("chat_ui.call_ring.no_answer_body", { name: nama })],
        ditolak: [t("chat_ui.call_ring.declined_title"), t("chat_ui.call_ring.declined_body", { name: nama })],
        sibuk: [t("chat_ui.call_ring.busy_title"), t("chat_ui.call_ring.busy_body", { name: nama })],
      }[kabar.jenis];
      setToast({
        type: kabar.jenis === "sibuk" ? TOAST_TYPE.WARNING : TOAST_TYPE.INFO,
        title: teks[0],
        message: teks[1],
      });
      // Panggilan terlewat saat tabnya di belakang: toast tidak akan terlihat,
      // jadi kartu peramban menggantikan kartu "panggilan masuk" yang sudah basi.
      if (kabar.jenis === "terlewat" && document.visibilityState !== "visible")
        tampilkanNotifPeramban({ judul: teks[0], isi: teks[1], tag: TAG_NOTIF });
    },
    [namaOrang, t]
  );

  const panggilan = usePanggilan({
    slug: workspaceSlug,
    saya: currentUser?.id,
    onGagal: (pesanGalat) => setToast({ type: TOAST_TYPE.ERROR, title: t("chat_ui.call_failed"), message: pesanGalat }),
    onKabar,
  });
  const { status, lawan, pakaiVideo, konferensi } = panggilan;

  // Nada dering selama berdering, berhenti begitu status berubah apa pun
  // sebabnya (angkat, tolak, dibatalkan, jam habis, tab lain mengangkat).
  // Teks kartu peramban dibaca lewat ref supaya ganti bahasa atau data anggota
  // yang termuat belakangan tidak memunculkan kartu kedua.
  // Efek penyalin dideklarasikan SEBELUM efek dering, jadi pada commit yang
  // sama ia jalan lebih dulu dan teksnya sudah terbaru.
  const teksDeringRef = useRef({ judul: "", isi: "" });
  const judulDering = pakaiVideo ? t("chat_ui.call_ring.incoming_video") : t("chat_ui.call_ring.incoming_voice");
  const namaPenelepon = namaOrang(lawan);
  useEffect(() => {
    teksDeringRef.current = { judul: judulDering, isi: namaPenelepon };
  }, [judulDering, namaPenelepon]);
  useEffect(() => {
    if (status !== "berdering") return undefined;
    mulaiDering();
    // Kartu sistem operasi hanya kalau orangnya tidak sedang melihat tab ini;
    // kalau sedang melihat, kartu di halaman dan nada dering sudah cukup.
    if (document.visibilityState !== "visible" || !document.hasFocus())
      tampilkanNotifPeramban({ ...teksDeringRef.current, tag: TAG_NOTIF });
    return () => hentikanDering();
  }, [status, mulaiDering, hentikanDering]);

  const nilai = useMemo<TNilai>(() => ({ ...panggilan, siap }), [panggilan, siap]);

  return (
    <KonteksPanggilan.Provider value={nilai}>
      {children}
      {status === "berdering" ? (
        <PanggilanMasuk
          nama={namaOrang(lawan)}
          avatar={avatarOrang(lawan)}
          video={pakaiVideo}
          onAngkat={(video) => void panggilan.angkat(video)}
          onTolak={panggilan.tutup}
        />
      ) : (
        <PanggilanLayar
          status={status}
          koneksi={panggilan.koneksi}
          judul={konferensi ? konferensi.nama : namaOrang(lawan)}
          avatarJudul={konferensi ? undefined : avatarOrang(lawan)}
          cariAvatar={avatarOrang}
          pakaiVideo={pakaiVideo}
          mikMati={panggilan.mikMati}
          kameraMati={panggilan.kameraMati}
          streamLokal={panggilan.streamLokal}
          pesertaJauh={panggilan.pesertaJauh}
          byteMasuk={panggilan.byteMasuk}
          onAngkat={() => void panggilan.angkat(pakaiVideo)}
          onTutup={panggilan.tutup}
          onSetelMik={panggilan.setelMik}
          onSetelKamera={panggilan.setelKamera}
        />
      )}
    </KonteksPanggilan.Provider>
  );
});
