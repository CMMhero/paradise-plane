/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: project lama -> departemen (KEP-29)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Sebelum KEP-29 tiap divisi adalah satu project. Baris di sini mengubah project
 * lama itu jadi departemen di sebuah divisi, sekaligus membawa anggotanya. Orang
 * dipilih satu per satu (default tercentang) karena pemetaan keanggotaan lama
 * harus disengaja, bukan otomatis.
 */

import { useState } from "react";
import useSWR from "swr";
// plane imports
import { Button } from "@plane/propel/button";
import { InstanceOrganisasiService, TINGKAT_DIREKTUR, type TProjectOrganisasi } from "@plane/services";
// local
import { inputClass } from "../members/constants";

const layanan = new InstanceOrganisasiService();

type Props = {
  project: TProjectOrganisasi;
  semuaDivisi: { id: string; nama: string; kode: string }[];
  onJadikan: (data: {
    project_id: string;
    divisi_id: string;
    kode: string;
    nama: string;
    member_ids: string[];
  }) => Promise<void>;
};

export function BarisProjectLama({ project, semuaDivisi, onJadikan }: Props) {
  const [terbuka, setTerbuka] = useState(false);

  return (
    <div className="rounded border border-subtle px-3 py-2">
      <div className="flex items-center gap-2">
        <span className="text-13 text-primary">{project.name}</span>
        <span className="text-11 text-tertiary">{project.identifier}</span>
        <Button
          variant="secondary"
          size="sm"
          className="ml-auto"
          disabled={semuaDivisi.length === 0}
          onClick={() => setTerbuka((t) => !t)}
        >
          {terbuka ? "Tutup" : "Jadikan departemen…"}
        </Button>
      </div>
      {terbuka && <FormJadikan project={project} semuaDivisi={semuaDivisi} onJadikan={onJadikan} />}
    </div>
  );
}

function FormJadikan({ project, semuaDivisi, onJadikan }: Props) {
  const { data } = useSWR(`ANGGOTA_PROJECT_LAMA_${project.id}`, () => layanan.anggotaProject(project.id));
  const [divisiId, setDivisiId] = useState(semuaDivisi[0]?.id ?? "");
  const [kode, setKode] = useState(project.identifier);
  const [nama, setNama] = useState(project.name);
  // null = belum disentuh: semua yang bisa ditempatkan dianggap tercentang.
  const [dipilih, setDipilih] = useState<Set<string> | null>(null);
  const [sibuk, setSibuk] = useState(false);

  const bisa = (data?.anggota ?? []).filter((a) => a.bisa_ditempatkan);
  const terpilih = dipilih ?? new Set(bisa.map((a) => a.id));
  const ganti = (id: string) => {
    const baru = new Set(terpilih);
    if (baru.has(id)) baru.delete(id);
    else baru.add(id);
    setDipilih(baru);
  };

  return (
    <div className="mt-2 space-y-2 border-t border-subtle pt-2">
      <div className="flex flex-wrap items-center gap-2">
        <select
          className={`${inputClass} min-w-[160px]`}
          value={divisiId}
          onChange={(e) => setDivisiId(e.target.value)}
        >
          {semuaDivisi.map((v) => (
            <option key={v.id} value={v.id}>
              Divisi: {v.nama}
            </option>
          ))}
        </select>
        <input className={`${inputClass} w-28`} maxLength={20} value={kode} onChange={(e) => setKode(e.target.value)} />
        <input
          className={`${inputClass} min-w-[160px] flex-1`}
          value={nama}
          onChange={(e) => setNama(e.target.value)}
        />
      </div>

      <span className="block text-11 text-secondary">
        Bawa anggota project ini ke departemen ({terpilih.size} dari {bisa.length})
      </span>
      {!data ? (
        <p className="text-11 text-tertiary">Memuat anggota…</p>
      ) : (
        <div className="grid gap-1 sm:grid-cols-2">
          {data.anggota.map((a) => (
            <label
              key={a.id}
              className={`flex items-center gap-2 text-11 ${a.bisa_ditempatkan ? "text-primary" : "text-tertiary"}`}
              title={a.email}
            >
              <input
                type="checkbox"
                disabled={!a.bisa_ditempatkan}
                checked={a.bisa_ditempatkan && terpilih.has(a.id)}
                onChange={() => ganti(a.id)}
              />
              <span className="truncate">
                {a.nama} · {a.tingkat_nama ?? "belum berjenjang, jadi Staf"}
                {!a.bisa_ditempatkan &&
                  ((a.tingkat ?? 0) >= TINGKAT_DIREKTUR
                    ? " (menjangkau seluruh perusahaan)"
                    : " (ditempatkan lewat divisi)")}
                {a.bisa_ditempatkan && a.departemen && ` · pindah dari ${a.departemen}`}
              </span>
            </label>
          ))}
        </div>
      )}

      <div className="flex items-center gap-2">
        <Button
          variant="primary"
          size="sm"
          disabled={sibuk || !divisiId || !kode.trim() || !nama.trim() || !data}
          onClick={async () => {
            setSibuk(true);
            await onJadikan({
              project_id: project.id,
              divisi_id: divisiId,
              kode: kode.trim(),
              nama: nama.trim(),
              member_ids: [...terpilih],
            });
            setSibuk(false);
          }}
        >
          Jadikan departemen
        </Button>
        <span className="text-11 text-tertiary">
          Yang tidak dicentang tetap anggota project sebagai pengecualian, tanpa penempatan.
        </span>
      </div>
    </div>
  );
}
