/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: teks pemberitahuan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Mengubah satu pemberitahuan menjadi dua baris teks polos: judul dan isi.
 *
 * Dipisah dari komponennya karena tujuannya berbeda dari kartu di panel
 * pemberitahuan. Kartu itu menyusun ReactNode: ada tautan, ada potongan editor,
 * ada warna. Yang dibutuhkan di sini TEKS POLOS, karena `new Notification()`
 * hanya menerima teks dan sistem operasilah yang menggambarnya. Memakai ulang
 * penyusun kartu berarti merender React lalu membuang hasilnya.
 *
 * Tipe masukannya sengaja ditulis ulang sebagai bentuk minimum, bukan diimpor
 * dari `@plane/types`. `TNotification` cocok secara struktural, dan tanpa impor
 * beralias berkas ini bisa dijalankan langsung oleh tsx lewat `teks.check.ts`.
 */

export type TTerjemah = (key: string, params?: Record<string, unknown>) => string;

export type TRingkasan = {
  judul: string;
  isi: string;
};

type TAktivitas = {
  field?: string | null | undefined;
  new_value?: string | null | undefined;
  old_value?: string | null | undefined;
  verb?: string | null | undefined;
};

export type TNotifikasiRingkas = {
  title?: string | null | undefined;
  is_mentioned_notification?: boolean | null | undefined;
  triggered_by_details?:
    | {
        display_name?: string | null | undefined;
        first_name?: string | null | undefined;
        is_bot?: boolean | null | undefined;
      }
    | null
    | undefined;
  data?:
    | {
        issue?:
          | {
              name?: string | null | undefined;
              identifier?: string | null | undefined;
              sequence_id?: number | null | undefined;
            }
          | null
          | undefined;
        issue_activity?: TAktivitas | null | undefined;
      }
    | null
    | undefined;
};

/** Sebanyak ini isi pemberitahuan dipotong. Windows dan macOS memang memotong
 * lebih pendek lagi, tapi teks yang sama juga dipakai toast di dalam aplikasi,
 * dan di sana ruangnya lebih lega. */
const BATAS_ISI = 160;

const potong = (teks: string, batas: number) => {
  const rapi = teks.replace(/\s+/g, " ").trim();
  return rapi.length > batas ? `${rapi.slice(0, batas - 1)}…` : rapi;
};

/** Komentar disimpan sebagai HTML. Ini bukan pembersih keamanan: hasilnya
 * ditaruh sebagai teks (body Notification, atau string di dalam JSX), jadi tidak
 * ada jalan bagi tag untuk hidup kembali. Gunanya cuma supaya orang membaca
 * "sudah saya cek" dan bukan "<p>sudah saya cek</p>". */
export const teksPolos = (html: string | null | undefined) => {
  if (!html) return "";
  return potong(
    html
      .replace(/<[^>]*>/g, " ")
      .replace(/&nbsp;/g, " ")
      .replace(/&amp;/g, "&")
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">")
      .replace(/&quot;/g, '"')
      .replace(/&#39;/g, "'"),
    BATAS_ISI
  );
};

/** Kata kerja untuk tiap jenis perubahan.
 *
 * Yang tidak terdaftar jatuh ke kalimat umum, dengan sengaja: Plane menambah
 * jenis aktivitas dari waktu ke waktu, dan daftar yang harus lengkap akan
 * berubah jadi daftar yang selalu ketinggalan. Yang terdaftar di sini adalah
 * yang benar-benar sering muncul di kantor.
 */
const AKSI: Record<string, (a: TAktivitas, t: TTerjemah) => string> = {
  // `None` adalah tugas yang BARU DIBUAT sekaligus ditugaskan ke penerimanya.
  None: (_a, t) => t("notification_ui.action.new_task"),
  assignees: (a, t) => t(a.new_value ? "notification_ui.action.assigned" : "notification_ui.action.unassigned"),
  comment: (a, t) => t("notification_ui.action.commented", { text: teksPolos(a.new_value) }),
  state: (a, t) => t("notification_ui.action.state", { value: a.new_value || "-" }),
  priority: (a, t) => t("notification_ui.action.priority", { value: a.new_value || "-" }),
  target_date: (a, t) =>
    a.new_value
      ? t("notification_ui.action.due_set", { date: String(a.new_value).slice(0, 10) })
      : t("notification_ui.action.due_removed"),
  start_date: (a, t) =>
    a.new_value
      ? t("notification_ui.action.start_set", { date: String(a.new_value).slice(0, 10) })
      : t("notification_ui.action.start_removed"),
  labels: (a, t) =>
    a.new_value
      ? t("notification_ui.action.label_added", { label: a.new_value })
      : t("notification_ui.action.label_removed"),
  attachment: (_a, t) => t("notification_ui.action.attachment"),
  description: (_a, t) => t("notification_ui.action.description"),
  archived_at: (a, t) =>
    t(a.new_value === "restore" ? "notification_ui.action.restored" : "notification_ui.action.archived"),
};

const kalimat = (n: TNotifikasiRingkas, t: TTerjemah) => {
  const aktivitas = n.data?.issue_activity ?? {};
  const field = aktivitas.field ?? "";

  // Penyebutan didahulukan. Sebuah komentar yang menyebut nama Anda tetap
  // datang dengan field "comment", dan "berkomentar" menyembunyikan justru
  // alasan pemberitahuan ini sampai kepada Anda.
  if (n.is_mentioned_notification) {
    const kutipan = field === "comment" ? teksPolos(aktivitas.new_value) : "";
    return kutipan
      ? t("notification_ui.action.mentioned_with_quote", { text: kutipan })
      : t("notification_ui.action.mentioned");
  }

  const penyusun = AKSI[field];
  if (penyusun) return penyusun(aktivitas, t);
  if (!field) return t("notification_ui.action.updated");
  return t("notification_ui.action.updated_field", { field: field.replace(/_/g, " ") });
};

export const ringkasNotifikasi = (n: TNotifikasiRingkas, t: TTerjemah): TRingkasan => {
  const pemicu = n.triggered_by_details;
  const nama = (pemicu?.is_bot ? pemicu?.first_name : pemicu?.display_name) || t("notification_ui.someone");

  const tugas = n.data?.issue;
  const kode = tugas?.identifier && tugas?.sequence_id ? `${tugas.identifier}-${tugas.sequence_id} ` : "";
  const judul = tugas?.name ? `${kode}${tugas.name}` : n.title || t("notification_ui.new_notification");

  return { judul: potong(judul, 90), isi: potong(`${nama} ${kalimat(n, t)}`, BATAS_ISI) };
};

// --- obrolan ----------------------------------------------------------------

export type TPercakapanRingkas = {
  id: string;
  nama?: string | null | undefined;
  lawan_bicara?: string | null | undefined;
  belum_dibaca: number;
  pesan_terakhir_pada?: string | null | undefined;
  isi?: string | null | undefined;
  dari_saya?: boolean | null | undefined;
};

/**
 * Percakapan mana yang layak dimunculkan, dan bagaimana bunyinya.
 *
 * `dari_saya` ikut disaring bukan karena kehati-hatian berlebih: mengirim pesan
 * dari perangkat lain menaikkan waktu pesan terakhir di percakapan itu, dan
 * tanpa saringan ini orang bisa diberi tahu tentang kalimatnya sendiri.
 *
 * `namaOrang` disuntikkan supaya berkas ini tidak menyentuh store MobX. Nama DM
 * tidak ada di jawaban server: yang ada hanya id lawan bicara, karena nama
 * sebuah DM berbeda tergantung siapa yang melihatnya.
 */
export const ringkasPercakapan = (
  baris: TPercakapanRingkas[],
  namaOrang: (userId: string) => string | undefined,
  t: TTerjemah
): (TRingkasan & { ruangId: string; lawanBicara: string | null }) | null => {
  const belum = baris.filter((b) => b.belum_dibaca > 0 && !b.dari_saya);
  if (belum.length === 0) return null;

  const terbaru = belum.reduce((a, b) => ((b.pesan_terakhir_pada ?? "") > (a.pesan_terakhir_pada ?? "") ? b : a));

  const namaKanal = terbaru.nama ? `# ${terbaru.nama}` : null;
  const namaDM = terbaru.lawan_bicara ? namaOrang(terbaru.lawan_bicara) : undefined;
  const judul = namaKanal ?? namaDM ?? t("notification_ui.new_message");

  const lain = belum.length - 1;
  const ekor = lain > 0 ? ` ${t("notification_ui.more_conversations", { count: lain })}` : "";
  // Pesannya dipotong lebih dulu supaya ekornya SELALU muat. Kalau keduanya
  // dipotong bersama, justru "(+3 percakapan lain)" yang hilang setiap kali
  // pesannya panjang, padahal itu bagian yang tidak bisa ditebak sendiri.
  const pesan = potong(teksPolos(terbaru.isi) || t("notification_ui.sent_attachment"), BATAS_ISI - ekor.length);

  return {
    judul: potong(judul, 90),
    isi: `${pesan}${ekor}`,
    ruangId: terbaru.id,
    lawanBicara: terbaru.lawan_bicara ?? null,
  };
};
