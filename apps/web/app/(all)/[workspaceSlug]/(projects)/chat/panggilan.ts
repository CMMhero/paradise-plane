/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: panggilan suara & video
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { ConnectionState, Room } from "livekit-client";
import { useTranslation } from "@plane/i18n";
import { dengarPanggilan, kirimSinyalPanggilan, soketKehadiranTerbuka } from "@/hooks/use-kehadiran";
import { ChatService } from "@/services/chat.service";
import { pesanGalatMedia } from "./galat-media";
import {
  akibatWaktuHabis,
  BATAS_DERING_PENELEPON_MS,
  BATAS_DERING_PENERIMA_MS,
  bacaSinyalPanggilan,
  putuskanSinyal,
  sinyalTutup,
  type TJenisSinyal,
  type TPanggilanAktif,
} from "./sinyal-panggilan";
import { statusSesudahPeristiwa } from "./tata-panggilan";

const chatService = new ChatService();

type TLivekit = typeof import("livekit-client");

/**
 * SDK LiveKit dimuat saat panggilan PERTAMA dimulai, bukan saat halaman dibuka.
 * Hook ini sekarang hidup di lapisan workspace (lihat `penyedia-panggilan.tsx`),
 * jadi impor statis berarti SETIAP halaman mengunduh SDK-nya, padahal panggilan
 * jarang terjadi.
 */
let livekitTermuat: TLivekit | null = null;
const muatLivekit = async (): Promise<TLivekit> => {
  livekitTermuat ??= await import("livekit-client");
  return livekitTermuat;
};

/** Id panggilan. `randomUUID` hanya ada di konteks aman; di origin http
 * panggilan memang tidak akan jalan (mikrofon ditiadakan peramban), tapi
 * membuat id tidak boleh jadi tempat ia meledak lebih dulu. */
const idBaru = (): string =>
  typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;

/**
 * Panggilan lewat LiveKit, bukan peer ke peer.
 *
 * KENAPA LIVEKIT
 * Versi pertama memakai RTCPeerConnection langsung. Jaringan kantor
 * mengisolasi klien satu sama lain, jadi peer ke peer memang tidak akan pernah
 * jalan. LiveKit itu SFU: kedua peramban menyambung KE SERVER. Yang ikut hilang
 * bersamanya (urutan negosiasi, antrean ICE, sambung ulang) dulu masing-masing
 * pernah jadi bug nyata.
 *
 * YANG TETAP MILIK KITA: dering. LiveKit tidak punya konsep "sedang dipanggil".
 *
 * KENAPA HIDUP DI LAPISAN WORKSPACE (4 Nov 2026)
 * Dulu hook ini hidup di halaman Obrolan dan undangannya lewat soket per ruang.
 * Akibatnya, semuanya senyap:
 * - yang ditelepon tidak berdering kecuali sedang membuka percakapan itu juga;
 * - yang mengangkat masuk ruang LiveKit milik percakapan yang SEDANG TERBUKA di
 *   layarnya, bukan ruang panggilannya;
 * - pindah halaman melepas hook dan memutus panggilan, dan lawan yang sekadar
 *   pindah percakapan (`pergi` di soket ruang) ikut menutupnya;
 * - tidak ada batas waktu dering di kedua sisi.
 * Sekarang sinyal DM lewat soket kehadiran (lihat `sinyal-panggilan.ts`), ruang
 * panggilan dibawa undangannya sendiri, dan panggilan bertahan selama tab di
 * workspace ini.
 *
 * Panggilan kanal (konferensi) tetap lewat soket ruang: ia memang hanya
 * mengajak orang yang sedang membuka kanal itu, bukan berdering.
 */

export type TStatusPanggilan = "diam" | "memanggil" | "berdering" | "menyambungkan" | "tersambung";

/** Satu lawan bicara di dalam panggilan.
 *
 * Bentuknya daftar, bukan satu objek, sejak awal. Konferensi bukan fitur
 * terpisah dari panggilan berdua: SFU memperlakukan keduanya sama, dan
 * membedakannya di sini cuma menciptakan dua jalur kode yang harus dijaga
 * sinkron. Panggilan berdua sekadar konferensi berisi satu orang. */
export type TPesertaJauh = {
  id: string;
  nama: string;
  stream: MediaStream;
  adaVideo: boolean;
  /** Kamera lawan sedang dimatikan: tampilkan avatar, bukan kotak hitam. */
  videoMati: boolean;
};

/** Kabar akhir panggilan DM yang perlu ditampilkan ke orangnya. */
export type TKabarPanggilan = {
  jenis: "terlewat" | "tak_terjawab" | "ditolak" | "sibuk";
  lawan: string;
  video: boolean;
};

/** Mengirim satu sinyal lewat soket ruang yang sedang terbuka (konferensi). */
export type TKirimSinyalRuang = (ke: string, muatan: unknown) => boolean;

type Opsi = {
  slug?: string;
  /** Id pengguna tab ini; pembeda gema dari tab saya sendiri. */
  saya?: string;
  onGagal?: (pesan: string) => void;
  onKabar?: (kabar: TKabarPanggilan) => void;
};

export function usePanggilan({ slug, saya, onGagal, onKabar }: Opsi) {
  const { t } = useTranslation();
  const [status, setStatus] = useState<TStatusPanggilan>("diam");
  const [koneksi, setKoneksi] = useState("belum mulai");
  const [lawan, setLawan] = useState<string | null>(null);
  /** Kanal yang sedang dikonferensikan, untuk judul layar. `null` = DM. */
  const [konferensi, setKonferensi] = useState<{ ruang: string; nama: string } | null>(null);
  const [pakaiVideo, setPakaiVideo] = useState(false);
  const [mikMati, setMikMati] = useState(false);
  const [kameraMati, setKameraMati] = useState(false);
  const [streamLokal, setStreamLokal] = useState<MediaStream | null>(null);
  const [pesertaJauh, setPesertaJauh] = useState<TPesertaJauh[]>([]);
  /** Ada konferensi berjalan di kanal ini yang belum kita ikuti. Dicatat
   * berikut ruangnya: ajakannya hanya relevan selama kanal itu yang dibuka. */
  const [konferensiBerjalan, setKonferensiBerjalan] = useState<{ ruang: string; video: boolean } | null>(null);
  const [byteMasuk, setByteMasuk] = useState({ audio: 0, video: 0 });

  const roomRef = useRef<Room | null>(null);
  /** Id panggilan yang sedang dipegang, DM maupun konferensi. Tiap `await`
   * memeriksanya ulang: panggilan yang ditutup selagi menyambung tidak boleh
   * hidup kembali begitu `room.connect()` selesai belakangan. */
  const idRef = useRef<string | null>(null);
  /** Panggilan DM aktif (lawan, ruang, peran). Konferensi = `null`. */
  const dmRef = useRef<TPanggilanAktif | null>(null);
  const jamRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  /** Status terbaru untuk penangan sinyal & jam, yang tidak ikut render. */
  const statusRef = useRef<TStatusPanggilan>("diam");
  /** Nilai terbaru dari render, dibaca penangan sinyal, jam, dan callback
   * LiveKit yang hidup di luar render. Lewat ref supaya callback panggilan tidak
   * dibuat ulang (dan langganan soket tidak dibongkar) tiap bahasa berganti.
   * Disalin di efek, bukan saat render: menulis ref saat render ditolak lint,
   * dan selisih satu commit tidak berarti untuk sinyal jaringan. */
  const terbaruRef = useRef({ t, onGagal, onKabar, saya, pakaiVideo });
  useEffect(() => {
    terbaruRef.current = { t, onGagal, onKabar, saya, pakaiVideo };
  });

  const ubahStatus = useCallback((next: TStatusPanggilan | ((s: TStatusPanggilan) => TStatusPanggilan)) => {
    setStatus((s) => {
      const hasil = typeof next === "function" ? next(s) : next;
      statusRef.current = hasil;
      return hasil;
    });
  }, []);

  /** Log panggilan di linimasa (kartu "Voice call 1:23" / "Missed call").
   * Ruang dicatat saat panggilan dimulai. Kedua pihak melapor; server memakai
   * log `berlangsung` terbaru di ruang itu, dan yang ditutup tanpa pernah
   * `tersambung` dicatatnya sebagai tak terjawab. Gagal melapor ditelan: log
   * yang hilang tidak boleh memutus panggilan. */
  const logRef = useRef<{ slug: string; ruang: string; tersambung: boolean } | null>(null);
  const lapor = useCallback((peristiwa: "mulai" | "tersambung" | "selesai", video = false) => {
    const log = logRef.current;
    if (!log) return;
    void chatService.logPanggilan(log.slug, log.ruang, peristiwa, video).catch(() => undefined);
  }, []);
  const mulaiLog = useCallback(
    (ruang: string, laporMulai: boolean, video: boolean) => {
      if (!slug) return;
      logRef.current = { slug, ruang, tersambung: false };
      if (laporMulai) lapor("mulai", video);
    },
    [slug, lapor]
  );

  /**
   * Akhiri panggilan di tab ini.
   *
   * `lapor: false` khusus untuk tab yang berhenti berdering karena tab LAIN
   * milik orang yang sama sudah mengangkat. Laporan "selesai" dari tab ini akan
   * menutup log sebagai tak terjawab tepat saat tab yang mengangkat sedang
   * menyambung.
   */
  const bereskan = useCallback(
    (opsi: { lapor?: boolean } = {}) => {
      if (jamRef.current) clearTimeout(jamRef.current);
      jamRef.current = null;
      if (logRef.current) {
        if (opsi.lapor !== false) lapor("selesai");
        logRef.current = null;
      }
      // `disconnect()` menghentikan track lokal, menutup sambungan, dan melepas
      // listener sekaligus. Tanpa itu lampu kamera bisa tetap menyala.
      const room = roomRef.current;
      roomRef.current = null;
      void room?.disconnect();
      idRef.current = null;
      dmRef.current = null;
      ubahStatus("diam");
      setKoneksi("belum mulai");
      setLawan(null);
      setKonferensi(null);
      setStreamLokal(null);
      setPesertaJauh([]);
      setMikMati(false);
      setKameraMati(false);
      setByteMasuk({ audio: 0, video: 0 });
    },
    [lapor, ubahStatus]
  );

  /** Kirim sinyal DM ke lawan panggilan sekarang. */
  const kirimDm = useCallback((aktif: TPanggilanAktif, jenis: TJenisSinyal, video?: boolean): boolean => {
    return kirimSinyalPanggilan({
      ke: aktif.lawan,
      ruang: aktif.ruang,
      muatan: { jenis, id: aktif.id, ...(video === undefined ? {} : { video }) },
    });
  }, []);

  /** Rakit ulang daftar peserta dari seluruh track yang sedang berlangganan.
   *
   * Stream dirakit PER ORANG, bukan satu stream gabungan: menggabungkan semua
   * track membuat suara semua orang keluar dari satu elemen dan gambarnya
   * bertumpuk, dan baru ketahuan salah begitu ada orang ketiga.
   */
  const susunPeserta = useCallback((room: Room) => {
    const daftar: TPesertaJauh[] = [];
    room.remoteParticipants.forEach((peserta) => {
      const track: MediaStreamTrack[] = [];
      let adaVideo = false;
      let videoMati = false;
      peserta.trackPublications.forEach((pub) => {
        const mst = pub.track?.mediaStreamTrack;
        if (!mst) return;
        track.push(mst);
        // `susunPeserta` hanya dipanggil dari peristiwa ruang, jadi SDK pasti sudah termuat.
        if (livekitTermuat && pub.kind === livekitTermuat.Track.Kind.Video) {
          adaVideo = true;
          videoMati = pub.isMuted;
        }
      });
      if (track.length === 0) return;
      daftar.push({
        id: peserta.identity,
        nama: peserta.name || peserta.identity,
        stream: new MediaStream(track),
        adaVideo,
        videoMati,
      });
    });
    setPesertaJauh(daftar);
  }, []);

  /** Rakit stream pratinjau sendiri dari track lokal yang sedang terbit. */
  const bangunLokal = useCallback((room: Room) => {
    const lokal: MediaStreamTrack[] = [];
    room.localParticipant.trackPublications.forEach((pub) => {
      if (pub.track?.mediaStreamTrack) lokal.push(pub.track.mediaStreamTrack);
    });
    setStreamLokal(lokal.length > 0 ? new MediaStream(lokal) : null);
  }, []);

  /** Sambung ke ruang panggilan dan mulai mengirim media.
   *
   * `ruang` selalu ruang MILIK PANGGILAN (dari undangan atau dari yang
   * menelepon), tidak pernah "percakapan yang sedang terbuka di layar". Dulu
   * yang kedua yang dipakai, sehingga yang mengangkat sambil membuka percakapan
   * lain masuk ke ruang LiveKit yang salah dan kedua orang menunggu sendirian.
   *
   * Mengembalikan `null` kalau gagal (sudah dibereskan dan dikabarkan) ATAU
   * kalau panggilannya sudah ditutup selagi menyambung (diam, tanpa galat).
   */
  const masukRuang = useCallback(
    async (ruang: string, video: boolean, id: string): Promise<Room | null> => {
      const masihIni = () => idRef.current === id;
      const gagal = (pesan: string) => {
        if (!masihIni()) return null;
        terbaruRef.current.onGagal?.(pesan);
        bereskan();
        return null;
      };
      if (!slug) return gagal(terbaruRef.current.t("chat_ui.call_error.no_room"));

      let izin: { url: string; token: string };
      try {
        izin = await chatService.getTokenPanggilan(slug, ruang);
      } catch (e) {
        return gagal((e as { error?: string })?.error ?? terbaruRef.current.t("chat_ui.call_error.cannot_start"));
      }

      let livekit: TLivekit;
      try {
        livekit = await muatLivekit();
      } catch {
        // Potongan bundel gagal diunduh (jaringan putus, atau deploy baru
        // mengganti nama berkasnya).
        return gagal(terbaruRef.current.t("chat_ui.call_error.cannot_start"));
      }
      if (!masihIni()) return null;

      // `dynacast` menurunkan kualitas otomatis saat jaringan memburuk.
      // `adaptiveStream` SENGAJA TIDAK dipakai: ia memutuskan perlu-tidaknya
      // video diteruskan dari elemen yang dipasang lewat `track.attach()`.
      // Kita merakit MediaStream sendiri tanpa attach, jadi bagi SDK video itu
      // tak pernah terlihat dan server berhenti meneruskannya. Gejalanya: suara
      // jalan, video 0 KB, tanpa galat di mana pun.
      const { Room, RoomEvent } = livekit;
      const room = new Room({ dynacast: true });
      roomRef.current = room;
      // Peristiwa dari ruang lama yang baru selesai memutus tidak boleh
      // membereskan panggilan baru yang kebetulan sudah dimulai.
      const ruangIni = () => roomRef.current === room;

      // Disambungkan ke TIGA peristiwa, dan ketiganya perlu (lihat
      // `statusSesudahPeristiwa`). `Connected` melayani yang MENGANGKAT, karena
      // lawannya sudah di ruangan sehingga `ParticipantConnected` tidak akan
      // dipancarkan. `ParticipantConnected` melayani yang MENELEPON.
      // `TrackSubscribed` jaring terakhir.
      const perbaruiStatus = () => {
        if (ruangIni()) ubahStatus((s) => statusSesudahPeristiwa(s, room.remoteParticipants.size > 0));
      };

      room
        .on(RoomEvent.ConnectionStateChanged, (s: ConnectionState) => {
          if (ruangIni()) setKoneksi(String(s));
        })
        .on(RoomEvent.Connected, perbaruiStatus)
        .on(RoomEvent.TrackSubscribed, () => {
          if (!ruangIni()) return;
          susunPeserta(room);
          perbaruiStatus();
        })
        .on(RoomEvent.TrackUnsubscribed, () => {
          if (ruangIni()) susunPeserta(room);
        })
        // Kamera lawan dimatikan/dinyalakan: tampilan berganti avatar/video.
        .on(RoomEvent.TrackMuted, () => {
          if (ruangIni()) susunPeserta(room);
        })
        .on(RoomEvent.TrackUnmuted, () => {
          if (ruangIni()) susunPeserta(room);
        })
        // Kamera sendiri menyala lagi = track BARU; stream pratinjau yang lama
        // memegang track mati dan hitam selamanya kalau tidak dirakit ulang.
        .on(RoomEvent.LocalTrackPublished, () => {
          if (ruangIni()) bangunLokal(room);
        })
        .on(RoomEvent.LocalTrackUnpublished, () => {
          if (ruangIni()) bangunLokal(room);
        })
        .on(RoomEvent.ParticipantConnected, () => {
          if (!ruangIni()) return;
          susunPeserta(room);
          perbaruiStatus();
        })
        .on(RoomEvent.ParticipantDisconnected, () => {
          if (!ruangIni()) return;
          susunPeserta(room);
          // Ruang yang tinggal berisi kita sendiri SESUDAH tersambung berarti
          // panggilannya selesai. Sebelum tersambung (penelepon menunggu
          // sendirian) itu bukan akhir, cuma belum dimulai.
          if (room.remoteParticipants.size === 0 && statusRef.current === "tersambung") bereskan();
        })
        .on(RoomEvent.Disconnected, () => {
          if (ruangIni()) bereskan();
        });

      try {
        await room.connect(izin.url, izin.token);
      } catch {
        return gagal(terbaruRef.current.t("chat_ui.call_error.server_unreachable"));
      }
      if (!masihIni()) {
        void room.disconnect();
        return null;
      }

      // Menyambung dan mengambil mikrofon adalah DUA kegagalan yang berbeda.
      // Menyatukannya dalam satu catch sempat membuat layar menuduh jaringan
      // padahal mikrofonnya yang ditolak.
      try {
        await room.localParticipant.setMicrophoneEnabled(true);
      } catch (e) {
        return gagal(pesanGalatMedia(e, typeof window !== "undefined" && window.isSecureContext, terbaruRef.current.t));
      }

      // Kamera boleh gagal tanpa membatalkan panggilan: suaranya sudah jalan.
      if (video)
        try {
          await room.localParticipant.setCameraEnabled(true);
        } catch (e) {
          terbaruRef.current.onGagal?.(
            `${terbaruRef.current.t("chat_ui.call_error.camera_failed")} ${pesanGalatMedia(e, typeof window !== "undefined" && window.isSecureContext, terbaruRef.current.t)}`
          );
          setKameraMati(true);
        }
      if (!masihIni()) return null;

      bangunLokal(room);

      return room;
    },
    [slug, susunPeserta, bangunLokal, bereskan, ubahStatus]
  );

  /** Jam dering habis: penelepon menyerah, yang ditelepon berhenti berdering. */
  const waktuHabis = useCallback(
    (id: string) => {
      const aktif = dmRef.current;
      const akibat = akibatWaktuHabis(aktif, statusRef.current, id);
      if (akibat === "abaikan" || !aktif) return;
      if (akibat === "tak_terjawab") kirimDm(aktif, "batal");
      terbaruRef.current.onKabar?.({ jenis: akibat, lawan: aktif.lawan, video: terbaruRef.current.pakaiVideo });
      // Laporan "selesai" tanpa "tersambung" = server mencatatnya tak terjawab.
      bereskan();
    },
    [kirimDm, bereskan]
  );
  const pasangJam = useCallback(
    (id: string, ms: number) => {
      if (jamRef.current) clearTimeout(jamRef.current);
      jamRef.current = setTimeout(() => waktuHabis(id), ms);
    },
    [waktuHabis]
  );

  /** Telepon satu orang di ruang DM bersamanya. */
  const panggil = useCallback(
    async (ke: string, ruang: string | null | undefined, video: boolean) => {
      if (statusRef.current !== "diam") return;
      // DM yang belum pernah berisi pesan belum punya ruang.
      if (!ruang) {
        terbaruRef.current.onGagal?.(terbaruRef.current.t("chat_ui.call_error.no_room"));
        return;
      }
      // Diperiksa SEBELUM masuk LiveKit: tanpa jalur sinyal, undangannya tidak
      // akan pernah sampai, dan yang menekan cuma menunggu sampai jam habis.
      if (!soketKehadiranTerbuka()) {
        terbaruRef.current.onGagal?.(terbaruRef.current.t("chat_ui.call_error.connection_down"));
        return;
      }
      const aktif: TPanggilanAktif = { id: idBaru(), lawan: ke, ruang, peran: "penelepon", terjawab: false };
      idRef.current = aktif.id;
      dmRef.current = aktif;
      setLawan(ke);
      setPakaiVideo(video);
      ubahStatus("menyambungkan");

      const room = await masukRuang(ruang, video, aktif.id);
      if (!room) return;

      // Log dimulai SEBELUM sinyal dikirim: penolakan yang datang sangat cepat
      // tidak boleh tiba lebih dulu daripada log yang hendak ditutupnya.
      mulaiLog(ruang, true, video);
      if (!kirimDm(aktif, "panggil", video)) {
        terbaruRef.current.onGagal?.(terbaruRef.current.t("chat_ui.call_error.connection_down"));
        bereskan();
        return;
      }
      // JANGAN menimpa "tersambung" di sini: lawan yang sudah ada di ruangan
      // tidak akan memancarkan peristiwa apa pun lagi (lihat tata-panggilan).
      ubahStatus((s) => (s === "tersambung" ? s : dmRef.current?.terjawab ? "menyambungkan" : "memanggil"));
      pasangJam(aktif.id, BATAS_DERING_PENELEPON_MS);
    },
    [masukRuang, mulaiLog, kirimDm, bereskan, ubahStatus, pasangJam]
  );

  /** Mulai atau ikut panggilan di sebuah kanal.
   *
   * Kanal tidak berdering ke satu orang. Undangannya disiarkan lewat soket
   * ruang ke anggota yang sedang membuka kanal itu, lalu mereka memutuskan
   * sendiri mau gabung atau tidak. Dering ke belasan orang sekaligus akan jadi
   * gangguan, bukan fitur.
   */
  const mulaiKonferensi = useCallback(
    async ({
      ruang,
      nama,
      video,
      kirimSinyalRuang,
    }: {
      ruang: string;
      nama: string;
      video: boolean;
      kirimSinyalRuang: TKirimSinyalRuang;
    }) => {
      if (statusRef.current !== "diam") return;
      // Yang IKUT konferensi berjalan tidak membuat log baru: satu panggilan
      // kanal = satu kartu, milik yang memulainya.
      const ikutYangBerjalan = konferensiBerjalan?.ruang === ruang;
      const id = idBaru();
      idRef.current = id;
      setKonferensi({ ruang, nama });
      setPakaiVideo(video);
      ubahStatus("menyambungkan");

      const room = await masukRuang(ruang, video, id);
      if (!room) return;

      if (!ikutYangBerjalan) mulaiLog(ruang, true, video);
      // Tanpa tujuan tertentu: server meneruskannya ke semua orang di ruang itu
      // kecuali pengirimnya.
      kirimSinyalRuang("", { jenis: "konferensi", video });
      ubahStatus("tersambung");
      setKonferensiBerjalan(null);
    },
    [konferensiBerjalan, masukRuang, mulaiLog, ubahStatus]
  );

  /** Angkat panggilan masuk. `video` false = angkat tanpa kamera walau
   * undangannya panggilan video. */
  const angkat = useCallback(
    async (video: boolean) => {
      const aktif = dmRef.current;
      if (!aktif || aktif.peran !== "penerima" || statusRef.current !== "berdering") return;
      if (jamRef.current) clearTimeout(jamRef.current);
      jamRef.current = null;
      setPakaiVideo(video);
      ubahStatus("menyambungkan");
      // `terima` dikirim DULU: menghentikan jam penelepon dan dering di tab lain
      // milik saya, sebelum masuk LiveKit yang bisa makan beberapa detik.
      if (!kirimDm(aktif, "terima")) {
        terbaruRef.current.onGagal?.(terbaruRef.current.t("chat_ui.call_error.connection_down"));
        bereskan();
        return;
      }
      // Gagal masuk harus dikabarkan ke penelepon, kalau tidak ia menunggu di
      // "Menyambungkan" sampai menyerah sendiri. `aktif` disalin sebelum await
      // karena pembersihan mengosongkan `dmRef`.
      if (!(await masukRuang(aktif.ruang, video, aktif.id))) kirimDm(aktif, "tutup");
    },
    [masukRuang, kirimDm, bereskan, ubahStatus]
  );

  /** Tolak, batalkan, atau akhiri, tergantung keadaannya (`sinyalTutup`). */
  const tutup = useCallback(() => {
    const aktif = dmRef.current;
    if (aktif) kirimDm(aktif, sinyalTutup(aktif, statusRef.current));
    bereskan();
  }, [kirimDm, bereskan]);

  /** Sinyal DM dari soket kehadiran. Keputusannya di `putuskanSinyal` (murni,
   * ada pemeriksaannya); di sini hanya menjalankannya. */
  const terimaSinyalDm = useCallback(
    (pesan: unknown) => {
      const sinyal = bacaSinyalPanggilan(pesan);
      const sayaId = terbaruRef.current.saya;
      if (!sinyal || !sayaId) return;
      const aktif = dmRef.current;
      const keputusan = putuskanSinyal(aktif, statusRef.current, sinyal, sayaId);

      switch (keputusan) {
        case "dering": {
          const baru: TPanggilanAktif = {
            id: sinyal.muatan.id,
            lawan: sinyal.dari,
            ruang: sinyal.ruang,
            peran: "penerima",
            terjawab: false,
          };
          idRef.current = baru.id;
          dmRef.current = baru;
          setLawan(baru.lawan);
          setPakaiVideo(Boolean(sinyal.muatan.video));
          ubahStatus("berdering");
          // Yang ditelepon ikut melapor (tersambung/selesai) ke log milik penelepon.
          mulaiLog(baru.ruang, false, Boolean(sinyal.muatan.video));
          pasangJam(baru.id, BATAS_DERING_PENERIMA_MS);
          return;
        }
        case "balas_sibuk":
          kirimSinyalPanggilan({
            ke: sinyal.dari,
            ruang: sinyal.ruang,
            muatan: { jenis: "sibuk", id: sinyal.muatan.id },
          });
          return;
        case "berhenti_senyap":
          bereskan({ lapor: false });
          return;
        case "terjawab":
          if (aktif) dmRef.current = { ...aktif, terjawab: true };
          if (jamRef.current) clearTimeout(jamRef.current);
          jamRef.current = null;
          ubahStatus((s) => (s === "memanggil" ? "menyambungkan" : s));
          return;
        case "ditolak":
        case "sibuk":
        case "terlewat":
          if (aktif)
            terbaruRef.current.onKabar?.({
              jenis: keputusan,
              lawan: aktif.lawan,
              video: terbaruRef.current.pakaiVideo,
            });
          bereskan();
          return;
        case "ditutup":
          bereskan();
          return;
        case "bertemu":
        // Dua orang saling menelepon bersamaan: keduanya sudah menuju ruang
        // LiveKit yang sama dan akan tersambung lewat kehadiran peserta.
        // Membalas `sibuk` di sini membuat keduanya saling membatalkan.
        case "abaikan":
        default:
      }
    },
    [bereskan, mulaiLog, pasangJam, ubahStatus]
  );

  /** Sinyal dari soket RUANG yang sedang terbuka di halaman Obrolan. Sejak DM
   * pindah ke soket kehadiran, yang tersisa di sini hanya ajakan konferensi. */
  const terimaSinyalRuang = useCallback((ruang: string | null, muatan: unknown) => {
    const sinyal = muatan as { jenis?: string; video?: boolean } | null;
    if (!ruang || sinyal?.jenis !== "konferensi") return;
    // Tidak berdering, hanya menandai. Yang sedang membuka kanal melihat ajakan.
    if (statusRef.current === "diam") setKonferensiBerjalan({ ruang, video: Boolean(sinyal.video) });
  }, []);

  /** Halaman Obrolan pindah kanal atau ditutup: ajakan lamanya tidak berlaku. */
  const lupakanKonferensi = useCallback(() => setKonferensiBerjalan(null), []);

  // Penangan dipanggil lewat ref supaya langganan soket tidak dibongkar-pasang
  // tiap kali identitas callback berubah.
  const terimaDmRef = useRef(terimaSinyalDm);
  useEffect(() => {
    terimaDmRef.current = terimaSinyalDm;
  });
  useEffect(() => dengarPanggilan((pesan) => terimaDmRef.current(pesan)), []);

  // Tab ditutup atau dimuat ulang di tengah panggilan: kabari lawan sebisanya.
  // Tanpa ini yang ditelepon berdering sampai jam pengamannya habis, dan lawan
  // bicara baru tahu sesudah LiveKit menyadari pesertanya hilang.
  useEffect(() => {
    const pergi = () => {
      const aktif = dmRef.current;
      if (aktif) kirimDm(aktif, sinyalTutup(aktif, statusRef.current));
    };
    window.addEventListener("pagehide", pergi);
    return () => window.removeEventListener("pagehide", pergi);
  }, [kirimDm]);

  const setelMik = useCallback((mati: boolean) => {
    void roomRef.current?.localParticipant.setMicrophoneEnabled(!mati);
    setMikMati(mati);
  }, []);

  const setelKamera = useCallback(
    (mati: boolean) => {
      const room = roomRef.current;
      setKameraMati(mati);
      if (!room) return;
      // Dirakit ulang sesudah kamera benar-benar berganti, dan kegagalannya
      // dikabarkan: menyalakan kamera di tengah panggilan suara bisa ditolak.
      void room.localParticipant
        .setCameraEnabled(!mati)
        .then(() => (roomRef.current === room ? bangunLokal(room) : undefined))
        .catch((e: unknown) => {
          setKameraMati(true);
          terbaruRef.current.onGagal?.(
            `${terbaruRef.current.t("chat_ui.call_error.camera_failed")} ${pesanGalatMedia(e, typeof window !== "undefined" && window.isSecureContext, terbaruRef.current.t)}`
          );
        });
    },
    [bangunLokal]
  );

  // "tersambung" di sini berarti lawan benar-benar hadir (lihat tata-panggilan),
  // jadi aman dipakai sebagai awal durasi di log panggilan. Sekali per panggilan.
  useEffect(() => {
    const log = logRef.current;
    if (status !== "tersambung" || !log || log.tersambung) return;
    log.tersambung = true;
    lapor("tersambung");
  }, [status, lapor]);

  /** Byte yang BENAR-BENAR masuk, dibaca dari statistik WebRTC.
   *
   * Status koneksi dan track yang tiba dua-duanya bisa terlihat benar sementara
   * nol byte berpindah, dan itu sudah pernah menyesatkan diagnosis di sini.
   */
  useEffect(() => {
    if (status !== "tersambung") return undefined;

    const id = setInterval(() => {
      const room = roomRef.current;
      if (!room) return;

      const tugas: Promise<{ audio: number; video: number }>[] = [];
      room.remoteParticipants.forEach((peserta) => {
        peserta.trackPublications.forEach((pub) => {
          const track = pub.track;
          if (!track) return;
          tugas.push(
            track
              .getRTCStatsReport()
              .then((laporan) => {
                let audio = 0;
                let video = 0;
                laporan?.forEach((baris: { type?: string; kind?: string; bytesReceived?: number }) => {
                  if (baris.type !== "inbound-rtp") return;
                  if (baris.kind === "audio") audio += baris.bytesReceived ?? 0;
                  if (baris.kind === "video") video += baris.bytesReceived ?? 0;
                });
                return { audio, video };
              })
              .catch(() => ({ audio: 0, video: 0 }))
          );
        });
      });

      void Promise.all(tugas).then((hasil) => {
        setByteMasuk({
          audio: hasil.reduce((n, h) => n + h.audio, 0),
          video: hasil.reduce((n, h) => n + h.video, 0),
        });
        return undefined;
      });
    }, 2000);

    return () => clearInterval(id);
  }, [status]);

  // Panggilan hidup selama tab berada di workspace ini; keluar workspace memutusnya.
  const tutupRef = useRef(tutup);
  useEffect(() => {
    tutupRef.current = tutup;
  });
  useEffect(() => () => tutupRef.current(), []);

  return {
    status,
    koneksi,
    lawan,
    konferensi,
    pakaiVideo,
    mikMati,
    kameraMati,
    streamLokal,
    pesertaJauh,
    konferensiBerjalan,
    byteMasuk,
    panggil,
    mulaiKonferensi,
    angkat,
    tutup,
    terimaSinyalRuang,
    lupakanKonferensi,
    setelMik,
    setelKamera,
  };
}

export type TPanggilan = ReturnType<typeof usePanggilan>;
