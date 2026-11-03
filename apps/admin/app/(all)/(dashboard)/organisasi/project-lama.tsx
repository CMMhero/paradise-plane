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
import { FolderKanban } from "lucide-react";
import useSWR from "swr";
// plane imports
import { Button } from "@plane/propel/button";
import { InstanceOrganisasiService, TINGKAT_DIREKTUR, type TProjectOrganisasi } from "@plane/services";
import { Checkbox, CustomSelect, Input, Loader } from "@plane/ui";
// components
import { Field, PersonCell } from "@/components/common/paradise-ui";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { BadgeJabatan } from "../members/jabatan";

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
  const { s } = useGodmodeStrings();
  const [terbuka, setTerbuka] = useState(false);

  return (
    <li className="px-4 py-3">
      <div className="flex items-center gap-3">
        <span className="grid size-8 shrink-0 place-items-center rounded-item border border-subtle bg-layer-2 text-tertiary">
          <FolderKanban className="size-4" aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          <div className="truncate text-13 font-medium text-primary">{project.name}</div>
          <div className="text-11 text-tertiary">{project.identifier}</div>
        </div>
        <Button
          variant={terbuka ? "ghost" : "secondary"}
          size="base"
          disabled={semuaDivisi.length === 0}
          onClick={() => setTerbuka((t) => !t)}
        >
          {terbuka ? s.org.legacy_close : s.org.legacy_convert}
        </Button>
      </div>
      {terbuka && <FormJadikan project={project} semuaDivisi={semuaDivisi} onJadikan={onJadikan} />}
    </li>
  );
}

function FormJadikan({ project, semuaDivisi, onJadikan }: Props) {
  const { s, fill } = useGodmodeStrings();
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
    <div className="mt-3 space-y-4 rounded-card border border-subtle bg-surface-1 p-4">
      <div className="grid gap-4 sm:grid-cols-[1fr_8rem_1fr]">
        <Field label={s.org.division_of}>
          <CustomSelect
            value={divisiId}
            label={semuaDivisi.find((v) => v.id === divisiId)?.nama}
            onChange={(v: string) => setDivisiId(v)}
            buttonClassName="w-full"
            className="w-full"
            input
          >
            {semuaDivisi.map((v) => (
              <CustomSelect.Option key={v.id} value={v.id}>
                {v.nama}
              </CustomSelect.Option>
            ))}
          </CustomSelect>
        </Field>
        <Field label={s.org.code}>
          <Input className="w-full" maxLength={20} value={kode} onChange={(e) => setKode(e.target.value)} />
        </Field>
        <Field label={s.org.name}>
          <Input className="w-full" value={nama} onChange={(e) => setNama(e.target.value)} />
        </Field>
      </div>

      <div className="space-y-2">
        <span className="block text-12 font-medium text-secondary">
          {fill(s.org.legacy_bring, { a: terpilih.size, b: bisa.length })}
        </span>
        {!data ? (
          <Loader className="space-y-1.5">
            <Loader.Item height="36px" />
            <Loader.Item height="36px" />
          </Loader>
        ) : (
          <ul className="grid gap-1 sm:grid-cols-2">
            {data.anggota.map((a) => {
              const alasan = !a.bisa_ditempatkan
                ? (a.tingkat ?? 0) >= TINGKAT_DIREKTUR
                  ? s.org.legacy_director_reach
                  : s.org.legacy_division_placed
                : a.departemen
                  ? fill(s.org.moved_from_bare, { from: a.departemen })
                  : "";
              return (
                <li key={a.id}>
                  <label
                    htmlFor={`lama-${project.id}-${a.id}`}
                    className={`flex items-center gap-3 rounded-item px-2 py-1.5 ${
                      a.bisa_ditempatkan ? "cursor-pointer hover:bg-layer-1-hover" : "opacity-60"
                    }`}
                  >
                    <Checkbox
                      id={`lama-${project.id}-${a.id}`}
                      disabled={!a.bisa_ditempatkan}
                      checked={a.bisa_ditempatkan && terpilih.has(a.id)}
                      onChange={() => ganti(a.id)}
                    />
                    <div className="min-w-0 flex-1">
                      <PersonCell name={a.nama} email={alasan.trim() || a.email} size="sm" />
                    </div>
                    <BadgeJabatan tingkat={a.tingkat} size="sm" />
                  </label>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-subtle pt-3">
        <span className="text-11 text-tertiary">{s.org.legacy_kept_note}</span>
        <Button
          variant="primary"
          size="base"
          loading={sibuk}
          disabled={!divisiId || !kode.trim() || !nama.trim() || !data}
          onClick={async () => {
            setSibuk(true);
            try {
              await onJadikan({
                project_id: project.id,
                divisi_id: divisiId,
                kode: kode.trim(),
                nama: nama.trim(),
                member_ids: [...terpilih],
              });
            } finally {
              setSibuk(false);
            }
          }}
        >
          {s.org.legacy_make}
        </Button>
      </div>
    </div>
  );
}
