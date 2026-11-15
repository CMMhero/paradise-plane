/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: layar panggilan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useTranslation } from "@plane/i18n";
import { useEffect, useRef } from "react";
import { Mic, MicOff, Phone, PhoneOff, Video, VideoOff } from "lucide-react";
import { Avatar } from "@plane/propel/avatar";
import type { TPesertaJauh, TStatusPanggilan } from "./panggilan";
import { tataPanggilan } from "./tata-panggilan";

/** `videoMati` opsional: diisi hook saat lawan mematikan kameranya (track
 * tetap ada tapi membeku hitam). Tanpa itu kotaknya hitam, bukan avatar. */
type TPesertaTampil = TPesertaJauh & { videoMati?: boolean };

type Props = {
  status: TStatusPanggilan;
  koneksi: string;
  judul: string;
  /** Foto profil untuk judul (lawan bicara di DM). Kosong = inisial. */
  avatarJudul?: string;
  /** Foto profil peserta dari identitas LiveKit (= id pengguna). */
  cariAvatar?: (id: string) => string | undefined;
  pakaiVideo: boolean;
  mikMati: boolean;
  kameraMati: boolean;
  streamLokal: MediaStream | null;
  pesertaJauh: TPesertaTampil[];
  byteMasuk: { audio: number; video: number };
  onAngkat: () => void;
  onTutup: () => void;
  onSetelMik: (mati: boolean) => void;
  onSetelKamera: (mati: boolean) => void;
};

/**
 * Satu elemen media yang memegang streamnya sendiri.
 *
 * KENAPA KOMPONEN SENDIRI, dan ini pernah salah sampai panggilan tidak
 * mengeluarkan suara maupun gambar sama sekali: versi sebelumnya memasang
 * `srcObject` lewat useEffect di komponen induk, sementara elemen videonya
 * dirender bersyarat. Saat stream didapat elemennya belum ada; saat elemennya
 * muncul efeknya tidak jalan lagi karena dependensinya tidak berubah.
 * `srcObject` tidak pernah terpasang, dan tidak ada satu pun error yang muncul.
 *
 * Di sini elemen dan efeknya hidup di komponen yang sama, jadi keduanya tidak
 * bisa lagi saling mendahului.
 */
function Media({ stream, className, bisu = false }: { stream: MediaStream | null; className: string; bisu?: boolean }) {
  const ref = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    // Induk merakit MediaStream BARU tiap ada peristiwa ruang, walau isi
    // track-nya sama. Memasang ulang `srcObject` pada stream yang isinya sama
    // memutus pemutaran sesaat (suara tersendat, gambar berkedip), jadi hanya
    // dipasang ulang kalau himpunan track-nya benar-benar berbeda. Kamera yang
    // dinyalakan ulang menghasilkan track baru, jadi tetap lolos.
    if (el.srcObject !== stream && !samaTrack(el.srcObject as MediaStream | null, stream)) {
      el.srcObject = stream;
    }
    if (!stream) return undefined;

    // Kebijakan autoplay (Safari iOS, Chrome Android) bisa menolak pemutaran
    // walau panggilan dimulai dari klik: yang mengangkat lewat dering atau
    // yang menunggu lama sudah di luar jendela gestur. Ditolak = kotak hitam
    // atau sunyi tanpa error. Jadi dicoba lagi saat metadata siap dan pada
    // sentuhan/klik berikutnya di mana pun.
    const putar = () => {
      if (el.paused) void el.play().catch(() => undefined);
    };
    putar();
    el.addEventListener("loadedmetadata", putar);
    document.addEventListener("pointerdown", putar);
    return () => {
      el.removeEventListener("loadedmetadata", putar);
      document.removeEventListener("pointerdown", putar);
    };
  }, [stream]);

  // eslint-disable-next-line jsx-a11y/media-has-caption
  return <video ref={ref} autoPlay playsInline muted={bisu} className={className} />;
}

/** Dua stream dianggap sama kalau memuat track yang persis sama. */
function samaTrack(a: MediaStream | null, b: MediaStream | null): boolean {
  if (!a || !b) return false;
  const ta = a.getTracks();
  const tb = b.getTracks();
  return ta.length === tb.length && ta.every((t) => tb.includes(t));
}

/** Satu kotak peserta: gambarnya kalau ada, avatar kalau hanya suara. */
function Peserta({ peserta, avatar }: { peserta: TPesertaTampil; avatar?: string }) {
  const tampilVideo = peserta.adaVideo && !peserta.videoMati;
  return (
    <div className="relative flex min-h-0 items-center justify-center overflow-hidden rounded-card bg-black/60">
      {/* Elemen media SELALU terpasang, juga saat peserta hanya mengirim suara.
          Kalau ia ikut dirender bersyarat, audionya tidak punya tempat keluar. */}
      <Media stream={peserta.stream} className={tampilVideo ? "h-full w-full object-contain" : "hidden"} />
      {!tampilVideo ? <Avatar name={peserta.nama} src={avatar} size={64} shape="circle" /> : null}
      <span className="absolute bottom-2 left-2 rounded-item bg-black/60 px-1.5 py-0.5 text-12 text-white/90">
        {peserta.nama}
      </span>
    </div>
  );
}

export function PanggilanLayar({
  status,
  koneksi,
  judul,
  avatarJudul,
  cariAvatar,
  pakaiVideo,
  mikMati,
  kameraMati,
  streamLokal,
  pesertaJauh,
  byteMasuk,
  onAngkat,
  onTutup,
  onSetelMik,
  onSetelKamera,
}: Props) {
  const { t } = useTranslation();
  const tata = tataPanggilan(status, pakaiVideo, Boolean(streamLokal), pesertaJauh.length);
  const tombolUtamaRef = useRef<HTMLButtonElement>(null);
  const tampil = tata.tampil;

  // Dialog modal: fokus dipindah ke tombol utama (tutup, atau angkat saat
  // berdering) begitu layar muncul, dan dikembalikan ke elemen sebelumnya saat
  // layar hilang. Efek ini jalan lagi saat berpindah dering -> tersambung
  // karena tombol yang tampil berganti.
  useEffect(() => {
    if (!tampil) return undefined;
    const sebelumnya = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    tombolUtamaRef.current?.focus();
    return () => {
      // Hanya kalau sebelumnya masih ada di dokumen; elemen yang sudah dilepas tidak bisa difokus.
      if (sebelumnya?.isConnected) sebelumnya.focus();
    };
  }, [tampil]);
  if (!tampil) return null;

  const keterangan =
    status === "berdering"
      ? t("chat_ui.call.ringing")
      : status === "memanggil"
        ? t("chat_ui.call.waiting")
        : status === "menyambungkan"
          ? t("chat_ui.call.connecting")
          : pesertaJauh.length > 1
            ? t("chat_ui.call.participants", { count: pesertaJauh.length + 1 })
            : t("chat_ui.call.connected");

  return (
    // oxlint-disable-next-line jsx-a11y/no-noninteractive-element-interactions -- penangan Escape/Tab milik dialog modal
    <div
      // oxlint-disable-next-line jsx-a11y/prefer-tag-over-role -- <dialog> asli butuh showModal(); lapisan ini sengaja selalu terpasang
      role="dialog"
      aria-modal="true"
      aria-labelledby="panggilan-layar-judul"
      aria-describedby="panggilan-layar-keterangan"
      className="fixed inset-0 z-40 flex flex-col items-center justify-center bg-black/85 p-3 sm:p-6"
      onKeyDown={(e) => {
        // Escape TIDAK mengakhiri panggilan: satu ketukan tak sengaja tidak
        // boleh memutus rapat. Menutup hanya lewat tombol Akhiri.
        if (e.key === "Escape") {
          e.preventDefault();
          e.stopPropagation();
          return;
        }
        // Fokus terkurung di tombol layar ini selagi dialog modal terbuka.
        if (e.key !== "Tab") return;
        const tombol = Array.from(e.currentTarget.querySelectorAll<HTMLButtonElement>("button:not(:disabled)"));
        if (tombol.length === 0) return;
        const pertama = tombol[0];
        const terakhir = tombol[tombol.length - 1];
        const aktif = document.activeElement;
        if (e.shiftKey && (aktif === pertama || !e.currentTarget.contains(aktif))) {
          e.preventDefault();
          terakhir.focus();
        } else if (!e.shiftKey && (aktif === terakhir || !e.currentTarget.contains(aktif))) {
          e.preventDefault();
          pertama.focus();
        }
      }}
    >
      <div className="relative flex min-h-0 w-full max-w-5xl flex-1 items-center justify-center">
        {tata.adaPeserta ? (
          // Kisi mengikuti RUANG YANG ADA, bukan jumlah peserta. `auto-fit`
          // memuat sebanyak yang muat dengan lebar minimum 240px, lalu
          // MENGEMPISKAN jalur kosong sehingga yang tersisa melar memenuhi
          // lebar. Hasilnya benar di tiap ukuran tanpa satu baris JS: dua
          // peserta di laptop jadi dua kolom lebar, dua peserta yang sama di
          // HP 375px jadi satu kolom bertumpuk. Sebelumnya jumlah kolom
          // dihitung dari cacah peserta, jadi di HP dua orang dipaksa berbagi
          // layar 375px, masing-masing 160px.
          <div className="grid h-full w-full grid-cols-[repeat(auto-fit,minmax(240px,1fr))] gap-2">
            {pesertaJauh.map((p) => (
              <Peserta key={p.id} peserta={p} avatar={cariAvatar?.(p.id)} />
            ))}
          </div>
        ) : (
          <Avatar name={judul} src={avatarJudul} size={80} shape="circle" />
        )}

        {/* Pratinjau diri tampil SEJAK MEMANGGIL, bukan setelah tersambung.
            Kalau kameranya bermasalah, orang tahu sejak detik pertama alih-alih
            menunggu panggilan yang memang tidak akan menampilkan apa pun.
            Selalu dibisukan supaya suara sendiri tidak menggema. */}
        {tata.pratinjauDiriTerlihat ? (
          <Media
            stream={streamLokal}
            bisu
            className={`absolute right-2 bottom-2 w-24 rounded-item border border-white/20 bg-black object-cover shadow-overlay-200 sm:right-3 sm:bottom-3 sm:w-32 ${kameraMati ? "hidden" : ""}`}
          />
        ) : null}
      </div>

      <p id="panggilan-layar-judul" className="mt-5 text-16 font-medium text-white">
        {judul}
      </p>
      <p id="panggilan-layar-keterangan" className="mt-1 text-13 text-white/75">
        {keterangan}
      </p>
      {/* Angka byte adalah SATU-SATUNYA bukti media benar-benar mengalir: status
          koneksi, track yang tiba, bahkan tulisan "Tersambung" semuanya bisa
          terlihat benar sementara nol byte berpindah. Tapi itu bahan diagnosis,
          bukan informasi untuk orang yang sedang menelepon, jadi baris teknis ini
          HANYA muncul saat sudah tersambung namun belum ada byte yang masuk. */}
      {status === "tersambung" && byteMasuk.audio === 0 && byteMasuk.video === 0 ? (
        <>
          <p className="mt-1 text-12 text-white/70">
            {koneksi}
            {streamLokal ? ` · ${t("chat_ui.call.mic_ready")}` : ` · ${t("chat_ui.call.mic_not_ready")}`}
            {` · ${t("chat_ui.call.incoming")} `}
            {Math.round(byteMasuk.audio / 1024)} {t("chat_ui.call.kb_audio")} / {Math.round(byteMasuk.video / 1024)}{" "}
            {t("chat_ui.call.kb_video")}
          </p>
          <p className="mt-2 max-w-md text-center text-12 text-label-yellow-icon">{t("chat_ui.call.no_data")}</p>
        </>
      ) : null}

      {/* Merah dan hijau di sini SENGAJA dipatok, bukan memakai token semantik.
          Layar panggilan selalu berlatar hitam apa pun tema aplikasinya,
          sementara `--bg-danger-primary` berbalik antar tema: `red-700` di tema
          terang, `red-300` di gelap. Memakainya di sini membuat tombol tutup
          jadi merah gelap di atas latar hitam ketika temanya terang. Token yang
          benar untuk permukaan bertema, bukan untuk lapisan yang temanya tetap. */}
      <div className="mt-4 flex items-center gap-3 sm:mt-7">
        {status === "berdering" ? (
          <>
            <button
              type="button"
              onClick={onAngkat}
              aria-label={t("chat_ui.call.accept")}
              className="bg-green-600 hover:bg-green-700 flex size-14 items-center justify-center rounded-control text-white"
            >
              <Phone className="size-6" />
            </button>
            <button
              ref={tombolUtamaRef}
              type="button"
              onClick={onTutup}
              aria-label={t("chat_ui.call.decline")}
              className="bg-red-600 hover:bg-red-700 flex size-14 items-center justify-center rounded-control text-white"
            >
              <PhoneOff className="size-6" />
            </button>
          </>
        ) : (
          <>
            <button
              type="button"
              onClick={() => onSetelMik(!mikMati)}
              // Nama tetap, keadaannya lewat aria-pressed (menyala = ditekan); judul
              // tooltip menyebut aksi berikutnya.
              aria-label={t("chat_ui.call.mic_label")}
              aria-pressed={!mikMati}
              title={mikMati ? t("chat_ui.call.mic_on") : t("chat_ui.call.mic_off")}
              className="flex size-12 items-center justify-center rounded-control bg-white/15 text-white hover:bg-white/25"
            >
              {mikMati ? <MicOff className="size-5" /> : <Mic className="size-5" />}
            </button>
            {pakaiVideo ? (
              <button
                type="button"
                onClick={() => onSetelKamera(!kameraMati)}
                aria-label={t("chat_ui.call.camera_label")}
                aria-pressed={!kameraMati}
                title={kameraMati ? t("chat_ui.call.camera_on") : t("chat_ui.call.camera_off")}
                className="flex size-12 items-center justify-center rounded-control bg-white/15 text-white hover:bg-white/25"
              >
                {kameraMati ? <VideoOff className="size-5" /> : <Video className="size-5" />}
              </button>
            ) : null}
            <button
              ref={tombolUtamaRef}
              type="button"
              onClick={onTutup}
              aria-label={t("chat_ui.call.end")}
              className="bg-red-600 hover:bg-red-700 flex size-14 items-center justify-center rounded-control text-white"
            >
              <PhoneOff className="size-6" />
            </button>
          </>
        )}
      </div>
    </div>
  );
}
