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
import { inputClass, PERAN, PERAN_DEFAULT } from "./constants";
import { DivisiPicker } from "./divisi-picker";

const memberService = new InstanceMemberService();
const hierarkiService = new InstanceHierarkiService();
const divisiService = new InstanceDivisiMemberService();
const workspaceService = new InstanceWorkspaceService();

/** Nilai dikirim ke backend. Tanpa "belum diisi": jabatan kosong = staf. */
const PILIHAN_TINGKAT: { value: string; label: string }[] = [
  { value: String(TINGKAT_MEMBER), label: "Member (staf)" },
  { value: String(TINGKAT_SUPERVISOR), label: "Supervisor" },
  { value: String(TINGKAT_MANAGER), label: "Manager" },
  { value: String(TINGKAT_DIREKTUR), label: "Direktur" },
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
  /** Cabut Super Admin (PATCH false). Grant ditangani internal (butuh frasa). */
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

  // Grant Super Admin butuh frasa konfirmasi (diperiksa server, tak ada di
  // bundle). Revoke lewat prop dari halaman (PATCH false, tanpa frasa).
  const handleGrant = async () => {
    setSibukGrant(true);
    try {
      await memberService.update(member.id, { is_super_admin: true, grant_passphrase: frasa });
      setFrasa("");
      await onSelesai();
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: "Super Admin diberikan",
        message: `${member.display_name} sekarang mengakses semua project.`,
      });
    } catch (err) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Ditolak",
        message: pesanGagal(err, "Tidak bisa memberi Super Admin."),
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
    // Frasa yang sudah diketik ikut tombol Simpan, bukan hanya tombol "Beri
    // Super Admin": dulu Simpan mengabaikannya lalu menutup panel seolah sukses.
    // Frasa salah = 403 di depan, tak satu kolom pun tersimpan (gerbang backend).
    if (frasa && !member.is_super_admin) {
      patch.is_super_admin = true;
      patch.grant_passphrase = frasa;
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
      const label = PILIHAN_TINGKAT.find((p) => p.value === tingkat)?.label ?? tingkat;
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: "Tersimpan",
        message: sesiBerakhir
          ? `${nama.trim() || member.display_name}: ${label}, ${divisi.length} divisi, ${sesiBerakhir} sesi diakhiri.`
          : `${nama.trim() || member.display_name}: ${label}, ${divisi.length} divisi.`,
      });
    } catch (err) {
      // Berhenti di panggilan pertama yang gagal: tidak ada keadaan setengah
      // jadi yang diam-diam (pola lama: jabatan tersimpan, divisi 403).
      setToast({ type: TOAST_TYPE.ERROR, title: "Gagal menyimpan", message: pesanGagal(err, "Tidak bisa menyimpan.") });
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
            <span className="block text-11 text-secondary">Nama</span>
            <input className={`${inputClass} w-full`} value={nama} onChange={(e) => setNama(e.target.value)} />
          </label>

          <label className="space-y-1">
            <span className="block text-11 text-secondary">Email (identitas login)</span>
            <input
              className={`${inputClass} w-full`}
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>

          <div className="space-y-1">
            <span className="block text-11 text-secondary">Workspace</span>
            <PemilihWorkspace nilai={wsSlug} onUbah={setWsSlug} />
          </div>

          <label className="space-y-1">
            <span className="block text-11 text-secondary">Hak akses workspace</span>
            <select className={`${inputClass} w-full`} value={peran} onChange={(e) => setPeran(Number(e.target.value))}>
              {Object.entries(PERAN).map(([nilai, label]) => (
                <option key={nilai} value={nilai}>
                  {label}
                </option>
              ))}
            </select>
          </label>

          <label className="space-y-1">
            <span className="block text-11 text-secondary">Password baru</span>
            <input
              className={`${inputClass} w-full`}
              type="password"
              autoComplete="new-password"
              placeholder="kosongkan = tidak diubah"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
        </div>

        {passwordTerlaluPendek && <p className="text-danger text-11">Password minimal 8 karakter.</p>}

        <div className="grid gap-3 sm:grid-cols-3">
          <label className="space-y-1">
            <span className="block text-11 text-secondary">Jabatan</span>
            <select
              className={`${inputClass} w-full`}
              value={tingkat}
              onChange={(e) => setTingkat(e.target.value)}
              disabled={hierarki === undefined}
            >
              {PILIHAN_TINGKAT.map((p) => (
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
                ? `Project tambahan, pengecualian eksplisit (${divisi.length})`
                : `Divisi (${divisi.length})`}
            </span>
            {hierarki === undefined ? (
              <p className="text-11 text-secondary">Bukan anggota workspace — jabatan dan divisi tak bisa diatur.</p>
            ) : (
              <>
                <DivisiPicker
                  opsi={daftarDivisi}
                  dipilih={divisi}
                  onUbah={setDivisi}
                  nama={namaDivisi}
                  placeholder="Pilih divisi…"
                />
                {(masuk.length > 0 || keluar.length > 0) && (
                  <p className="text-11 text-secondary">
                    {masuk.length > 0 && `Masuk: ${masuk.join(", ")}. `}
                    {keluar.length > 0 && `Keluar: ${keluar.join(", ")}.`}
                  </p>
                )}
              </>
            )}
          </div>
        </div>

        {tampilAwasi && (
          <div className="space-y-1">
            <span className="block text-11 text-secondary">Divisi yang dia bawahi (pengawasan)</span>
            <DivisiPicker
              opsi={opsiAwasi}
              dipilih={awasi}
              onUbah={setAwasi}
              nama={namaDivisi}
              placeholder="Ikut rumus (kosong)"
            />
            <p className="text-11 text-secondary">
              Kosong = ikut rumus (direktur semua divisi; lainnya divisinya sendiri). Centang = menang atas rumus.
            </p>
          </div>
        )}

        <p className="text-11 text-secondary">
          Mengubah <strong>password</strong> atau <strong>email</strong> mengakhiri semua sesi orang itu, dia harus
          masuk lagi. Manager/supervisor otomatis jadi Admin di divisinya; member jadi Member biasa. Password barunya
          sampaikan langsung; SMTP belum jalan, tidak ada email yang terkirim.
        </p>

        {member.is_super_admin ? (
          <div className="border-warning-primary/30 flex flex-wrap items-center gap-2 rounded border bg-warning-subtle/20 px-3 py-2">
            <ShieldCheck className="size-4 shrink-0 text-warning-primary" />
            <span className="text-11 font-medium text-primary">Super Admin — akses seluruh project.</span>
            <Button variant="secondary" size="sm" disabled={sibukSuperAdmin} onClick={onCabutSuperAdmin}>
              Cabut
            </Button>
          </div>
        ) : (
          <div className="space-y-1.5 rounded border border-subtle px-3 py-2">
            <span className="block text-11 font-medium text-secondary">Jadikan Super Admin</span>
            <span className="block text-11 text-tertiary">
              Akses seluruh project termasuk yang dibuat nanti. Perlu frasa konfirmasi.
            </span>
            <div className="flex flex-wrap items-center gap-2">
              <input
                className={`${inputClass} min-w-[200px] flex-1`}
                type="password"
                autoComplete="off"
                placeholder="Frasa konfirmasi"
                value={frasa}
                onChange={(e) => setFrasa(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && frasa && !sibukGrant) handleGrant();
                }}
              />
              <Button variant="primary" size="sm" disabled={sibukGrant || !frasa} onClick={handleGrant}>
                Beri Super Admin
              </Button>
            </div>
          </div>
        )}

        <div className="flex gap-2">
          <Button variant="primary" size="sm" disabled={sibuk || passwordTerlaluPendek} onClick={handleSimpan}>
            Simpan
          </Button>
          <Button variant="secondary" size="sm" disabled={sibuk} onClick={onTutup}>
            Batal
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
  if (tingkat >= TINGKAT_DIREKTUR) {
    return (
      <div className="space-y-1 sm:col-span-2">
        <span className="block text-11 text-secondary">Penempatan</span>
        <p className="text-11 text-secondary">Direktur menjangkau seluruh perusahaan, tidak perlu ditempatkan.</p>
      </div>
    );
  }
  if (tingkat >= TINGKAT_MANAGER) {
    return (
      <label className="space-y-1 sm:col-span-2">
        <span className="block text-11 text-secondary">Divisi yang dipimpin</span>
        <select className={`${inputClass} w-full`} value={divisiId} onChange={(e) => onDivisi(e.target.value)}>
          <option value="">— Belum ditempatkan —</option>
          {pilihanDivisi.map((v) => (
            <option key={v.id} value={v.id}>
              {v.nama} ({v.kode})
            </option>
          ))}
        </select>
        <span className="block text-11 text-tertiary">Manager melihat semua departemen di divisi ini.</span>
      </label>
    );
  }
  return (
    <label className="space-y-1 sm:col-span-2">
      <span className="block text-11 text-secondary">Departemen</span>
      <select className={`${inputClass} w-full`} value={departemenId} onChange={(e) => onDepartemen(e.target.value)}>
        <option value="">— Belum ditempatkan —</option>
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
        {tingkat >= TINGKAT_SUPERVISOR
          ? "Supervisor melihat dan mengelola project departemen ini."
          : "Staf melihat semua project departemen ini, mengubah hanya tugas miliknya."}
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
        title: "Akun dihapus",
        message: `${member.display_name} dinonaktifkan dan identitasnya digosok (${hasil.sessions_ended ?? 0} sesi diakhiri). Riwayat tetap utuh.`,
      });
    } catch (err) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Gagal menghapus",
        message: pesanGagal(err, "Tidak bisa menghapus akun."),
      });
    } finally {
      setSibuk(false);
    }
  };

  return (
    <div className="rounded border border-danger-subtle px-3 py-2">
      {!terbuka ? (
        <div className="flex flex-wrap items-center gap-2">
          <Trash2 className="size-4 shrink-0 text-danger-primary" />
          <span className="text-11 font-medium text-primary">Hapus akun ini</span>
          <span className="text-11 text-tertiary">Nonaktif + gosok identitas. Riwayat tetap utuh.</span>
          <Button variant="error-outline" size="sm" onClick={() => setTerbuka(true)}>
            Hapus…
          </Button>
        </div>
      ) : (
        <div className="space-y-1.5">
          <p className="text-11 font-medium text-primary">
            Ketik <strong>{member.display_name}</strong> persis untuk mengonfirmasi. Tidak bisa dibatalkan.
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <input
              className={`${inputClass} min-w-[200px] flex-1`}
              placeholder={member.display_name}
              value={ketikan}
              onChange={(e) => setKetikan(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && cocok && !sibuk) handleHapus();
              }}
            />
            <Button variant="error-fill" size="sm" disabled={sibuk || !cocok} onClick={handleHapus}>
              Hapus permanen
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
              Batal
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function PemilihWorkspace({ nilai, onUbah }: { nilai: string; onUbah: (slug: string) => void }) {
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
    <select className={`${inputClass} w-full`} value={nilai} onChange={(e) => onUbah(e.target.value)}>
      {nilai === "" && <option value="">— Bukan anggota workspace —</option>}
      {daftar.map((w) => (
        <option key={w.slug} value={w.slug}>
          {w.name}
        </option>
      ))}
    </select>
  );
}
