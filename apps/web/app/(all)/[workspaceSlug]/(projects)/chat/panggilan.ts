/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: panggilan suara & video
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { ConnectionState, Room, RoomEvent, Track } from "livekit-client";
import { useTranslation } from "@plane/i18n";
import { ChatService } from "@/services/chat.service";
import { pesanGalatMedia } from "./galat-media";
import { statusSesudahPeristiwa } from "./tata-panggilan";

const chatService = new ChatService();

/**
 * Panggilan lewat LiveKit, bukan peer ke peer.
 *
 * KENAPA DITULIS ULANG
 * Versi pertama memakai RTCPeerConnection langsung, dua peramban saling
 * menyambung. Secara teori itu cukup untuk dua orang di satu kantor. Dalam
 * praktik ia gagal berulang kali, dan sebab terdalamnya tidak bisa diperbaiki
 * dari sisi kode: peer ke peer menuntut kedua KOMPUTER bisa saling menghubungi
 * langsung, dan jaringan kantor ini tidak mengizinkannya.
 *
 * LiveKit membalik arahnya. Ia SFU: kedua peramban menyambung KE SERVER, lalu
 * server meneruskan media. Jalur komputer ke server sudah pasti terbuka, karena
 * aplikasinya sendiri berjalan lewat jalur itu.
 *
 * Yang ikut hilang bersama peer ke peer, dan TIAP SATUNYA pernah jadi bug nyata
 * di versi buatan sendiri: urutan setRemoteDescription dan addTrack, antrean
 * kandidat ICE yang tiba terlalu dini, perakitan stream jauh saat track datang
 * tanpa stream, tabrakan saat dua orang menelepon bersamaan, dan sambung ulang
 * ketika jaringan berkedip. Semuanya sudah ditangani klien LiveKit.
 *
 * YANG TETAP MILIK KITA: dering. LiveKit tidak punya konsep "sedang dipanggil",
 * ia hanya tahu ruang yang bisa dimasuki. Jadi undangan tetap lewat soket
 * obrolan, dan itu memang tempatnya, karena hak menelepon sama persis dengan
 * hak membaca ruangnya.
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
};

type TSinyal =
  | { jenis: "panggil"; video: boolean }
  | { jenis: "konferensi"; video: boolean }
  | { jenis: "tolak" }
  | { jenis: "tutup" };

type Opsi = {
  slug?: string;
  /** Ruang obrolan yang sedang dibuka. Panggilan selalu terjadi di dalamnya. */
  ruangId?: string | null;
  /** Mengembalikan false kalau soket sedang putus. */
  kirimSinyal: (ke: string, muatan: unknown) => boolean;
  onGagal?: (pesan: string) => void;
};

export function usePanggilan({ slug, ruangId, kirimSinyal, onGagal }: Opsi) {
  // Lewat ref supaya callback panggilan tidak dibuat ulang tiap bahasa berganti.
  const { t } = useTranslation();
  const tRef = useRef(t);
  tRef.current = t;
  const [status, setStatus] = useState<TStatusPanggilan>("diam");
  const [koneksi, setKoneksi] = useState("belum mulai");
  const [lawan, setLawan] = useState<string | null>(null);
  const [pakaiVideo, setPakaiVideo] = useState(false);
  const [mikMati, setMikMati] = useState(false);
  const [kameraMati, setKameraMati] = useState(false);
  const [streamLokal, setStreamLokal] = useState<MediaStream | null>(null);
  const [pesertaJauh, setPesertaJauh] = useState<TPesertaJauh[]>([]);
  /** Ada panggilan berlangsung di kanal ini yang belum kita ikuti. */
  const [konferensiBerjalan, setKonferensiBerjalan] = useState(false);
  const [byteMasuk, setByteMasuk] = useState({ audio: 0, video: 0 });

  const roomRef = useRef<Room | null>(null);
  const lawanRef = useRef<string | null>(null);
  const gagalRef = useRef(onGagal);
  gagalRef.current = onGagal;

  const bereskan = useCallback(() => {
    // `disconnect()` menghentikan track lokal, menutup sambungan, dan melepas
    // seluruh listener sekaligus. Satu panggilan yang menggantikan pembersihan
    // manual yang dulu panjang dan mudah terlewat separuh, meninggalkan lampu
    // kamera menyala sampai tabnya ditutup.
    void roomRef.current?.disconnect();
    roomRef.current = null;
    lawanRef.current = null;
    setStatus("diam");
    setKoneksi("belum mulai");
    setLawan(null);
    setStreamLokal(null);
    setPesertaJauh([]);
    setKonferensiBerjalan(false);
    setMikMati(false);
    setKameraMati(false);
    setByteMasuk({ audio: 0, video: 0 });
  }, []);

  /** Rakit ulang daftar peserta dari seluruh track yang sedang berlangganan.
   *
   * Stream dirakit PER ORANG, bukan satu stream gabungan. Menggabungkan semua
   * track ke satu MediaStream membuat suara semua orang keluar dari satu elemen
   * dan gambarnya bertumpuk; untuk dua orang itu masih terlihat benar, dan baru
   * ketahuan salah begitu ada orang ketiga.
   */
  const susunPeserta = useCallback((room: Room) => {
    const daftar: TPesertaJauh[] = [];
    room.remoteParticipants.forEach((peserta) => {
      const track: MediaStreamTrack[] = [];
      let adaVideo = false;
      peserta.trackPublications.forEach((pub) => {
        const mst = pub.track?.mediaStreamTrack;
        if (!mst) return;
        track.push(mst);
        if (pub.kind === Track.Kind.Video) adaVideo = true;
      });
      if (track.length === 0) return;
      daftar.push({
        id: peserta.identity,
        nama: peserta.name || peserta.identity,
        stream: new MediaStream(track),
        adaVideo,
      });
    });
    setPesertaJauh(daftar);
  }, []);

  /** Sambung ke ruang panggilan dan mulai mengirim media. */
  const masukRuang = useCallback(
    async (video: boolean) => {
      if (!slug || !ruangId) {
        gagalRef.current?.(tRef.current("chat_ui.call_error.no_room"));
        return null;
      }

      let izin: { url: string; token: string };
      try {
        izin = await chatService.getTokenPanggilan(slug, ruangId);
      } catch (e) {
        gagalRef.current?.((e as { error?: string })?.error ?? tRef.current("chat_ui.call_error.cannot_start"));
        return null;
      }

      // `adaptiveStream` dan `dynacast` menurunkan kualitas otomatis saat
      // jaringan memburuk, alih-alih memutus panggilan. Untuk dua orang
      // biayanya nyaris nol.
      const room = new Room({ adaptiveStream: true, dynacast: true });
      roomRef.current = room;

      // Disambungkan ke TIGA peristiwa, dan ketiganya perlu. `Connected` melayani
      // yang MENGANGKAT, karena lawannya sudah berada di ruangan sebelum ia masuk
      // sehingga `ParticipantConnected` tidak akan pernah dipancarkan untuk orang
      // itu. `ParticipantConnected` melayani yang MENELEPON, yang masuk duluan dan
      // sendirian. `TrackSubscribed` jadi jaring terakhir kalau daftar peserta
      // ternyata belum terisi saat `Connected` dipancarkan.
      const perbaruiStatus = () => setStatus((s) => statusSesudahPeristiwa(s, room.remoteParticipants.size > 0));

      room
        .on(RoomEvent.ConnectionStateChanged, (s: ConnectionState) => setKoneksi(String(s)))
        .on(RoomEvent.Connected, perbaruiStatus)
        .on(RoomEvent.TrackSubscribed, () => {
          susunPeserta(room);
          perbaruiStatus();
        })
        .on(RoomEvent.TrackUnsubscribed, () => susunPeserta(room))
        .on(RoomEvent.ParticipantConnected, () => {
          susunPeserta(room);
          perbaruiStatus();
        })
        .on(RoomEvent.ParticipantDisconnected, () => {
          susunPeserta(room);
          // Ruang yang tinggal berisi kita sendiri berarti panggilannya selesai.
          // Berlaku sama untuk berdua maupun konferensi, jadi tidak perlu
          // cabang kode kedua.
          if (room.remoteParticipants.size === 0) bereskan();
        })
        .on(RoomEvent.Disconnected, () => bereskan());

      try {
        await room.connect(izin.url, izin.token);
      } catch {
        gagalRef.current?.(tRef.current("chat_ui.call_error.server_unreachable"));
        bereskan();
        return null;
      }

      // Menyambung dan mengambil mikrofon adalah DUA kegagalan yang berbeda, dan
      // menyatukannya dalam satu catch sempat menyembunyikan sebab yang sebenarnya:
      // sambungan berhasil, mikrofonnya yang ditolak, sementara layar menuduh
      // jaringan. Log LiveKit memperlihatkannya sebagai peserta yang masuk lalu
      // keluar sendiri dalam 40 milidetik tanpa menerbitkan satu track pun.
      try {
        await room.localParticipant.setMicrophoneEnabled(true);
      } catch (e) {
        gagalRef.current?.(pesanGalatMedia(e, typeof window !== "undefined" && window.isSecureContext, tRef.current));
        bereskan();
        return null;
      }

      // Kamera boleh gagal tanpa membatalkan panggilan: suaranya sudah jalan, dan
      // memutus panggilan yang berfungsi karena webcam-nya rusak itu lebih buruk
      // daripada meneruskannya sebagai panggilan suara.
      if (video)
        try {
          await room.localParticipant.setCameraEnabled(true);
        } catch (e) {
          gagalRef.current?.(
            `${tRef.current("chat_ui.call_error.camera_failed")} ${pesanGalatMedia(e, typeof window !== "undefined" && window.isSecureContext, tRef.current)}`
          );
          setKameraMati(true);
        }

      const lokal: MediaStreamTrack[] = [];
      room.localParticipant.trackPublications.forEach((pub) => {
        if (pub.track?.mediaStreamTrack) lokal.push(pub.track.mediaStreamTrack);
      });
      setStreamLokal(lokal.length > 0 ? new MediaStream(lokal) : null);

      return room;
    },
    [slug, ruangId, susunPeserta, bereskan]
  );

  const panggil = useCallback(
    async (ke: string, video: boolean) => {
      if (status !== "diam") return;
      lawanRef.current = ke;
      setLawan(ke);
      setPakaiVideo(video);
      setStatus("menyambungkan");

      const room = await masukRuang(video);
      if (!room) return;

      if (!kirimSinyal(ke, { jenis: "panggil", video })) {
        gagalRef.current?.(tRef.current("chat_ui.call_error.connection_down"));
        bereskan();
        return;
      }
      // JANGAN menimpa "tersambung" di sini. Lawan yang sudah berada di ruangan
      // sejak sebelum kita masuk, misalnya karena panggilan sebelumnya belum
      // benar-benar ditutup, tidak akan memancarkan peristiwa apa pun lagi, jadi
      // status yang tertimpa di baris ini tidak akan pernah pulih.
      setStatus((s) => (s === "tersambung" ? s : "memanggil"));
    },
    [status, masukRuang, kirimSinyal, bereskan]
  );

  /** Mulai atau ikut panggilan di sebuah kanal.
   *
   * Kanal tidak berdering ke satu orang. Undangannya disiarkan ke seluruh
   * anggota yang sedang membuka kanal itu, lalu mereka memutuskan sendiri mau
   * gabung atau tidak, seperti panggilan di kanal aplikasi obrolan lain.
   * Meneleponkan dering ke belasan orang sekaligus akan jadi gangguan, bukan
   * fitur.
   */
  const mulaiKonferensi = useCallback(
    async (video: boolean) => {
      if (status !== "diam") return;
      setPakaiVideo(video);
      setStatus("menyambungkan");

      const room = await masukRuang(video);
      if (!room) return;

      // Disiarkan tanpa tujuan tertentu: server meneruskannya ke semua orang di
      // ruang itu kecuali pengirimnya.
      kirimSinyal("", { jenis: "konferensi", video });
      setStatus("tersambung");
      setKonferensiBerjalan(false);
    },
    [status, masukRuang, kirimSinyal]
  );

  const angkat = useCallback(async () => {
    const ke = lawanRef.current;
    if (!ke || status !== "berdering") return;
    setStatus("menyambungkan");
    // Gagal mengangkat harus dikabarkan. Tanpa ini penelepon menunggu di layar
    // "Memanggil" sampai ia menyerah sendiri, sementara yang dipanggil sudah
    // melihat pesan galat dan mengira panggilannya sudah putus untuk keduanya.
    // `lawanRef` disalin lebih dulu karena pembersihan di dalam mengosongkannya.
    if (!(await masukRuang(pakaiVideo))) kirimSinyal(ke, { jenis: "tolak" });
  }, [status, pakaiVideo, masukRuang, kirimSinyal]);

  const tutup = useCallback(() => {
    const ke = lawanRef.current;
    if (ke) kirimSinyal(ke, { jenis: status === "berdering" ? "tolak" : "tutup" });
    bereskan();
  }, [status, kirimSinyal, bereskan]);

  const terimaSinyal = useCallback(
    async (dari: string, muatan: unknown) => {
      const sinyal = muatan as TSinyal;
      if (!sinyal?.jenis) return;

      if (sinyal.jenis === "panggil") {
        // Dua orang menelepon bersamaan: yang datang belakangan ditolak, bukan
        // dibiarkan menimpa panggilan yang sedang berjalan.
        if (status !== "diam") {
          kirimSinyal(dari, { jenis: "tolak" });
          return;
        }
        lawanRef.current = dari;
        setLawan(dari);
        setPakaiVideo(sinyal.video);
        setStatus("berdering");
        return;
      }

      if (sinyal.jenis === "konferensi") {
        // Tidak berdering, hanya menandai. Yang sedang membuka kanal akan
        // melihat ajakan bergabung.
        if (status === "diam") {
          setPakaiVideo(sinyal.video);
          setKonferensiBerjalan(true);
        }
        return;
      }

      if (sinyal.jenis === "tolak" || sinyal.jenis === "tutup") bereskan();
    },
    [status, kirimSinyal, bereskan]
  );

  const lawanPergi = useCallback(
    (dari: string) => {
      if (lawanRef.current === dari) bereskan();
    },
    [bereskan]
  );

  const setelMik = useCallback((mati: boolean) => {
    void roomRef.current?.localParticipant.setMicrophoneEnabled(!mati);
    setMikMati(mati);
  }, []);

  const setelKamera = useCallback((mati: boolean) => {
    void roomRef.current?.localParticipant.setCameraEnabled(!mati);
    setKameraMati(mati);
  }, []);

  /** Byte yang BENAR-BENAR masuk, dibaca dari statistik WebRTC.
   *
   * Status koneksi dan track yang tiba dua-duanya bisa terlihat benar sementara
   * nol byte berpindah, dan itu sudah pernah menyesatkan diagnosis di sini.
   * Angka ini satu-satunya yang tidak bisa dibantah tampilan apa pun.
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

  // Panggilan tidak boleh hidup lebih lama dari halamannya.
  useEffect(() => () => bereskan(), [bereskan]);

  return {
    status,
    koneksi,
    lawan,
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
    terimaSinyal,
    lawanPergi,
    setelMik,
    setelKamera,
  };
}
