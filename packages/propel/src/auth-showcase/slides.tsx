/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: gambar aplikasi di panel layar masuk
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Empat potongan aplikasi yang digambar ulang: papan project, dashboard divisi,
 * detail tugas, dan chat. Ini GAMBAR (aria-hidden), bukan data: isinya data demo
 * project Marketing dan Promosi dari `seed_demo_data`, disederhanakan supaya muat
 * di panel sempit. Label antarmuka sengaja English, sama dengan bawaan aplikasi.
 * Kalau tampilan aslinya berubah (kolom papan, chip Approved, kartu dashboard),
 * samakan gambarnya juga.
 */

import * as React from "react";
import { cn } from "../utils";

// ---------- potongan kecil yang dipakai bersama ----------

function Jendela({ judul, keterangan, children }: { judul: string; keterangan?: string; children: React.ReactNode }) {
  return (
    <div className="w-full max-w-[500px] overflow-hidden rounded-card border border-white/15 bg-pamer-latar text-12 leading-snug text-pamer-teks pamer-jendela">
      <div className="flex items-center gap-2 border-b border-pamer-batas bg-pamer-bilah px-3.5 py-2.5 whitespace-nowrap">
        <span className="mr-1 flex gap-1.5">
          <i className="size-2 rounded-full bg-pamer-lampu" />
          <i className="size-2 rounded-full bg-pamer-lampu" />
          <i className="size-2 rounded-full bg-pamer-lampu" />
        </span>
        <b className="font-semibold">{judul}</b>
        {keterangan && <span className="truncate text-pamer-teks-3">{keterangan}</span>}
      </div>
      {children}
    </div>
  );
}

function Pil({ nada = "biasa", children }: { nada?: "biasa" | "telat" | "setuju"; children: React.ReactNode }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-control border px-1 py-px text-10 whitespace-nowrap",
        nada === "biasa" && "border-pamer-batas text-pamer-teks-2",
        nada === "telat" && "border-pamer-batas text-pamer-merah",
        nada === "setuju" && "border-pamer-hijau-batas bg-pamer-hijau-latar text-pamer-hijau-teks"
      )}
    >
      {children}
    </span>
  );
}

function Avatar({ inisial }: { inisial: string }) {
  return (
    <span className="inline-grid size-[18px] shrink-0 place-items-center rounded-full border-[1.5px] border-pamer-latar bg-pamer-teal text-9 font-semibold text-white">
      {inisial}
    </span>
  );
}

type TStatus = "todo" | "jalan" | "selesai";

function IkonStatus({ status }: { status: TStatus }) {
  return (
    <span
      className={cn(
        "size-[9px] shrink-0 rounded-full border-[1.5px]",
        status === "todo" && "border-current",
        status === "jalan" && "border-2 border-pamer-jingga",
        status === "selesai" && "border-pamer-hijau bg-pamer-hijau"
      )}
    />
  );
}

// ---------- 1. papan project ----------

type TKartu = { id: number; judul: string; tanggal?: string; telat?: boolean; orang?: string; disetujui?: boolean };

const KOLOM: { status: TStatus; nama: string; jumlah: number; kartu: TKartu[] }[] = [
  {
    status: "todo",
    nama: "Todo",
    jumlah: 10,
    kartu: [
      { id: 17, judul: "Koordinasi dengan tim IT", tanggal: "Oct 28 - Nov 26", orang: "R" },
      { id: 16, judul: "Wireframe halaman", tanggal: "Oct 26 - Nov 16", orang: "R" },
    ],
  },
  {
    status: "jalan",
    nama: "In Progress",
    jumlah: 2,
    kartu: [
      { id: 8, judul: "Laporan performa iklan digital Oktober", tanggal: "Oct 21 - Nov 24", orang: "N" },
      { id: 19, judul: "Atur ulang hak akses Marketing", tanggal: "Oct 14 - Nov 25", orang: "M" },
    ],
  },
  {
    status: "selesai",
    nama: "Done",
    jumlah: 5,
    kartu: [
      { id: 14, judul: "Olah hasil survei", disetujui: true },
      { id: 12, judul: "Riset kepuasan pelanggan 2026", disetujui: true },
    ],
  },
];

export function SlidePapan() {
  return (
    <Jendela judul="Marketing dan Promosi">
      <div className="grid grid-cols-3 gap-2.5 bg-pamer-papan p-3.5 text-11">
        {KOLOM.map((kolom) => (
          <div key={kolom.nama} className="min-w-0">
            <div className="mb-2 ml-0.5 flex items-center gap-1.5 font-medium whitespace-nowrap">
              <IkonStatus status={kolom.status} />
              {kolom.nama}
              <span className="font-normal text-pamer-teks-3">{kolom.jumlah}</span>
            </div>
            {kolom.kartu.map((kartu) => (
              <div key={kartu.id} className="mb-2 rounded-item border border-pamer-batas bg-pamer-latar p-2">
                <div className="text-10 text-pamer-teks-3">MKT-{kartu.id}</div>
                <div className="mt-0.5 mb-2 line-clamp-2 font-medium">{kartu.judul}</div>
                <div className="flex flex-col items-start gap-1.5">
                  {kartu.disetujui ? (
                    <Pil nada="setuju">✓ Approved</Pil>
                  ) : (
                    <Pil nada={kartu.telat ? "telat" : "biasa"}>{kartu.tanggal}</Pil>
                  )}
                  {kartu.orang && <Avatar inisial={kartu.orang} />}
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </Jendela>
  );
}

// ---------- 2. dashboard divisi ----------

function KartuDivisi({ nama, persen, telat }: { nama: string; persen: number; telat: number }) {
  const kritis = telat > 0;
  return (
    <div className="rounded-item border border-pamer-batas px-3 py-2.5">
      <div className="flex items-center justify-between font-medium">
        {nama}
        {kritis ? (
          <span className="text-11 font-medium text-pamer-merah">Critical</span>
        ) : (
          <span className="rounded-control bg-pamer-hijau-latar px-1.5 text-11 text-pamer-hijau-teks">On track</span>
        )}
      </div>
      <div className="mt-2.5 mb-1.5 h-[5px] overflow-hidden rounded-full bg-pamer-lapis">
        <i
          className={cn("block h-full rounded-full", kritis ? "bg-pamer-merah" : "bg-pamer-hijau")}
          style={{ width: `${persen}%` }}
        />
      </div>
      <div className="flex justify-between text-11 text-pamer-teks-2">
        <span>{persen}% done</span>
        <span className={cn(kritis && "text-pamer-merah")}>Overdue: {telat}</span>
      </div>
    </div>
  );
}

const ANGKA = [
  { nilai: "100%", label: "Done on time" },
  { nilai: "3", label: "Completed this week" },
  { nilai: "5", label: "Overdue now", telat: true },
];

export function SlideDashboard() {
  return (
    <Jendela judul="Division Dashboard">
      <div className="grid gap-2.5 p-4">
        <div className="grid grid-cols-3 gap-2.5">
          {ANGKA.map((angka) => (
            <div key={angka.label} className="rounded-item border border-pamer-batas px-3 py-2.5">
              <div className={cn("text-20 font-medium tracking-tight", angka.telat && "text-pamer-merah")}>
                {angka.nilai}
              </div>
              <div className="mt-0.5 text-11 text-pamer-teks-2">{angka.label}</div>
            </div>
          ))}
        </div>
        <KartuDivisi nama="Sales & Marketing" persen={26} telat={5} />
        <KartuDivisi nama="Operasional" persen={68} telat={0} />
      </div>
    </Jendela>
  );
}

// ---------- 3. detail tugas ----------

function Bagian({ judul, keterangan }: { judul: string; keterangan: string }) {
  return (
    <div className="flex justify-between border-b border-pamer-batas pt-2.5 pb-1.5 font-medium">
      {judul}
      <span className="font-normal text-pamer-teks-3">{keterangan}</span>
    </div>
  );
}

function Baris({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 border-b border-pamer-batas py-1.5 pl-1 last:border-b-0 last:pb-0">
      {children}
    </div>
  );
}

export function SlideTugas() {
  return (
    <Jendela judul="MKT-9" keterangan="Marketing dan Promosi">
      <div className="p-4">
        <div className="text-16 font-medium tracking-tight">Sponsorship seminar industri</div>
        <div className="mt-2.5 mb-1.5 flex items-center gap-1.5">
          <Pil>
            <IkonStatus status="todo" />
            Todo
          </Pil>
          <Pil nada="telat">Due Oct 29</Pil>
          <span className="inline-flex [&>*+*]:-ml-1.5">
            <Avatar inisial="T" />
            <Avatar inisial="R" />
          </span>
        </div>
        <Bagian judul="Sub-work items" keterangan="0/2 Done" />
        <Baris>
          <IkonStatus status="todo" />
          <span className="flex-1 truncate">Negosiasi paket sponsor</span>
          <Avatar inisial="T" />
        </Baris>
        <Baris>
          <IkonStatus status="todo" />
          <span className="flex-1 truncate">Siapkan merchandise</span>
          <Avatar inisial="N" />
        </Baris>
        <Bagian judul="Attachments" keterangan="1" />
        <Baris>
          <span className="flex-1 truncate">mkt-9-grafik.png</span>
          <span className="text-pamer-teks-3">1 KB</span>
        </Baris>
      </div>
    </Jendela>
  );
}

// ---------- 4. chat ----------

const PESAN = [
  { inisial: "B", nama: "Bambang", isi: "Tim, tolong cek tugas yang lewat tenggat hari ini.", jam: "15:32" },
  { inisial: "R", nama: "Reza", isi: "Siap, saya rekap dan kabari sore ini.", jam: "17:15" },
  { inisial: "T", nama: "Tania", isi: "Tinggal satu, menunggu data dari divisi lain.", jam: "17:29" },
];

export function SlideChat() {
  return (
    <Jendela judul="Chat" keterangan="Divisi Sales & Marketing">
      <div className="flex flex-col gap-2.5 p-4">
        {PESAN.map((pesan) => (
          <div key={pesan.jam} className="flex items-end gap-2">
            <Avatar inisial={pesan.inisial} />
            <div className="max-w-[80%] rounded-card bg-pamer-lapis px-2.5 py-1.5">
              <div className="text-11 font-semibold">{pesan.nama}</div>
              {pesan.isi}
              <div className="mt-0.5 text-10 text-pamer-teks-3">{pesan.jam}</div>
            </div>
          </div>
        ))}
        <div className="mt-1 flex items-center gap-2">
          <span className="flex-1 rounded-field border border-pamer-batas px-2.5 py-1.5 text-pamer-teks-3">
            Write a message
          </span>
          <span className="grid size-[30px] shrink-0 place-items-center rounded-button bg-pamer-merah text-white">
            ➤
          </span>
        </div>
      </div>
    </Jendela>
  );
}
