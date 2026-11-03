/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: penjaga pemberitahuan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Bell, X } from "lucide-react";
import { useNavigate } from "react-router";
import useSWR from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
// hooks
import { useMember } from "@/hooks/store/use-member";
import { useWorkspaceNotifications } from "@/hooks/store/notifications";
import useLocalStorage from "@/hooks/use-local-storage";
import { useParadiseModules } from "@/hooks/use-paradise-module";
import { useSuaraNotifikasi } from "@/hooks/use-suara-notifikasi";
// services
import { ChatService, KUNCI_BELUM_DIBACA } from "@/services/chat.service";
import { WorkspaceNotificationService } from "@/services/workspace-notification.service";
// local imports
import { KUNCI_SPANDUK, izinPeramban, tampilkanNotifPeramban } from "./peramban";
import { TumpukanPopup, type TPopup } from "./popup";
import { ringkasNotifikasi, ringkasPercakapan } from "./teks";

const chatService = new ChatService();
const notifService = new WorkspaceNotificationService();

/** SATU-SATUNYA jam di aplikasi untuk kedua hitungan ini. Lencana di sidebar
 * memakai kunci SWR yang persis sama dan sengaja TIDAK punya `refreshInterval`
 * sendiri, jadi putaran ini yang menyegarkan keduanya. Dua jam untuk satu kunci
 * cuma menggandakan permintaan tanpa menambah kabar apa pun.
 *
 * 15 detik, bukan 30: kartu pemberitahuan yang datang setengah menit sesudah
 * pesannya tidak terasa sebagai pemberitahuan, terasa sebagai laporan. Yang
 * ditarik cuma dua angka. */
const SELANG = 15000;

const KUNCI_JUMLAH_NOTIF = "WORKSPACE_UNREAD_NOTIFICATION_COUNT";

/** Sebanyak ini kartu boleh menumpuk sekaligus. Lebih dari itu bukan lagi
 * pemberitahuan melainkan dinding. Yang tergeser tidak hilang: angkanya tetap di
 * lencana dan isinya tetap di panel Pemberitahuan. */
const MAKS_KARTU = 3;

type TCalon = Omit<TPopup, "id">;

/**
 * Mengintai dua hitungan murah, lalu mengambil isinya hanya saat naik.
 *
 * Kenapa mengintai dan bukan WebSocket: sambungan langsung yang sudah ada hanya
 * hidup di halaman Obrolan dan hanya untuk satu ruang, sementara pemberitahuan
 * pekerjaan lahir di Celery dan tidak pernah lewat sana sama sekali. Membuat
 * satu saluran langsung untuk seluruh aplikasi adalah pekerjaan yang jauh lebih
 * besar daripada yang diminta, dan hitungan ini memang sudah ditarik lencana:
 * kuncinya sama, jadi SWR menggabungkannya jadi satu permintaan.
 *
 * Yang mahal (isi percakapan, daftar pemberitahuan) baru diambil saat angkanya
 * NAIK. Dalam keadaan tenang, penjaga ini tidak menambah satu pun permintaan.
 */
export function PenjagaNotifikasi({ workspaceSlug }: { workspaceSlug: string }) {
  // Lewat ref: efek polling tidak perlu dijalankan ulang tiap bahasa berganti.
  const { t } = useTranslation();
  const tRef = useRef(t);
  // oxlint-disable-next-line react-hooks/refs -- latest-value ref so the polling effect need not restart on language change
  tRef.current = t;
  const navigate = useNavigate();
  const { bunyikan } = useSuaraNotifikasi();
  const { getUnreadNotificationsCount } = useWorkspaceNotifications();
  // Kustomisasi Paradise: modul Chat/Inbox yang dimatikan di God Mode tidak dipantau,
  // jadi tak ada pop-up atau bunyi yang menautkan ke halaman yang tersembunyi.
  const { isModuleEnabled } = useParadiseModules();
  const pantauObrolan = !!workspaceSlug && isModuleEnabled("chat");
  const pantauNotif = !!workspaceSlug && isModuleEnabled("inbox");
  const {
    workspace: { getWorkspaceMemberDetails },
  } = useMember();

  const [antrean, setAntrean] = useState<TPopup[]>([]);
  // Penomoran sendiri, bukan cap waktu atau acak: dua pemberitahuan yang tiba di
  // milidetik yang sama akan bertabrakan kuncinya, dan React membuang salah satu
  // kartunya tanpa bilang apa-apa.
  const nomor = useRef(0);

  const tutup = useCallback((id: string) => setAntrean((lama) => lama.filter((p) => p.id !== id)), []);

  /**
   * Memberi tahu lewat DUA jalur: kartu peramban (sistem operasi) dan kartu di
   * dalam aplikasi.
   *
   * Permintaan user 3 Nov 2026: pemberitahuan obrolan & inbox JUGA lewat
   * peramban. Dulu kartu peramban hanya untuk tab tersembunyi, sehingga orang
   * yang membuka Paradise di belakang aplikasi lain (tab "visible", jendela
   * tidak fokus) tidak mendapat apa-apa di luar bunyi. Sekarang kartu peramban
   * selalu dikirim kalau diizinkan dan saklarnya menyala (Chat atau panel
   * Pemberitahuan > tombol suara > Browser notifications).
   *
   * Kartu dalam aplikasi tetap muncul saat tab terlihat. Saat tab tersembunyi
   * ia dilewati kalau kartu peramban berhasil (tujuh detiknya habis sebelum
   * orangnya kembali), tapi TETAP dipakai sebagai cadangan kalau peramban
   * menolak, mis. Chrome Android yang melempar untuk `new Notification()`.
   */
  const tampilkan = useCallback(
    (calon: TCalon, penanda: string) => {
      bunyikan("pesan");

      const lewatPeramban = tampilkanNotifPeramban({
        judul: calon.judul,
        isi: calon.isi,
        tag: penanda,
        onKlik: () => navigate(calon.tautan),
      });
      if (lewatPeramban && document.visibilityState !== "visible") return;

      nomor.current += 1;
      const baru: TPopup = { ...calon, id: `popup-${nomor.current}` };
      setAntrean((lama) => [...lama, baru].slice(-MAKS_KARTU));
    },
    [bunyikan, navigate]
  );

  const { data: statusObrolan } = useSWR(
    pantauObrolan ? KUNCI_BELUM_DIBACA : null,
    pantauObrolan ? () => chatService.getStatus(workspaceSlug) : null,
    { refreshInterval: SELANG }
  );

  const { data: statusNotif } = useSWR(
    pantauNotif ? KUNCI_JUMLAH_NOTIF : null,
    pantauNotif ? () => getUnreadNotificationsCount(workspaceSlug) : null,
    { refreshInterval: SELANG }
  );

  const jumlahObrolan = statusObrolan?.jumlah ?? null;
  // Diambil dari jawaban SWR, BUKAN dari store MobX. Store berangkat dari nol,
  // dan nol yang berarti "belum pernah diambil" terlihat persis sama dengan nol
  // yang berarti "memang tidak ada". Bedanya baru terasa saat orang membuka
  // aplikasi dengan 12 pemberitahuan lama: dari store, angka 0 -> 12 terbaca
  // sebagai dua belas hal baru dan langsung berbunyi.
  const jumlahNotif = statusNotif?.total_unread_notifications_count ?? null;

  // Muatan PERTAMA tidak pernah berbunyi. Tanpa penjaga ini, membuka aplikasi
  // dengan tumpukan lama yang belum dibaca langsung disambut bunyi dan kartu,
  // padahal tidak ada yang baru saja terjadi.
  const obrolanSebelumnya = useRef<number | null>(null);
  const notifSebelumnya = useRef<number | null>(null);

  useEffect(() => {
    if (jumlahObrolan === null) return;
    const sebelumnya = obrolanSebelumnya.current;
    obrolanSebelumnya.current = jumlahObrolan;
    if (sebelumnya === null || jumlahObrolan <= sebelumnya) return;

    let dibatalkan = false;
    void (async () => {
      try {
        const baris = await chatService.getPercakapan(workspaceSlug);
        if (dibatalkan) return;
        const ringkas = ringkasPercakapan(
          baris,
          (id) => getWorkspaceMemberDetails(id)?.member?.display_name,
          tRef.current
        );
        if (!ringkas) return;

        const pengirim = ringkas.lawanBicara ? getWorkspaceMemberDetails(ringkas.lawanBicara)?.member : undefined;
        tampilkan(
          {
            jenis: ringkas.lawanBicara ? "pesan" : "kanal",
            judul: ringkas.judul,
            isi: ringkas.isi,
            namaOrang: pengirim?.display_name,
            avatarUrl: pengirim?.avatar_url,
            tautan: ringkas.lawanBicara
              ? `/${workspaceSlug}/chat/?dengan=${ringkas.lawanBicara}`
              : `/${workspaceSlug}/chat/?ruang=${ringkas.ruangId}`,
          },
          `obrolan-${ringkas.ruangId}`
        );
      } catch {
        // Ditelan dengan sengaja. Angkanya sudah naik dan lencana sudah
        // memberitahukannya; gagal mengambil ISI pesan bukan alasan untuk
        // melemparkan galat ke muka orang yang cuma sedang membuka halaman lain.
      }
    })();
    return () => {
      dibatalkan = true;
    };
  }, [jumlahObrolan, workspaceSlug, getWorkspaceMemberDetails, tampilkan]);

  useEffect(() => {
    if (jumlahNotif === null) return;
    const sebelumnya = notifSebelumnya.current;
    notifSebelumnya.current = jumlahNotif;
    if (sebelumnya === null || jumlahNotif <= sebelumnya) return;

    let dibatalkan = false;
    void (async () => {
      try {
        const halaman = await notifService.fetchNotifications(workspaceSlug, {
          read: false,
          archived: false,
          snoozed: false,
          // Beberapa, bukan satu: baris DM (entity "chat") tidak menaikkan hitungan ini
          // dan sudah diberitahukan pengintai obrolan, jadi dilewati di sini.
          per_page: 5,
        });
        if (dibatalkan) return;
        const terbaru = halaman?.results?.find((n) => n.entity_name !== "chat");
        if (!terbaru) return;

        const ringkas = ringkasNotifikasi(terbaru, tRef.current);
        const pemicu = terbaru.triggered_by_details;
        tampilkan(
          {
            jenis: "tugas",
            judul: ringkas.judul,
            isi: ringkas.isi,
            namaOrang: pemicu?.is_bot ? pemicu?.first_name : pemicu?.display_name,
            avatarUrl: pemicu?.avatar_url,
            tautan: `/${workspaceSlug}/notifications`,
          },
          `notifikasi-${terbaru.entity_identifier ?? terbaru.id}`
        );
      } catch {
        // Lihat alasan yang sama di pengintai obrolan di atas.
      }
    })();
    return () => {
      dibatalkan = true;
    };
  }, [jumlahNotif, workspaceSlug, tampilkan]);

  return (
    <>
      <TumpukanPopup daftar={antrean} onTutup={tutup} onBuka={navigate} />
      <SpandukIzin />
    </>
  );
}

/**
 * Menawarkan izin pemberitahuan sistem, sekali, dengan cara yang bisa ditolak.
 *
 * `Notification.requestPermission()` HARUS dipanggil dari sentuhan pengguna,
 * bukan dari useEffect: Safari menolaknya diam-diam, dan Chrome memberi hukuman
 * pada situs yang meminta izin begitu halaman terbuka. Karena itu ada tombol,
 * dan bukan permintaan otomatis.
 *
 * Duduk di kiri bawah, menjauh dari dua sudut yang sudah terpakai: kartu
 * pemberitahuan di kanan atas, toast bawaan aplikasi di kanan bawah.
 */
function SpandukIzin() {
  const { t } = useTranslation();
  const { storedValue: ditutup, setValue: setDitutup } = useLocalStorage<boolean>(KUNCI_SPANDUK, false);
  const [izin, setIzin] = useState<ReturnType<typeof izinPeramban>>("tidak-didukung");

  useEffect(() => {
    // oxlint-disable-next-line react-hooks/set-state-in-effect -- reads browser-only Notification API after mount (SSR-safe)
    setIzin(izinPeramban());
  }, []);

  if (ditutup || izin !== "default") return null;

  return (
    <div className="fixed bottom-4 left-4 z-[60] w-80 rounded-popover border border-subtle bg-surface-1 p-4 shadow-overlay-200">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-control bg-accent-primary/10">
          <Bell className="size-4 text-accent-primary" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-13 font-medium text-primary">{t("notification_ui.enable_title")}</p>
          <p className="mt-1 text-12 text-tertiary">{t("notification_ui.enable_message")}</p>
          <div className="mt-3 flex items-center gap-2">
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                void Notification.requestPermission().then(setIzin);
              }}
            >
              {t("notification_ui.enable")}
            </Button>
            <Button variant="secondary" size="sm" onClick={() => setDitutup(true)}>
              {t("notification_ui.later")}
            </Button>
          </div>
        </div>
        <button
          type="button"
          aria-label={t("close")}
          className="text-tertiary hover:text-primary"
          onClick={() => setDitutup(true)}
        >
          <X className="size-4" />
        </button>
      </div>
    </div>
  );
}
