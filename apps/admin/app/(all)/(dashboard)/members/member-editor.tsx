/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: editor member terpadu God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Satu panel, satu tombol Simpan, untuk semua sumbu orang ini:
 * - Data akun (nama, email, hak akses workspace, password) — PATCH members.
 * - Jabatan organisasi + "divisi yang dia bawahi" — POST hierarki.
 * - Divisi tempat ia anggota — POST divisi-anggota (atomik).
 *
 * Tiga panggilan berurutan, berhenti di yang pertama gagal supaya tidak ada
 * keadaan setengah jadi. Gaya mengikuti EditMember (yang digantikan berkas ini):
 * `space-y-3 border-t border-subtle bg-layer-1 p-4`, label `text-11`, catatan
 * `text-11 text-secondary`, tombol Simpan/Batal yang sama.
 *
 * Peran divisi DITURUNKAN dari jabatan, bukan dipilih: manager/supervisor =
 * Admin divisi (20), member/belum-diisi = Member (15). Keputusan user 2026-10-16.
 */

import { useEffect, useState } from "react";
import { ShieldCheck, Trash2 } from "lucide-react";
// plane imports
import { Button } from "@plane/propel/button";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
import {
  InstanceDivisiMemberService,
  InstanceHierarkiService,
  InstanceMemberService,
  InstanceWorkspaceService,
  TINGKAT_DIREKTUR,
  TINGKAT_MANAGER,
  TINGKAT_MEMBER,
  TINGKAT_SUPERVISOR,
  type TInstanceMember,
  type TMemberUpdate,
  type TPilihanDepartemen,
  type TPilihanDivisi,
} from "@plane/services";
// local
import { cocokKonfirmasiGrant, useGodmodeStrings, type TGodmodeStrings } from "@/app/i18n/godmode";
import { inputClass, PERAN_DEFAULT } from "./constants";
import { DivisiPicker } from "./divisi-picker";

const memberService = new InstanceMemberService();
const hierarkiService = new InstanceHierarkiService();
const divisiService = new InstanceDivisiMemberService();
const workspaceService = new InstanceWorkspaceService();

/** Nilai dikirim ke backend. Tanpa "belum diisi": jabatan kosong = staf. */
const pilihanTingkat = (s: TGodmodeStrings): { value: string; label: string }[] => [
  { value: String(TINGKAT_MEMBER), label: s.editor.position_member },
  { value: String(TINGKAT_SUPERVISOR), label: s.editor.position_supervisor },
  { value: String(TINGKAT_MANAGER), label: s.editor.position_manager },
  { value: String(TINGKAT_DIREKTUR), label: s.editor.position_director },
];

/** Peran project dari jabatan. Bukan pilihan — turunan aturan. */
const peranDivisi = (tingkat: number | null): number => (tingkat !== null && tingkat >= TINGKAT_SUPERVISOR ? 20 : 15);

const pesanGagal = (err: unknown, fallback: string): string => {
  const pesan = (err as { error?: string } | undefined)?.error;
  return typeof pesan === "string" && pesan.length > 0 ? pesan : fallback;
};

type Props = {
  member: TInstanceMember;
  /** Undefined kalau bukan anggota workspace — jabatan/divisi nonaktif. */
  hierarki:
    | {
        tingkat: number | null;
        divisi: string[];
        divisi_diawasi: string[];
        departemen_id?: string | null;
        divisi_id?: string | null;
      }
    | undefined;
  /** Pilihan penempatan KEP-29. Kosong = workspace belum memakai struktur divisi/departemen. */
  pilihanDepartemen?: TPilihanDepartemen[];
  pilihanDivisi?: TPilihanDivisi[];
  /** Identifier divisi (urutan backend). */
  daftarDivisi: string[];
  /** Identifier → UUID project. */
  petaDivisi: Record<string, string>;
  /** Identifier → nama tampil ("ACC" → "Accounting"). Aditif, boleh kosong. */
  namaDivisi?: Record<string, string>;
  onSelesai: () => Promise<unknown>;
  onTutup: () => void;
  /** Cabut Super Admin (PATCH false). Grant ditangani internal (butuh konfirmasi ketik). */
  onCabutSuperAdmin: () => void;
  sibukSuperAdmin?: boolean;
};

export function MemberEditor({
  member,
  hierarki,
  daftarDivisi,
  petaDivisi,
  namaDivisi = {},
  pilihanDepartemen = [],
  pilihanDivisi = [],
  onSelesai,
  onTutup,
  onCabutSuperAdmin,
  sibukSuperAdmin = false,
}: Props) {
  const { s, fill } = useGodmodeStrings();
  const opsiTingkat = pilihanTingkat(s);
  // --- data akun (dari EditMember) ---
  const [nama, setNama] = useState(member.display_name);
  const [email, setEmail] = useState(member.email);
  const [peran, setPeran] = useState(member.workspace_role ?? PERAN_DEFAULT);
  const [password, setPassword] = useState("");
  // Workspace tempat ia anggota sekarang; "" = belum jadi anggota mana pun.
  const [wsSlug, setWsSlug] = useState(member.workspace_slug ?? "");
  // --- jabatan + pengawasan + divisi (initial dari hierarki kalau ada) ---
  // Jabatan kosong dianggap staf; tersimpan sebagai staf saat Simpan.
  const [tingkat, setTingkat] = useState<string>(String(hierarki?.tingkat ?? TINGKAT_MEMBER));
  const [awasi, setAwasi] = useState<string[]>(hierarki ? [...hierarki.divisi_diawasi] : []);
  const [divisi, setDivisi] = useState<string[]>(hierarki ? [...hierarki.divisi] : []);
  // Penempatan (KEP-29): "" = belum ditempatkan.
  const [departemenId, setDepartemenId] = useState(hierarki?.departemen_id ?? "");
  const [divisiId, setDivisiId] = useState(hierarki?.divisi_id ?? "");
  const [sibuk, setSibuk] = useState(false);
  const [frasa, setFrasa] = useState("");
  const [sibukGrant, setSibukGrant] = useState(false);

  // Grant Super Admin butuh konfirmasi KETIK (diperiksa server; kedua frasa
  // diterima). Revoke lewat prop dari halaman (PATCH false, tanpa konfirmasi).
  const frasaCocok = cocokKonfirmasiGrant(frasa);
  const handleGrant = async () => {
    if (!cocokKonfirmasiGrant(frasa)) return;
    setSibukGrant(true);
    try {
      await memberService.update(member.id, { is_super_admin: true, grant_confirm: frasa });
      setFrasa("");
      await onSelesai();
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: s.editor.superadmin_granted,
        message: fill(s.editor.superadmin_granted_message, { name: member.display_name }),
      });
    } catch (err) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: s.editor.grant_denied,
        message: pesanGagal(err, s.editor.grant_failed),
      });
      setFrasa("");
    } finally {
      setSibukGrant(false);
    }
  };

  const passwordTerlaluPendek = password.length > 0 && password.length < 8;

  const simpanAkun = async (): Promise<number> => {
    // Kirim HANYA yang berubah — pola EditMember: tulis-ulang email mengakhiri
    // sesi orangnya tanpa alasan.
    const patch: TMemberUpdate = {};
    if (nama.trim() && nama.trim() !== member.display_name) patch.display_name = nama.trim();
    if (email.trim().toLowerCase() !== member.email.toLowerCase()) patch.email = email.trim().toLowerCase();
    // Dua sumbu terpisah: pindah workspace tidak menunggu perannya ikut berubah.
    if (peran !== member.workspace_role) patch.workspace_role = peran;
    if (wsSlug && wsSlug !== member.workspace_slug) patch.workspace_slug = wsSlug;
    if (password) patch.password = password;
    // Konfirmasi yang sudah diketik ikut tombol Simpan, bukan hanya tombol "Beri
    // Super Admin": dulu Simpan mengabaikannya lalu menutup panel seolah sukses.
    // Tanpa konfirmasi yang cocok = 403 di depan, tak satu kolom pun tersimpan
    // (gerbang backend).
    if (frasaCocok && !member.is_super_admin) {
      patch.is_super_admin = true;
      patch.grant_confirm = frasa;
    }
    if (Object.keys(patch).length === 0) return 0;
    const hasil = await memberService.update(member.id, patch);
    setPassword("");
    setFrasa("");
    return hasil.sessions_ended ?? 0;
  };

  const handleSimpan = async () => {
    setSibuk(true);
    try {
      const sesiBerakhir = await simpanAkun();
      if (hierarki !== undefined) {
        const tingkatBaru = Number(tingkat);
        const tingkatBerubah = tingkatBaru !== hierarki.tingkat;
        const pengawasanBerubah =
          awasi.length !== hierarki.divisi_diawasi.length || awasi.some((d) => !hierarki.divisi_diawasi.includes(d));
        const divisiBerubah =
          divisi.length !== hierarki.divisi.length || divisi.some((d) => !hierarki.divisi.includes(d));
        const departemenBerubah = departemenId !== (hierarki.departemen_id ?? "");
        const divisiIdBerubah = divisiId !== (hierarki.divisi_id ?? "");
        if (tingkatBerubah || pengawasanBerubah || departemenBerubah || divisiIdBerubah) {
          // `pengawasan` hanya dikirim kalau diubah: tidak-dikirim = jangan
          // sentuh, dikirim kosong = cabut semua (kontrak endpoint). Penempatan
          // ikut panggilan yang sama: satu simpan = satu sinkron akses di server.
          await hierarkiService.setel({
            member_id: member.id,
            ...(tingkatBerubah ? { tingkat: tingkatBaru } : {}),
            ...(departemenBerubah ? { departemen_id: departemenId || null } : {}),
            ...(divisiIdBerubah ? { divisi_id: divisiId || null } : {}),
            ...(pengawasanBerubah
              ? { pengawasan: awasi.map((d) => petaDivisi[d]).filter((id): id is string => typeof id === "string") }
              : {}),
          });
        }
        if (divisiBerubah) {
          const peranTarget = peranDivisi(tingkatBaru);
          await divisiService.ganti(
            member.id,
            divisi.map((d) => ({ project_id: petaDivisi[d], role: peranTarget })).filter((b) => b.project_id)
          );
        }
      }
      await onSelesai();
      onTutup();
      const label = opsiTingkat.find((p) => p.value === tingkat)?.label ?? tingkat;
      const namaTampil = nama.trim() || member.display_name;
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: s.editor.saved_ok,
        message: sesiBerakhir
          ? fill(s.editor.saved_message_sessions, {
              name: namaTampil,
              jabatan: label,
              n: divisi.length,
              sesi: sesiBerakhir,
            })
          : fill(s.editor.saved_message, { name: namaTampil, jabatan: label, n: divisi.length }),
      });
    } catch (err) {
      // Berhenti di panggilan pertama yang gagal: tidak ada keadaan setengah
      // jadi yang diam-diam (pola lama: jabatan tersimpan, divisi 403).
      setToast({
        type: TOAST_TYPE.ERROR,
        title: s.editor.save_failed,
        message: pesanGagal(err, s.editor.save_failed_message),
      });
    } finally {
      setSibuk(false);
    }
  };

  // Pengawasan hanya punya arti untuk supervisor ke atas (calon penyetuju =
  // tingkat lebih tinggi). Untuk member/belum-diisi rumusnya sudah cukup.
  const tampilAwasi = hierarki !== undefined && Number(tingkat) >= TINGKAT_SUPERVISOR;
  const strukturAktif = pilihanDivisi.length > 0;
  const opsiAwasi = daftarDivisi.filter((d) => divisi.includes(d) || awasi.includes(d));
  const masuk = hierarki === undefined ? [] : divisi.filter((d) => !hierarki.divisi.includes(d));
  const keluar = hierarki === undefined ? [] : hierarki.divisi.filter((d) => !divisi.includes(d));

  return (
    <div className="space-y-3 border-t border-subtle bg-layer-1 px-4 py-3">
      <div className="w-full space-y-3">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <label className="space-y-1">
            <span className="block text-11 text-secondary">{s.editor.name}</span>
            <input className={`${inputClass} w-full`} value={nama} onChange={(e) => setNama(e.target.value)} />
          </label>

          <label className="space-y-1">
            <span className="block text-11 text-secondary">{s.editor.email}</span>
            <input
              className={`${inputClass} w-full`}
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>

          <div className="space-y-1">
            <span className="block text-11 text-secondary">{s.editor.workspace}</span>
            <PemilihWorkspace nilai={wsSlug} onUbah={setWsSlug} />
          </div>

          <label className="space-y-1">
            <span className="block text-11 text-secondary">{s.editor.workspace_role}</span>
            <select className={`${inputClass} w-full`} value={peran} onChange={(e) => setPeran(Number(e.target.value))}>
              <option value={20}>{s.members.role_admin}</option>
              <option value={15}>{s.members.role_member}</option>
              <option value={5}>{s.members.role_guest}</option>
            </select>
          </label>

          <label className="space-y-1">
            <span className="block text-11 text-secondary">{s.editor.new_password}</span>
            <input
              className={`${inputClass} w-full`}
              type="password"
              autoComplete="new-password"
              placeholder={s.editor.password_hint}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
        </div>

        {passwordTerlaluPendek && <p className="text-danger text-11">{s.editor.password_too_short}</p>}

        <div className="grid gap-3 sm:grid-cols-3">
          <label className="space-y-1">
            <span className="block text-11 text-secondary">{s.editor.position}</span>
            <select
              className={`${inputClass} w-full`}
              value={tingkat}
              onChange={(e) => setTingkat(e.target.value)}
              disabled={hierarki === undefined}
            >
              {opsiTingkat.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>

          {strukturAktif && hierarki !== undefined && (
            <Penempatan
              tingkat={Number(tingkat)}
              departemenId={departemenId}
              divisiId={divisiId}
              onDepartemen={setDepartemenId}
              onDivisi={setDivisiId}
              pilihanDepartemen={pilihanDepartemen}
              pilihanDivisi={pilihanDivisi}
            />
          )}

          <div className={strukturAktif ? "space-y-1 sm:col-span-3" : "space-y-1 sm:col-span-2"}>
            <span className="block text-11 text-secondary">
              {strukturAktif
                ? fill(s.editor.extra_projects, { n: divisi.length })
                : fill(s.editor.divisions, { n: divisi.length })}
            </span>
            {hierarki === undefined ? (
              <p className="text-11 text-secondary">{s.editor.not_workspace_member}</p>
            ) : (
              <>
                <DivisiPicker opsi={daftarDivisi} dipilih={divisi} onUbah={setDivisi} nama={namaDivisi} />
                {(masuk.length > 0 || keluar.length > 0) && (
                  <p className="text-11 text-secondary">
                    {masuk.length > 0 && `${fill(s.editor.joined, { list: masuk.join(", ") })} `}
                    {keluar.length > 0 && fill(s.editor.left, { list: keluar.join(", ") })}
                  </p>
                )}
              </>
            )}
          </div>
        </div>

        {tampilAwasi && (
          <div className="space-y-1">
            <span className="block text-11 text-secondary">{s.editor.supervised}</span>
            <DivisiPicker
              opsi={opsiAwasi}
              dipilih={awasi}
              onUbah={setAwasi}
              nama={namaDivisi}
              placeholder={s.editor.supervised_empty}
            />
            <p className="text-11 text-secondary">{s.editor.supervised_note}</p>
          </div>
        )}

        <p className="text-11 text-secondary">{s.editor.password_note}</p>

        {member.is_super_admin ? (
          <div className="border-warning-primary/30 flex flex-wrap items-center gap-2 rounded border bg-warning-subtle/20 px-3 py-2">
            <ShieldCheck className="size-4 shrink-0 text-warning-primary" aria-hidden />
            <span className="text-11 font-medium text-primary">{s.editor.superadmin_badge}</span>
            <Button variant="secondary" size="sm" disabled={sibukSuperAdmin} onClick={onCabutSuperAdmin}>
              {s.editor.revoke}
            </Button>
          </div>
        ) : (
          <div className="space-y-1.5 rounded border border-subtle px-3 py-2">
            <span className="block text-11 font-medium text-secondary">{s.editor.make_superadmin}</span>
            <span className="block text-11 text-tertiary">{s.editor.make_superadmin_note}</span>
            <p className="text-11 text-secondary">
              {
                fill(s.editor.confirm_instruction, { phrase: s.editor.confirm_phrase }).split(
                  s.editor.confirm_phrase
                )[0]
              }
              <code className="font-mono rounded bg-layer-2 px-1 py-0.5 text-primary">{s.editor.confirm_phrase}</code>
              {
                fill(s.editor.confirm_instruction, { phrase: s.editor.confirm_phrase }).split(
                  s.editor.confirm_phrase
                )[1]
              }
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <input
                className={`${inputClass} min-w-[200px] flex-1`}
                type="text"
                autoComplete="off"
                placeholder={s.editor.confirm_phrase}
                aria-label={s.editor.confirm_phrase}
                aria-invalid={frasa.length > 0 && !frasaCocok}
                value={frasa}
                onChange={(e) => setFrasa(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && frasaCocok && !sibukGrant) handleGrant();
                }}
              />
              <Button variant="primary" size="sm" disabled={sibukGrant || !frasaCocok} onClick={handleGrant}>
                {s.editor.grant_superadmin}
              </Button>
            </div>
          </div>
        )}

        <div className="flex gap-2">
          <Button variant="primary" size="sm" disabled={sibuk || passwordTerlaluPendek} onClick={handleSimpan}>
            {s.editor.save}
          </Button>
          <Button variant="secondary" size="sm" disabled={sibuk} onClick={onTutup}>
            {s.editor.cancel}
          </Button>
        </div>

        <ZonaHapus member={member} onSelesai={onSelesai} onTutup={onTutup} />
      </div>
    </div>
  );
}

/**
 * Satu sumber kebenaran jangkauan (KEP-29): staf/supervisor = departemen,
 * manager = divisi (dipilih eksplisit, tidak ditebak), direktur = seluruh perusahaan.
 * Akses project mengikuti otomatis di server sesudah Simpan.
 */
function Penempatan({
  tingkat,
  departemenId,
  divisiId,
  onDepartemen,
  onDivisi,
  pilihanDepartemen,
  pilihanDivisi,
}: {
  tingkat: number;
  departemenId: string;
  divisiId: string;
  onDepartemen: (id: string) => void;
  onDivisi: (id: string) => void;
  pilihanDepartemen: TPilihanDepartemen[];
  pilihanDivisi: TPilihanDivisi[];
}) {
  const { s } = useGodmodeStrings();
  if (tingkat >= TINGKAT_DIREKTUR) {
    return (
      <div className="space-y-1 sm:col-span-2">
        <span className="block text-11 text-secondary">{s.editor.placement}</span>
        <p className="text-11 text-secondary">{s.editor.director_note}</p>
      </div>
    );
  }
  if (tingkat >= TINGKAT_MANAGER) {
    return (
      <label className="space-y-1 sm:col-span-2">
        <span className="block text-11 text-secondary">{s.editor.led_division}</span>
        <select className={`${inputClass} w-full`} value={divisiId} onChange={(e) => onDivisi(e.target.value)}>
          <option value="">{s.editor.not_placed}</option>
          {pilihanDivisi.map((v) => (
            <option key={v.id} value={v.id}>
              {v.nama} ({v.kode})
            </option>
          ))}
        </select>
        <span className="block text-11 text-tertiary">{s.editor.manager_note}</span>
      </label>
    );
  }
  return (
    <label className="space-y-1 sm:col-span-2">
      <span className="block text-11 text-secondary">{s.editor.department}</span>
      <select className={`${inputClass} w-full`} value={departemenId} onChange={(e) => onDepartemen(e.target.value)}>
        <option value="">{s.editor.not_placed}</option>
        {pilihanDivisi.map((v) => (
          <optgroup key={v.id} label={v.nama}>
            {pilihanDepartemen
              .filter((d) => d.divisi_id === v.id)
              .map((d) => (
                <option key={d.id} value={d.id}>
                  {d.nama} ({d.kode})
                </option>
              ))}
          </optgroup>
        ))}
      </select>
      <span className="block text-11 text-tertiary">
        {tingkat >= TINGKAT_SUPERVISOR ? s.editor.supervisor_note : s.editor.staff_note}
      </span>
    </label>
  );
}

function ZonaHapus({
  member,
  onSelesai,
  onTutup,
}: {
  member: TInstanceMember;
  onSelesai: () => Promise<unknown>;
  onTutup: () => void;
}) {
  const { s, fill } = useGodmodeStrings();
  const [terbuka, setTerbuka] = useState(false);
  const [ketikan, setKetikan] = useState("");
  const [sibuk, setSibuk] = useState(false);
  const cocok = ketikan.trim() === (member.display_name || "").trim() && ketikan.trim().length > 0;

  const handleHapus = async () => {
    if (!cocok) return;
    setSibuk(true);
    try {
      const hasil = await memberService.hapus(member.id, ketikan.trim());
      await onSelesai();
      onTutup();
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: s.editor.account_deleted,
        message: fill(s.editor.account_deleted_message, {
          name: member.display_name,
          sesi: hasil.sessions_ended ?? 0,
        }),
      });
    } catch (err) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: s.editor.delete_failed,
        message: pesanGagal(err, s.editor.delete_failed_message),
      });
    } finally {
      setSibuk(false);
    }
  };

  return (
    <div className="rounded border border-danger-subtle px-3 py-2">
      {!terbuka ? (
        <div className="flex flex-wrap items-center gap-2">
          <Trash2 className="size-4 shrink-0 text-danger-primary" aria-hidden />
          <span className="text-11 font-medium text-primary">{s.editor.delete_zone}</span>
          <span className="text-11 text-tertiary">{s.editor.delete_zone_note}</span>
          <Button variant="error-outline" size="sm" onClick={() => setTerbuka(true)}>
            {s.editor.delete_open}
          </Button>
        </div>
      ) : (
        <div className="space-y-1.5">
          <p className="text-11 font-medium text-primary">
            {fill(s.editor.delete_confirm, { name: member.display_name }).split(member.display_name)[0]}
            <strong>{member.display_name}</strong>
            {fill(s.editor.delete_confirm, { name: member.display_name }).split(member.display_name)[1]}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <input
              className={`${inputClass} min-w-[200px] flex-1`}
              placeholder={member.display_name}
              aria-label={member.display_name}
              value={ketikan}
              onChange={(e) => setKetikan(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && cocok && !sibuk) handleHapus();
              }}
            />
            <Button variant="error-fill" size="sm" disabled={sibuk || !cocok} onClick={handleHapus}>
              {s.editor.delete_now}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={sibuk}
              onClick={() => {
                setTerbuka(false);
                setKetikan("");
              }}
            >
              {s.editor.cancel}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function PemilihWorkspace({ nilai, onUbah }: { nilai: string; onUbah: (slug: string) => void }) {
  const { s } = useGodmodeStrings();
  const [daftar, setDaftar] = useState<{ slug: string; name: string }[]>([]);
  useEffect(() => {
    let hidup = true;
    workspaceService
      .list()
      .then((res) => {
        if (hidup) setDaftar((res?.results ?? []).map((w) => ({ slug: w.slug, name: w.name })));
        return null;
      })
      .catch(() => {});
    return () => {
      hidup = false;
    };
  }, []);
  if (daftar.length <= 1) return null;
  return (
    <select
      className={`${inputClass} w-full`}
      value={nilai}
      aria-label={s.editor.workspace}
      onChange={(e) => onUbah(e.target.value)}
    >
      {nilai === "" && <option value="">{s.editor.workspace_none}</option>}
      {daftar.map((w) => (
        <option key={w.slug} value={w.slug}>
          {w.name}
        </option>
      ))}
    </select>
  );
}
