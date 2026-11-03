/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: editor member terpadu God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Satu modal, satu tombol Simpan, untuk semua sumbu orang ini:
 * - Data akun (nama, email, hak akses workspace, password) — PATCH members.
 * - Jenjang + SATU daftar penempatan (departemen & divisi) — POST hierarki (KEP-76).
 * - Akses project lain (pengecualian) — POST divisi-anggota (atomik).
 *
 * Tiga panggilan berurutan, berhenti di yang pertama gagal supaya tidak ada
 * keadaan setengah jadi. Tampilan: ParadiseModal dengan Panel per bagian
 * (Akun, Organisasi, Preferensi, Super Admin, Zona bahaya); Simpan/Batal di
 * kaki yang lengket supaya tidak perlu menggulir ke bawah untuk menyimpan.
 *
 * Peran divisi DITURUNKAN dari jabatan, bukan dipilih: manager/supervisor =
 * Admin divisi (20), member/belum-diisi = Member (15). Keputusan user 2026-10-16.
 */

import { useEffect, useState } from "react";
import { Building2, KeyRound, Settings2, ShieldAlert, ShieldCheck, Trash2, UserRound } from "lucide-react";
// plane imports
import { Badge } from "@plane/propel/badge";
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
import { CustomSearchSelect, CustomSelect, Input } from "@plane/ui";
// components
import { EModalWidth, Field, Panel, ParadiseModal, PersonAvatar } from "@/components/common/paradise-ui";
import { UnsavedIndicator, useUnsavedChanges } from "@/components/common/unsaved-changes";
// local
import { cocokKonfirmasiGrant, useGodmodeStrings, type TGodmodeStrings } from "@/app/i18n/godmode";
import { PERAN_DEFAULT } from "./constants";
import { DivisiPicker } from "./divisi-picker";
import { PreferensiMember, useMemberPreferences } from "./preferensi";

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
/** True when two id lists differ as sets (order ignored). */
const himpunanBeda = (a: string[], b: string[]) => a.length !== b.length || a.some((x) => !b.includes(x));

const peranDivisi = (tingkat: number | null): number => (tingkat !== null && tingkat >= TINGKAT_SUPERVISOR ? 20 : 15);

const pesanGagal = (err: unknown, fallback: string): string => {
  const pesan = (err as { error?: string } | undefined)?.error;
  return typeof pesan === "string" && pesan.length > 0 ? pesan : fallback;
};

/** Pecah kalimat bertanda {placeholder} supaya bagian tengahnya bisa ditebalkan/dikode. */
const pecah = (kalimat: string, sisip: string): [string, string] => {
  const i = kalimat.indexOf(sisip);
  return i < 0 ? [kalimat, ""] : [kalimat.slice(0, i), kalimat.slice(i + sisip.length)];
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
        departemen_ids?: string[];
        divisi_ids?: string[];
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

const NAMA_DIVISI_KOSONG: Record<string, string> = {};
const DEPARTEMEN_KOSONG: TPilihanDepartemen[] = [];
const DIVISI_KOSONG: TPilihanDivisi[] = [];

export function MemberEditor({
  member,
  hierarki,
  daftarDivisi,
  petaDivisi,
  namaDivisi = NAMA_DIVISI_KOSONG,
  pilihanDepartemen = DEPARTEMEN_KOSONG,
  pilihanDivisi = DIVISI_KOSONG,
  onSelesai,
  onTutup,
  onCabutSuperAdmin,
  sibukSuperAdmin = false,
}: Props) {
  const { s, fill } = useGodmodeStrings();
  const opsiTingkat = pilihanTingkat(s);
  // --- data akun ---
  const [nama, setNama] = useState(member.display_name);
  const [email, setEmail] = useState(member.email);
  // Kontak kantor untuk kartu profil anggota di apps/web.
  const [ekstensi, setEkstensi] = useState(member.phone_extension ?? "");
  const [peran, setPeran] = useState(member.workspace_role ?? PERAN_DEFAULT);
  const [password, setPassword] = useState("");
  // Workspace tempat ia anggota sekarang; "" = belum jadi anggota mana pun.
  const [wsSlug, setWsSlug] = useState(member.workspace_slug ?? "");
  // --- jabatan + pengawasan + divisi (initial dari hierarki kalau ada) ---
  // Jabatan kosong dianggap staf; tersimpan sebagai staf saat Simpan.
  const [tingkat, setTingkat] = useState<string>(String(hierarki?.tingkat ?? TINGKAT_MEMBER));
  const [awasi, setAwasi] = useState<string[]>(hierarki ? [...hierarki.divisi_diawasi] : []);
  // Penempatan (KEP-76): satu daftar, menambah tidak pernah memindahkan.
  const depAwal = hierarki?.departemen_ids ?? (hierarki?.departemen_id ? [hierarki.departemen_id] : []);
  const divAwal = hierarki?.divisi_ids ?? (hierarki?.divisi_id ? [hierarki.divisi_id] : []);
  const [departemenIds, setDepartemenIds] = useState<string[]>(depAwal);
  const [divisiIds, setDivisiIds] = useState<string[]>(divAwal);
  // Divisi hanya dipimpin manager ke atas: di bawahnya yang dikirim kosong.
  const divisiDikirim = Number(tingkat) >= TINGKAT_MANAGER ? divisiIds : [];
  // Project yang sudah otomatis dari penempatan tidak ditampilkan sebagai
  // "akses lain": mencentangnya tidak berarti apa-apa (sinkron hierarki menang).
  const otomatisAwal = projectOtomatis(pilihanDepartemen, depAwal, divAwal, hierarki?.tingkat ?? null);
  const ekstraAwal = hierarki ? hierarki.divisi.filter((d) => !otomatisAwal.has(d)) : [];
  const [divisi, setDivisi] = useState<string[]>(ekstraAwal);
  const [sibuk, setSibuk] = useState(false);
  const [frasa, setFrasa] = useState("");
  const [sibukGrant, setSibukGrant] = useState(false);
  const pref = useMemberPreferences(member.id);

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
    // Kirim HANYA yang berubah: tulis-ulang email mengakhiri sesi orangnya
    // tanpa alasan.
    const patch: TMemberUpdate = {};
    if (nama.trim() && nama.trim() !== member.display_name) patch.display_name = nama.trim();
    if (email.trim().toLowerCase() !== member.email.toLowerCase()) patch.email = email.trim().toLowerCase();
    if (ekstensi.trim() !== (member.phone_extension ?? "")) patch.phone_extension = ekstensi.trim();
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
      const prefBerubah = pref.perubahan();
      if (prefBerubah) await memberService.ubahPreferensi(member.id, prefBerubah);
      if (hierarki !== undefined) {
        const tingkatBaru = Number(tingkat);
        const tingkatBerubah = tingkatBaru !== hierarki.tingkat;
        const pengawasanBerubah =
          awasi.length !== hierarki.divisi_diawasi.length || awasi.some((d) => !hierarki.divisi_diawasi.includes(d));
        const divisiBerubah = himpunanBeda(divisi, ekstraAwal);
        const departemenBerubah = himpunanBeda(departemenIds, depAwal);
        const divisiIdBerubah = himpunanBeda(divisiDikirim, divAwal);
        if (tingkatBerubah || pengawasanBerubah || departemenBerubah || divisiIdBerubah) {
          // `pengawasan` hanya dikirim kalau diubah: tidak-dikirim = jangan
          // sentuh, dikirim kosong = cabut semua (kontrak endpoint). Penempatan
          // ikut panggilan yang sama: satu simpan = satu sinkron akses di server.
          await hierarkiService.setel({
            member_id: member.id,
            ...(tingkatBerubah ? { tingkat: tingkatBaru } : {}),
            ...(departemenBerubah ? { departemen_ids: departemenIds } : {}),
            ...(divisiIdBerubah ? { divisi_ids: divisiDikirim } : {}),
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
  const strukturAktif = pilihanDivisi.length > 0;
  // KEP-76: dengan struktur aktif, wewenang supervisor/manager datang dari
  // penempatan; baris pengawasan hanya berarti untuk direktur (membatasi).
  const tampilAwasi =
    hierarki !== undefined &&
    (strukturAktif ? Number(tingkat) >= TINGKAT_DIREKTUR : Number(tingkat) >= TINGKAT_SUPERVISOR);
  const opsiAwasi = strukturAktif ? daftarDivisi : daftarDivisi.filter((d) => divisi.includes(d) || awasi.includes(d));
  const otomatis = projectOtomatis(pilihanDepartemen, departemenIds, divisiDikirim, Number(tingkat));
  const opsiEkstra = strukturAktif ? daftarDivisi.filter((d) => !otomatis.has(d)) : daftarDivisi;
  const namaDivisiOrg = Object.fromEntries(pilihanDivisi.map((v) => [v.id, v.nama]));
  const divisiDilepas = Number(tingkat) < TINGKAT_MANAGER ? divAwal.map((id) => namaDivisiOrg[id] ?? id) : [];
  const masuk = hierarki === undefined ? [] : divisi.filter((d) => !ekstraAwal.includes(d));
  const keluar = hierarki === undefined ? [] : ekstraAwal.filter((d) => !divisi.includes(d));
  const labelPeran: Record<number, string> = {
    20: s.members.role_admin,
    15: s.members.role_member,
    5: s.members.role_guest,
  };
  const [instruksiAwal, instruksiAkhir] = pecah(
    fill(s.editor.confirm_instruction, { phrase: s.editor.confirm_phrase }),
    s.editor.confirm_phrase
  );

  // Paradise: modal footer is always on screen, so it carries the unsaved marker
  // instead of the dashboard bar; the leave-page guard still applies.
  const isDirty =
    nama !== member.display_name ||
    email !== member.email ||
    ekstensi !== (member.phone_extension ?? "") ||
    peran !== (member.workspace_role ?? PERAN_DEFAULT) ||
    wsSlug !== (member.workspace_slug ?? "") ||
    password !== "" ||
    pref.perubahan() !== null ||
    (hierarki !== undefined &&
      (Number(tingkat) !== (hierarki.tingkat ?? TINGKAT_MEMBER) ||
        himpunanBeda(awasi, hierarki.divisi_diawasi) ||
        himpunanBeda(divisi, ekstraAwal) ||
        himpunanBeda(departemenIds, depAwal) ||
        himpunanBeda(divisiDikirim, divAwal)));
  useUnsavedChanges({
    isDirty,
    isSaving: sibuk,
    canSave: !passwordTerlaluPendek,
    showBar: false,
    onSave: handleSimpan,
    onDiscard: onTutup,
  });

  return (
    <ParadiseModal
      isOpen
      onClose={onTutup}
      width={EModalWidth.XXXXL}
      leading={<PersonAvatar name={member.display_name || member.email} size="lg" />}
      title={
        <span className="flex items-center gap-2">
          <span className="truncate">{member.display_name || member.email}</span>
          {member.is_super_admin && (
            <Badge variant="warning" prependIcon={<ShieldCheck />}>
              {s.supercell.label}
            </Badge>
          )}
        </span>
      }
      subtitle={member.email}
      closeLabel={s.editor.close}
      footerNote={
        <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
          {isDirty && <UnsavedIndicator />}
          <span>{s.editor.password_note}</span>
        </span>
      }
      footer={
        <>
          <Button variant="secondary" size="base" disabled={sibuk} onClick={onTutup}>
            {s.editor.cancel}
          </Button>
          <Button variant="primary" size="base" loading={sibuk} disabled={passwordTerlaluPendek} onClick={handleSimpan}>
            {s.editor.save}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Panel
          icon={<UserRound className="size-4" />}
          title={s.editor.section_account}
          description={s.editor.section_account_note}
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={s.editor.name}>
              <Input className="w-full" value={nama} onChange={(e) => setNama(e.target.value)} />
            </Field>
            <Field label={s.editor.email}>
              <Input className="w-full" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            </Field>
            <Field label={s.editor.phone_extension}>
              <Input
                className="w-full"
                inputMode="tel"
                maxLength={20}
                value={ekstensi}
                onChange={(e) => setEkstensi(e.target.value)}
              />
            </Field>
            <PemilihWorkspace nilai={wsSlug} onUbah={setWsSlug} />
            <Field label={s.editor.workspace_role}>
              <CustomSelect
                value={peran}
                label={labelPeran[peran] ?? s.members.role_member}
                onChange={(v: number) => setPeran(Number(v))}
                buttonClassName="w-full"
                className="w-full"
                input
              >
                {[20, 15, 5].map((v) => (
                  <CustomSelect.Option key={v} value={v}>
                    {labelPeran[v]}
                  </CustomSelect.Option>
                ))}
              </CustomSelect>
            </Field>
            <Field
              label={s.editor.new_password}
              hint={s.editor.password_hint}
              error={passwordTerlaluPendek ? s.editor.password_too_short : undefined}
            >
              <Input
                className="w-full"
                type="password"
                autoComplete="new-password"
                hasError={passwordTerlaluPendek}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </Field>
          </div>
        </Panel>

        <Panel
          icon={<Building2 className="size-4" />}
          title={s.editor.section_org}
          description={hierarki === undefined ? s.editor.not_workspace_member : s.editor.section_org_note}
        >
          {hierarki !== undefined && (
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label={s.editor.position}>
                <CustomSelect
                  value={tingkat}
                  label={opsiTingkat.find((p) => p.value === tingkat)?.label}
                  onChange={(v: string) => setTingkat(v)}
                  buttonClassName="w-full"
                  className="w-full"
                  input
                >
                  {opsiTingkat.map((p) => (
                    <CustomSelect.Option key={p.value} value={p.value}>
                      {p.label}
                    </CustomSelect.Option>
                  ))}
                </CustomSelect>
              </Field>

              {strukturAktif && (
                <Penempatan
                  tingkat={Number(tingkat)}
                  departemenIds={departemenIds}
                  divisiIds={divisiIds}
                  onUbah={(dep, div) => {
                    setDepartemenIds(dep);
                    setDivisiIds(div);
                  }}
                  pilihanDepartemen={pilihanDepartemen}
                  pilihanDivisi={pilihanDivisi}
                  divisiDilepas={divisiDilepas}
                />
              )}

              <Field
                className="sm:col-span-2"
                label={
                  strukturAktif
                    ? fill(s.editor.extra_projects, { n: divisi.length })
                    : fill(s.editor.divisions, { n: divisi.length })
                }
                hint={
                  strukturAktif && masuk.length === 0 && keluar.length === 0
                    ? s.editor.extra_projects_note
                    : masuk.length > 0 || keluar.length > 0
                      ? [
                          masuk.length > 0 ? fill(s.editor.joined, { list: masuk.join(", ") }) : "",
                          keluar.length > 0 ? fill(s.editor.left, { list: keluar.join(", ") }) : "",
                        ]
                          .filter(Boolean)
                          .join(" ")
                      : undefined
                }
              >
                <DivisiPicker opsi={opsiEkstra} dipilih={divisi} onUbah={setDivisi} nama={namaDivisi} />
              </Field>

              {tampilAwasi && (
                <Field className="sm:col-span-2" label={s.editor.supervised} hint={s.editor.supervised_note}>
                  <DivisiPicker
                    opsi={opsiAwasi}
                    dipilih={awasi}
                    onUbah={setAwasi}
                    nama={namaDivisi}
                    placeholder={s.editor.supervised_empty}
                  />
                </Field>
              )}
            </div>
          )}
        </Panel>

        <Panel
          icon={<Settings2 className="size-4" />}
          title={s.editor.section_prefs}
          description={s.editor.section_prefs_note}
        >
          <PreferensiMember
            nilai={pref.nilai}
            gagal={pref.gagal}
            onProfil={pref.ubahProfil}
            onNotif={pref.ubahNotif}
            onNavigasi={pref.ubahNavigasi}
            onTataLetak={pref.ubahTataLetak}
          />
        </Panel>

        {member.is_super_admin ? (
          <Panel
            tone="warning"
            icon={<ShieldCheck className="size-4" />}
            title={s.editor.section_superadmin}
            description={s.editor.superadmin_badge}
            actions={
              <Button variant="secondary" size="base" loading={sibukSuperAdmin} onClick={onCabutSuperAdmin}>
                {s.editor.revoke}
              </Button>
            }
          />
        ) : (
          <Panel
            icon={<KeyRound className="size-4" />}
            title={s.editor.make_superadmin}
            description={s.editor.make_superadmin_note}
          >
            <div className="space-y-2">
              <p className="text-12 text-secondary">
                {instruksiAwal}
                <code className="rounded-item bg-layer-2 px-1 py-0.5 font-code text-primary">
                  {s.editor.confirm_phrase}
                </code>
                {instruksiAkhir}
              </p>
              <div className="flex flex-wrap items-center gap-2">
                <Input
                  className="min-w-[220px] flex-1"
                  type="text"
                  autoComplete="off"
                  placeholder={s.editor.confirm_phrase}
                  aria-label={s.editor.confirm_phrase}
                  hasError={frasa.length > 0 && !frasaCocok}
                  value={frasa}
                  onChange={(e) => setFrasa(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && frasaCocok && !sibukGrant) void handleGrant();
                  }}
                />
                <Button
                  variant="secondary"
                  size="base"
                  prependIcon={<ShieldAlert />}
                  loading={sibukGrant}
                  disabled={!frasaCocok}
                  onClick={handleGrant}
                >
                  {s.editor.grant_superadmin}
                </Button>
              </div>
            </div>
          </Panel>
        )}

        <ZonaHapus member={member} onSelesai={onSelesai} onTutup={onTutup} />
      </div>
    </ParadiseModal>
  );
}

/** Identifier project yang otomatis didapat dari penempatan (departemen + divisi untuk manager). */
function projectOtomatis(
  pilihan: TPilihanDepartemen[],
  departemenIds: string[],
  divisiIds: string[],
  tingkat: number | null
): Set<string> {
  const hasil = new Set<string>();
  const pimpin = tingkat !== null && tingkat >= TINGKAT_MANAGER;
  for (const d of pilihan) {
    if (departemenIds.includes(d.id) || (pimpin && divisiIds.includes(d.divisi_id))) {
      for (const p of d.projects ?? []) hasil.add(p);
    }
  }
  return hasil;
}

const KODE_DEP = "dep:";
const KODE_DIV = "div:";

/**
 * Satu daftar penempatan (KEP-76): departemen untuk semua jenjang, divisi untuk
 * manager ke atas. Menambah tidak pernah memindahkan; mencabut = hapus centang.
 * Akses project mengikuti otomatis di server sesudah Simpan.
 */
function Penempatan({
  tingkat,
  departemenIds,
  divisiIds,
  onUbah,
  pilihanDepartemen,
  pilihanDivisi,
  divisiDilepas,
}: {
  tingkat: number;
  departemenIds: string[];
  divisiIds: string[];
  onUbah: (departemenIds: string[], divisiIds: string[]) => void;
  pilihanDepartemen: TPilihanDepartemen[];
  pilihanDivisi: TPilihanDivisi[];
  divisiDilepas: string[];
}) {
  const { s, fill } = useGodmodeStrings();
  if (tingkat >= TINGKAT_DIREKTUR) {
    return (
      <Field label={s.editor.placement}>
        <p className="rounded-card border border-subtle bg-layer-2 px-3 py-2 text-12 text-secondary">
          {s.editor.director_note}
        </p>
      </Field>
    );
  }
  const pimpin = tingkat >= TINGKAT_MANAGER;
  const namaDivisi = Object.fromEntries(pilihanDivisi.map((v) => [v.id, v.nama]));
  const namaDep = Object.fromEntries(pilihanDepartemen.map((d) => [d.id, d.nama]));
  const dipilih = [
    ...(pimpin ? divisiIds.map((id) => KODE_DIV + id) : []),
    ...departemenIds.map((id) => KODE_DEP + id),
  ];
  const label = (kode: string) =>
    kode.startsWith(KODE_DIV)
      ? fill(s.org.div_of, { div: namaDivisi[kode.slice(KODE_DIV.length)] ?? "" })
      : (namaDep[kode.slice(KODE_DEP.length)] ?? "");
  const ringkas =
    dipilih.length === 0 ? (
      <span className="text-placeholder">{s.editor.not_placed}</span>
    ) : dipilih.length <= 2 ? (
      dipilih.map(label).join(", ")
    ) : (
      fill(s.picker.chosen_count, { n: dipilih.length })
    );
  const catatan = pimpin
    ? s.editor.placement_manager_note
    : tingkat >= TINGKAT_SUPERVISOR
      ? s.editor.placement_supervisor_note
      : s.editor.placement_staff_note;
  const opsiDivisi = pimpin
    ? pilihanDivisi.map((v) => ({
        value: KODE_DIV + v.id,
        query: `${v.nama} ${v.kode} ${s.editor.placement_group_divisions}`,
        content: (
          <span className="flex w-full items-center justify-between gap-2">
            <span className="truncate">{fill(s.org.div_of, { div: v.nama })}</span>
            <span className="shrink-0 text-11 text-tertiary">{s.editor.placement_group_divisions}</span>
          </span>
        ),
      }))
    : [];
  const opsiDepartemen = pilihanDepartemen.map((d) => ({
    value: KODE_DEP + d.id,
    query: `${d.nama} ${d.kode} ${namaDivisi[d.divisi_id] ?? ""}`,
    content: (
      <span className="flex w-full items-center justify-between gap-2">
        <span className="min-w-0 truncate">
          {d.nama} <span className="text-11 text-tertiary">{d.kode}</span>
        </span>
        <span className="shrink-0 text-11 text-tertiary">{namaDivisi[d.divisi_id]}</span>
      </span>
    ),
  }));
  const ubah = (kode: string[]) => {
    const dep = kode.filter((k) => k.startsWith(KODE_DEP)).map((k) => k.slice(KODE_DEP.length));
    const div = kode.filter((k) => k.startsWith(KODE_DIV)).map((k) => k.slice(KODE_DIV.length));
    // Divisi lama tetap di state selama jenjang di bawah Manager: kembali ke
    // Manager sebelum Simpan mengembalikannya. Yang dikirim disaring pemanggil.
    onUbah(dep, pimpin ? div : divisiIds);
  };
  const hint =
    divisiDilepas.length > 0 ? fill(s.editor.placement_divisions_dropped, { list: divisiDilepas.join(", ") }) : catatan;
  return (
    <Field label={s.editor.placement} hint={hint}>
      <CustomSearchSelect
        multiple
        value={dipilih}
        onChange={(v: string[]) => ubah(v)}
        label={<span className="truncate">{ringkas}</span>}
        buttonClassName="w-full"
        className="w-full"
        input
        maxHeight="lg"
        noResultsMessage={s.picker.empty}
        options={[...opsiDivisi, ...opsiDepartemen]}
      />
    </Field>
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
  const [konfirmasiAwal, konfirmasiAkhir] = pecah(
    fill(s.editor.delete_confirm, { name: member.display_name }),
    member.display_name
  );

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
    <Panel
      tone="danger"
      icon={<Trash2 className="size-4" />}
      title={s.editor.delete_zone}
      description={s.editor.delete_zone_note}
      actions={
        !terbuka && (
          <Button variant="error-outline" size="base" onClick={() => setTerbuka(true)}>
            {s.editor.delete_open}
          </Button>
        )
      }
    >
      {terbuka && (
        <div className="space-y-2">
          <p className="text-12 text-secondary">
            {konfirmasiAwal}
            <strong className="text-primary">{member.display_name}</strong>
            {konfirmasiAkhir}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <Input
              className="min-w-[220px] flex-1"
              placeholder={member.display_name}
              aria-label={member.display_name}
              value={ketikan}
              onChange={(e) => setKetikan(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && cocok && !sibuk) void handleHapus();
              }}
            />
            <Button
              variant="secondary"
              size="base"
              disabled={sibuk}
              onClick={() => {
                setTerbuka(false);
                setKetikan("");
              }}
            >
              {s.editor.cancel}
            </Button>
            <Button variant="error-fill" size="base" loading={sibuk} disabled={!cocok} onClick={handleHapus}>
              {s.editor.delete_now}
            </Button>
          </div>
        </div>
      )}
    </Panel>
  );
}

/** Pemilih workspace; tersembunyi kalau instance hanya punya satu workspace. */
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
    <Field label={s.editor.workspace}>
      <CustomSelect
        value={nilai}
        label={daftar.find((w) => w.slug === nilai)?.name ?? s.editor.workspace_none}
        onChange={(v: string) => onUbah(v)}
        buttonClassName="w-full"
        className="w-full"
        input
      >
        {daftar.map((w) => (
          <CustomSelect.Option key={w.slug} value={w.slug}>
            {w.name}
          </CustomSelect.Option>
        ))}
      </CustomSelect>
    </Field>
  );
}
