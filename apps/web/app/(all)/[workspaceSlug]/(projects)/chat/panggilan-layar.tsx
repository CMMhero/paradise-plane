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

type Props = {
  status: TStatusPanggilan;
  koneksi: string;
  judul: string;
  pakaiVideo: boolean;
  mikMati: boolean;
  kameraMati: boolean;
  streamLokal: MediaStream | null;
  pesertaJauh: TPesertaJauh[];
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
    if (!el || el.srcObject === stream) return;
    el.srcObject = stream;
    // Kebijakan autoplay bisa menolak pemutaran tanpa gestur. Panggilan selalu
    // dimulai dari klik jadi normalnya lolos; ditangkap supaya penolakannya
    // tidak jatuh sebagai unhandled rejection yang tak terlihat.
    void el.play().catch(() => undefined);
  }, [stream]);

  // eslint-disable-next-line jsx-a11y/media-has-caption
  return <video ref={ref} autoPlay playsInline muted={bisu} className={className} />;
}

/** Satu kotak peserta: gambarnya kalau ada, avatar kalau hanya suara. */
function Peserta({ peserta }: { peserta: TPesertaJauh }) {
  return (
    <div className="relative flex min-h-0 items-center justify-center overflow-hidden rounded-lg bg-black/60">
      {/* Elemen media SELALU terpasang, juga saat peserta hanya mengirim suara.
          Kalau ia ikut dirender bersyarat, audionya tidak punya tempat keluar. */}
      <Media stream={peserta.stream} className={peserta.adaVideo ? "h-full w-full object-contain" : "hidden"} />
      {!peserta.adaVideo ? <Avatar name={peserta.nama} size={64} shape="circle" /> : null}
      <span className="text-xs absolute bottom-2 left-2 rounded bg-black/60 px-1.5 py-0.5 text-white/90">
        {peserta.nama}
      </span>
    </div>
  );
}

export function PanggilanLayar({
  status,
  koneksi,
  judul,
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
  if (!tata.tampil) return null;

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
    <div className="fixed inset-0 z-40 flex flex-col items-center justify-center bg-black/85 p-3 sm:p-6">
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
              <Peserta key={p.id} peserta={p} />
            ))}
          </div>
        ) : (
          <Avatar name={judul} size={80} shape="circle" />
        )}

        {/* Pratinjau diri tampil SEJAK MEMANGGIL, bukan setelah tersambung.
            Kalau kameranya bermasalah, orang tahu sejak detik pertama alih-alih
            menunggu panggilan yang memang tidak akan menampilkan apa pun.
            Selalu dibisukan supaya suara sendiri tidak menggema. */}
        {tata.pratinjauDiriTerlihat ? (
          <Media
            stream={streamLokal}
            bisu
            className="shadow-lg absolute right-2 bottom-2 w-24 rounded-md border border-white/20 bg-black object-cover sm:right-3 sm:bottom-3 sm:w-32"
          />
        ) : null}
      </div>

      <p className="text-lg mt-5 font-medium text-white">{judul}</p>
      <p className="text-sm mt-1 text-white/60">{keterangan}</p>
      {/* Angka byte adalah SATU-SATUNYA bukti media benar-benar mengalir. Status
          koneksi, track yang tiba, bahkan tulisan "Tersambung" semuanya bisa
          terlihat benar sementara nol byte berpindah. */}
      <p className="text-xs mt-1 text-white/35">
        {koneksi}
        {streamLokal ? ` · ${t("chat_ui.call.mic_ready")}` : ` · ${t("chat_ui.call.mic_not_ready")}`}
        {` · ${t("chat_ui.call.incoming")} `}
        {Math.round(byteMasuk.audio / 1024)} {t("chat_ui.call.kb_audio")} / {Math.round(byteMasuk.video / 1024)}{" "}
        {t("chat_ui.call.kb_video")}
      </p>
      {status === "tersambung" && byteMasuk.audio === 0 && byteMasuk.video === 0 ? (
        <p className="text-xs text-amber-300/80 mt-2 max-w-md text-center">{t("chat_ui.call.no_data")}</p>
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
              className="bg-green-600 hover:bg-green-500 flex size-14 items-center justify-center rounded-full text-white"
            >
              <Phone className="size-6" />
            </button>
            <button
              type="button"
              onClick={onTutup}
              aria-label={t("chat_ui.call.decline")}
              className="bg-red-600 hover:bg-red-500 flex size-14 items-center justify-center rounded-full text-white"
            >
              <PhoneOff className="size-6" />
            </button>
          </>
        ) : (
          <>
            <button
              type="button"
              onClick={() => onSetelMik(!mikMati)}
              aria-label={mikMati ? t("chat_ui.call.mic_on") : t("chat_ui.call.mic_off")}
              className="flex size-12 items-center justify-center rounded-full bg-white/15 text-white hover:bg-white/25"
            >
              {mikMati ? <MicOff className="size-5" /> : <Mic className="size-5" />}
            </button>
            {pakaiVideo ? (
              <button
                type="button"
                onClick={() => onSetelKamera(!kameraMati)}
                aria-label={kameraMati ? t("chat_ui.call.camera_on") : t("chat_ui.call.camera_off")}
                className="flex size-12 items-center justify-center rounded-full bg-white/15 text-white hover:bg-white/25"
              >
                {kameraMati ? <VideoOff className="size-5" /> : <Video className="size-5" />}
              </button>
            ) : null}
            <button
              type="button"
              onClick={onTutup}
              aria-label={t("chat_ui.call.end")}
              className="bg-red-600 hover:bg-red-500 flex size-14 items-center justify-center rounded-full text-white"
            >
              <PhoneOff className="size-6" />
            </button>
          </>
        )}
      </div>
    </div>
  );
}
