/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: grafik login harian
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
// local
import { SERI } from "./constants";

type Titik = { tgl: string; login: number; orang: number };

type Props = {
  /** Terurut naik menurut tanggal dari server. */
  harian: Titik[];
};

const W = 720;
const H = 200;
const PAD = { atas: 12, kanan: 12, bawah: 24, kiri: 32 };

function tanggalPendek(iso: string) {
  const d = new Date(`${iso}T00:00:00`);
  return d.toLocaleDateString("id-ID", { day: "2-digit", month: "short" });
}

/**
 * Dua garis pada SATU sumbu, keduanya hitungan orang/peristiwa, jadi skalanya
 * sebanding. Sengaja BUKAN dua sumbu-y: grafik dua sumbu bisa dibuat menunjukkan
 * korelasi apa pun hanya dengan menggeser salah satu skalanya.
 *
 * SVG murni, tanpa pustaka grafik, dua garis tidak sebanding dengan menambah
 * dependensi ke bundle God Mode.
 */
export function GrafikHarian({ harian }: Props) {
  const [aktif, setAktif] = useState<number | null>(null);

  const titik = harian;

  if (titik.length === 0) {
    return (
      <div className="rounded border border-subtle p-8 text-center text-body-sm-regular text-secondary">
        Belum ada login yang tercatat pada rentang ini.
        <div className="mt-1 text-11 text-placeholder">
          Riwayat baru direkam sejak fitur ini dipasang, hari sebelumnya memang kosong, bukan sepi.
        </div>
      </div>
    );
  }

  const maks = Math.max(...titik.map((t) => Math.max(t.login, t.orang)), 1);
  const lebarPlot = W - PAD.kiri - PAD.kanan;
  const tinggiPlot = H - PAD.atas - PAD.bawah;
  const x = (i: number) => PAD.kiri + (titik.length === 1 ? lebarPlot / 2 : (i / (titik.length - 1)) * lebarPlot);
  const y = (n: number) => PAD.atas + tinggiPlot - (n / maks) * tinggiPlot;
  const garis = (ambil: (t: Titik) => number) =>
    titik.map((t, i) => `${i === 0 ? "M" : "L"}${x(i)},${y(ambil(t))}`).join(" ");

  // Empat garis bantu saja, grid yang rapat bersaing dengan datanya sendiri.
  const tanda = [0, 0.25, 0.5, 0.75, 1].map((f) => ({ f, n: Math.round(maks * f) }));
  const t = aktif !== null ? titik[aktif] : null;

  return (
    <div className="rounded border border-subtle p-3">
      {/* Legenda selalu ada untuk 2 seri, identitas tidak boleh bersandar pada warna saja. */}
      <div className="mb-2 flex items-center gap-4 px-1">
        {(["login", "orang"] as const).map((k) => (
          <span key={k} className="flex items-center gap-1.5 text-11 text-secondary">
            <span className="size-2 rounded-full" style={{ background: `var(--seri-${k})` }} aria-hidden />
            {SERI[k].label}
          </span>
        ))}
        <span className="ml-auto text-11 text-placeholder">maks {maks}/hari</span>
      </div>

      <style>{`
        .grafik-aktivitas { --seri-login: ${SERI.login.terang}; --seri-orang: ${SERI.orang.terang}; }
        @media (prefers-color-scheme: dark) {
          :root:where(:not([data-theme="light"])) .grafik-aktivitas {
            --seri-login: ${SERI.login.gelap}; --seri-orang: ${SERI.orang.gelap};
          }
        }
        :root[data-theme="dark"] .grafik-aktivitas {
          --seri-login: ${SERI.login.gelap}; --seri-orang: ${SERI.orang.gelap};
        }
      `}</style>

      <div className="grafik-aktivitas relative">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="w-full"
          role="img"
          aria-label={`Login harian, ${titik.length} hari, puncak ${maks} login per hari`}
          onMouseLeave={() => setAktif(null)}
        >
          {tanda.map(({ f, n }) => (
            <g key={f}>
              <line x1={PAD.kiri} x2={W - PAD.kanan} y1={y(n)} y2={y(n)} className="stroke-subtle" strokeWidth={1} />
              <text x={PAD.kiri - 6} y={y(n) + 3} textAnchor="end" className="fill-placeholder text-[9px]">
                {n}
              </text>
            </g>
          ))}

          <path
            d={garis((p) => p.login)}
            fill="none"
            stroke="var(--seri-login)"
            strokeWidth={2}
            strokeLinejoin="round"
          />
          <path
            d={garis((p) => p.orang)}
            fill="none"
            stroke="var(--seri-orang)"
            strokeWidth={2}
            strokeLinejoin="round"
          />

          {aktif !== null ? (
            <line
              x1={x(aktif)}
              x2={x(aktif)}
              y1={PAD.atas}
              y2={H - PAD.bawah}
              className="stroke-subtle"
              strokeWidth={1}
            />
          ) : null}

          {titik.map((p, i) => (
            <g key={p.tgl}>
              {aktif === i ? (
                <>
                  <circle
                    cx={x(i)}
                    cy={y(p.login)}
                    r={4}
                    fill="var(--seri-login)"
                    stroke="var(--color-layer-1, #fff)"
                    strokeWidth={2}
                  />
                  <circle
                    cx={x(i)}
                    cy={y(p.orang)}
                    r={4}
                    fill="var(--seri-orang)"
                    stroke="var(--color-layer-1, #fff)"
                    strokeWidth={2}
                  />
                </>
              ) : null}
              {/* Pita tak terlihat: sasaran hover harus lebih besar dari titiknya. */}
              <rect
                x={x(i) - lebarPlot / titik.length / 2}
                y={PAD.atas}
                width={Math.max(6, lebarPlot / titik.length)}
                height={tinggiPlot}
                fill="transparent"
                onMouseEnter={() => setAktif(i)}
              />
            </g>
          ))}

          <text x={PAD.kiri} y={H - 6} className="fill-placeholder text-[9px]">
            {tanggalPendek(titik[0].tgl)}
          </text>
          <text x={W - PAD.kanan} y={H - 6} textAnchor="end" className="fill-placeholder text-[9px]">
            {tanggalPendek(titik[titik.length - 1].tgl)}
          </text>
        </svg>

        {t ? (
          <div
            className="shadow-sm pointer-events-none absolute top-0 rounded border border-subtle bg-layer-1 px-2 py-1 text-11"
            style={{ left: `${(x(aktif ?? 0) / W) * 100}%`, transform: "translateX(-50%)" }}
          >
            <div className="font-medium text-primary">{tanggalPendek(t.tgl)}</div>
            <div className="text-secondary">
              {t.login} login · {t.orang} orang
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
