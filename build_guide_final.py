"""Space Paradise Perkasa Task Tracker Guide, final ber-brand, dwibahasa, + navigasi PDF."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, Table, TableStyle, PageBreak, Image as RLImage,
                                KeepTogether)
import os
import re as _re
import html as _html
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont as _TTFont
pdfmetrics.registerFont(_TTFont('Geist', 'assets/fonts/Geist-Regular.ttf'))
pdfmetrics.registerFont(_TTFont('Geist-Medium', 'assets/fonts/Geist-Medium.ttf'))
pdfmetrics.registerFont(_TTFont('Geist-SemiBold', 'assets/fonts/Geist-SemiBold.ttf'))
pdfmetrics.registerFont(_TTFont('Geist-Bold', 'assets/fonts/Geist-Bold.ttf'))
pdfmetrics.registerFontFamily('Geist', normal='Geist', bold='Geist-Bold', italic='Geist', boldItalic='Geist-Bold')

OUT = "Space Paradise Perkasa Task Tracker Guide.pdf"
LOGO = "Company_Logo/Paradise_Perkasa.png"
SHOT = "guide_shots"
TGL_ID = "22 Oktober 2026"
TGL_EN = "October 22, 2026"
APP_VER = "v1.5.0"
DOC_VER = "Final v1.0"
APP_URL = "https://space.paradiseperkasa.com"

RED = colors.HexColor("#C0392B")
RED_DARK = colors.HexColor("#96281B")
RED_BG = colors.HexColor("#FDECEA")
INK = colors.HexColor("#1F2937")
GREY = colors.HexColor("#6B7280")
LINE = colors.HexColor("#E5E7EB")
LIGHT = colors.HexColor("#F6F7F9")
BLUE = colors.HexColor("#1D4ED8")
BLUE_BG = colors.HexColor("#EFF4FF")
GREEN_BG = colors.HexColor("#EDF9F0")
GREEN_BD = colors.HexColor("#2E9E5B")
AMBER_BG = colors.HexColor("#FFF7E8")
AMBER_BD = colors.HexColor("#D9A021")

PW, PH = A4
ML, MR, MT, MB = 18 * mm, 18 * mm, 22 * mm, 18 * mm

sTitle = ParagraphStyle("title", fontName="Geist-Bold", fontSize=26, leading=30, textColor=RED)
sSubtitle = ParagraphStyle("subtitle", fontName="Geist-Bold", fontSize=13, leading=17, textColor=BLUE)
sCoverDesc = ParagraphStyle("coverdesc", fontName="Geist", fontSize=10.5, leading=15, textColor=GREY)
sCoverCo = ParagraphStyle("coverco", fontName="Geist-Bold", fontSize=13, textColor=RED)
sH1 = ParagraphStyle("h1", fontName="Geist-Bold", fontSize=14, leading=18, textColor=RED)
sH1en = ParagraphStyle("h1en", parent=sH1, textColor=RED)
sH2 = ParagraphStyle("h2", fontName="Geist-Bold", fontSize=11.5, leading=15, textColor=INK)
sBody = ParagraphStyle("body", fontName="Geist", fontSize=9.8, leading=14.5, alignment=TA_JUSTIFY,
                       textColor=INK, spaceAfter=4)
sBullet = ParagraphStyle("bullet", parent=sBody, leftIndent=14, bulletIndent=4, spaceAfter=3)
sCell = ParagraphStyle("cell", fontName="Geist", fontSize=9.2, leading=12.5, textColor=INK)
sCellH = ParagraphStyle("cellh", parent=sCell, fontName="Geist-Bold", textColor=colors.white)
sCap = ParagraphStyle("cap", fontName="Geist", fontSize=8.8, leading=12,
                      textColor=GREY, alignment=TA_CENTER)
sToc0 = ParagraphStyle("toc0", fontName="Geist-Bold", fontSize=11, leading=18, textColor=RED, spaceBefore=8)
sToc1 = ParagraphStyle("toc1", fontName="Geist", fontSize=10, leading=16, textColor=INK, leftIndent=6)
sToc2 = ParagraphStyle("toc2", fontName="Geist", fontSize=9.5, leading=15, textColor=INK, leftIndent=18)
sBack = ParagraphStyle("back", fontName="Geist", fontSize=8.5, leading=11, textColor=BLUE)
sHeadTxt = ParagraphStyle("headtxt", fontName="Geist", fontSize=7.5, textColor=GREY)
sFootTxt = ParagraphStyle("foottxt", fontName="Geist", fontSize=7.5, textColor=colors.white,
                          alignment=TA_CENTER)

story = []
HEADS = []
TOC_AT = [None]
fig = [0]


def _sp(h):
    s = Spacer(1, h)
    s.keepWithNext = True
    return s


# ---------- helpers ----------
def H(text, style, level):
    key = f"sec{len(HEADS)}"
    plain = _html.unescape(_re.sub(r"<.*?>", "", text)).strip()
    if level <= 1:
        story.append(PageBreak())
    HEADS.append((key, plain, level))
    anchor = Paragraph(f'<a name="{key}"/>',
                       ParagraphStyle("anch", parent=sBody, fontSize=1, leading=2, spaceAfter=0, spaceBefore=0))
    anchor._bmkey = key
    anchor._bmplain = plain
    anchor._bmlevel = level
    anchor.keepWithNext = True
    story.append(anchor)
    if level == 0:
        inner = [[Paragraph(text, ParagraphStyle("ph0", parent=sH1, fontSize=17, leading=21))]]
        t = Table(inner, colWidths=[PW - ML - MR])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), RED_BG),
                               ("BOX", (0, 0), (-1, -1), 0.8, RED),
                               ("LEFTPADDING", (0, 0), (-1, -1), 10),
                               ("TOPPADDING", (0, 0), (-1, -1), 8),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
        p = Paragraph(text, style)
        t.keepWithNext = True
        story.append(t)
        story.append(_sp(10))
        if os.path.exists(LOGO):
            try:
                _lw = 52 * mm
                story.append(RLImage(LOGO, width=_lw, height=_lw, kind="proportional"))
                story.append(_sp(8))
            except Exception:
                pass
        if "BAGIAN A" in text:
            story.append(Paragraph("Bagian ini berisi panduan lengkap dalam <b>Bahasa Indonesia</b>, "
                                   "sembilan bab dari pengenalan sampai bantuan cepat, dengan screenshot "
                                   "langkah-demi-langkah.", sCoverDesc))
            story.append(_sp(6))
            for _ch in ["1. Pengenalan &amp; persyaratan", "2. Cara masuk (login)",
                        "3. Navigasi: menu &amp; tampilan", "4. Alur kerja sehari-hari",
                        "5. Membuat work item baru", "6. Melihat status pekerjaan",
                        "7. Persetujuan (untuk atasan)", "8. Pengaturan &amp; preferensi",
                        "9. Bantuan cepat (FAQ)"]:
                story.append(Paragraph(_ch, ParagraphStyle("pch", parent=sToc1, leftIndent=12)))
        else:
            story.append(Paragraph("This part contains the complete guide in <b>English</b>, nine "
                                   "chapters from introduction to quick help, with step-by-step screenshots.",
                                   sCoverDesc))
            story.append(_sp(6))
            for _ch in ["1. Introduction &amp; requirements", "2. Signing in",
                        "3. Navigation: menus &amp; layout", "4. Daily workflow",
                        "5. Creating a new work item", "6. Tracking your work status",
                        "7. Approvals (for managers)", "8. Settings &amp; preferences",
                        "9. Quick help (FAQ)"]:
                story.append(Paragraph(_ch, ParagraphStyle("pch", parent=sToc1, leftIndent=12)))
    elif level == 1:
        white = ParagraphStyle("h1w", parent=style, textColor=colors.white)
        inner = [[Paragraph(text, white)]]
        t = Table(inner, colWidths=[PW - ML - MR])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), RED),
                               ("ROUNDEDCORNERS", [4, 4, 4, 4]),
                               ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 10),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                               ("TOPPADDING", (0, 0), (-1, -1), 6),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        t.keepWithNext = True
        story.append(t)
        story.append(_sp(7))
        p = Paragraph(text, style)
    else:
        hp = Paragraph(text, style)
        hp.keepWithNext = True
        story.append(hp)
        story.append(_sp(3))
        p = Paragraph(text, style)
    p._bmkey = key
    p._bmplain = plain
    p._bmlevel = level
    return p


def img(fname, caption):
    fig[0] += 1
    story.append(_sp(3))
    _block = []
    p = os.path.join(SHOT, fname)
    if os.path.exists(p):
        iw = PW - ML - MR
        story.append(RLImage(p, width=iw, height=iw * 0.586, kind="proportional"))
        outer = [[story.pop()]]
        t = Table(outer, colWidths=[iw])
        t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.7, LINE),
                               ("INNERPADDING", (0, 0), (-1, -1), 0),
                               ("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                               ("TOPPADDING", (0, 0), (-1, -1), 0),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
        _block.append(t)
    _block.append(Spacer(1, 2))
    _block.append(Paragraph(f"Gambar {fig[0]}, {caption}", sCap))
    story.append(KeepTogether(_block))
    story.append(Spacer(1, 5))


def bullets(items):
    for it in items:
        story.append(Paragraph(it, sBullet, bulletText="•"))


def steps(items):
    for i, it in enumerate(items, 1):
        num = (f'<font color="#FFFFFF"><b>{i}</b></font>')
        badge = Table([[Paragraph(num, ParagraphStyle("nb", parent=sBody, alignment=TA_CENTER,
                                                      fontSize=9, leading=11, textColor=colors.white))]],
                      colWidths=[7 * mm])
        badge.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), RED),
                                   ("ROUNDEDCORNERS", [3, 3, 3, 3]),
                                   ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                   ("TOPPADDING", (0, 0), (-1, -1), 2),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
        body = Paragraph(it, sBody)
        t = Table([[badge, body]], colWidths=[9 * mm, PW - ML - MR - 9 * mm])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 1),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 1),
                               ("TOPPADDING", (0, 0), (-1, -1), 1),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
        story.append(KeepTogether(t))


def grid(rows, widths=(52 * mm, 100 * mm)):
    t = Table(rows, colWidths=list(widths), repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), RED),
        ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#D1D5DB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT])]))
    story.append(_sp(3))
    story.append(t)
    story.append(Spacer(1, 5))


def callout(kind, text):
    if kind == "tip":
        bg, bd, label = GREEN_BG, GREEN_BD, "TIPS / TIP"
    elif kind == "warn":
        bg, bd, label = AMBER_BG, AMBER_BD, "PERHATIAN / NOTE"
    else:
        bg, bd, label = BLUE_BG, BLUE, "INFO"
    lab = Paragraph(f"<b>{label}</b>",
                    ParagraphStyle("cl", parent=sBody, fontSize=8.5, leading=11, textColor=bd, spaceAfter=2))
    txt = Paragraph(text, sBody)
    t = Table([[lab], [txt]], colWidths=[PW - ML - MR])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg),
                           ("BOX", (0, 0), (-1, -1), 0.8, bd),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 5),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    story.append(_sp(3))
    story.append(KeepTogether(t))
    story.append(Spacer(1, 4))


def hcell(s):
    return Paragraph(f"<b>{s}</b>", sCellH)


def c(s):
    return Paragraph(s, sCell)


def build_toc():
    elems = [Paragraph("Daftar Isi / Table of Contents", sH1)]
    elems.append(Spacer(1, 4))
    for key, plain, level in HEADS:
        if level > 1:
            continue
        st = sToc0 if level == 0 else sToc1
        safe = plain.replace("&", "&amp;").replace("<", "&lt;")
        elems.append(Paragraph(f'<a href="#{key}" color="blue">{safe}</a>', st))
    return elems


# ================= COVER =================
story.append(Spacer(1, 14))
story.append(Paragraph("PT PARADISE PERKASA &nbsp;&nbsp;•&nbsp;&nbsp; INTERNAL DOCUMENT",
                       ParagraphStyle("eyebrow", parent=sCoverDesc, alignment=TA_CENTER,
                                      fontSize=9, leading=12, textColor=RED, fontName="Geist-Bold")))
story.append(Spacer(1, 8))
if os.path.exists(LOGO):
    try:
        _lw = 58 * mm
        _logo = RLImage(LOGO, width=_lw, height=_lw, kind="proportional")
        _logo.hAlign = "CENTER"
        story.append(_logo)
        story.append(Spacer(1, 8))
    except Exception:
        pass
story.append(Paragraph("Space Paradise Perkasa", ParagraphStyle("t1", parent=sTitle, alignment=TA_CENTER,
                                                                fontSize=30, leading=33)))
story.append(Paragraph("Task Tracker Guide", ParagraphStyle("t2", parent=sTitle, alignment=TA_CENTER,
                                                            fontSize=30, leading=33)))
story.append(Spacer(1, 4))
story.append(Spacer(1, 6))

story.append(Spacer(1, 6))
story.append(Paragraph("Step-by-step guide for employees: daily workflow, creating work items, manager &amp; staff approvals, and account settings.",
                       ParagraphStyle("descc", parent=sCoverDesc, alignment=TA_CENTER)))
story.append(Spacer(1, 8))

story.append(Spacer(1, 10))
grid([[hcell("Details"), hcell("Content")],
      [c("Date of issue"), c(f"<b>{TGL_EN}</b>")],
      [c("App version"), c(APP_VER)],
      [c("Classification"), c("Internal only")]])

TOC_AT[0] = len(story)
story.append(PageBreak())

# ============================================================
# BAGIAN A. INDONESIA
# ============================================================
H("BAGIAN A. Panduan Bahasa Indonesia", sH1, 0)

H("1. Pengenalan &amp; persyaratan", sH1, 1)
story.append(Paragraph("Paradise Task Tracker adalah aplikasi pencatat dan pelacak pekerjaan kantor "
                       "PT Paradise Perkasa, dipakai lewat browser di alamat "
                       f"<b>{APP_URL}</b>. Pekerjaan di aplikasi ini disebut <b>work item</b> "
                       "(kartu pekerjaan). Setiap divisi (IT, Sales, HRGA, dsb.) punya <b>ruang kerja sendiri "
                       "(project)</b>. Anda hanya melihat divisi Anda sendiri.", sBody))
story.append(Paragraph("Sebelum mulai, pastikan Anda punya:", sBody))
bullets(["Alamat aplikasi: <b>https://space.paradiseperkasa.com</b> (buka di browser).",
         "Akun email kantor + password awal dari IT.",
         "Koneksi internet/intranet kantor."])
story.append(Paragraph("Istilah yang sering muncul (aplikasi memakai Bahasa Inggris):", sBody))
grid([[hcell("Istilah di layar"), hcell("Artinya")],
      [c("Work item"), c("Kartu/tugas pekerjaan")],
      [c("Add work item"), c("Tambah pekerjaan baru")],
      [c("Approvals"), c("Persetujuan")],
      [c("Needs my decision"), c("Perlu keputusan saya (untuk atasan)")],
      [c("My requests"), c("Pengajuan saya (untuk staf)")],
      [c("Awaiting approval"), c("Menunggu persetujuan atasan")],
      [c("Approved"), c("Disetujui, boleh dikerjakan")],
      [c("Backlog / Todo / In Progress"), c("Antri / Belum dikerjakan / Sedang dikerjakan")],
      [c("Assignee"), c("Pelaksana (orang yang mengerjakan)")],
      [c("Save / Discard"), c("Simpan / Batalkan")]])

H("2. Cara masuk (login)", sH1, 1)
steps(["Buka <b>https://space.paradiseperkasa.com</b> di browser. Halaman menyapa "
       "<i>“Selamat datang / Welcome back”</i>.",
       "Ketik <b>email kantor</b> di kolom Email, klik <b>Continue</b>.",
       "Ketik <b>password</b>, klik <b>Continue</b>.",
       "Jika muncul pesan kesalahan, periksa ketikan (huruf besar/kecil). Masih gagal? Hubungi IT.",
       "Anda masuk ke workspace <b>PT Paradise Perkasa</b>."])
img("staff_01_login.png", "Halaman login, isi email kantor lalu klik Continue. / Sign-in page.")
img("staff_02_password.png", "Halaman password. / Password page.")
H("2.1. Masuk dengan kode OTP (tanpa password)", sH2, 2)
story.append(Paragraph("Selain password, Anda bisa masuk memakai <b>kode OTP</b> yang dikirim ke email. "
                       "Caranya:", sBody))
steps(["Di halaman password, klik tautan <b>Sign in with unique code</b>.",
       "Kode OTP dikirim ke <b>email kantor</b> Anda. Buka inbox email dan salin kodenya.",
       "Kembali ke aplikasi, masukkan kode di kolom yang tersedia, klik <b>Continue</b>.",
       "Kode kedaluwarsa dalam beberapa menit. Jika kedaluwarsa, minta kode baru lewat tombol kirim ulang."])
callout("warn", "<b>Keamanan:</b> Jangan berikan password kepada siapa pun, termasuk atasan. "
                "Saat login pertama, segera ganti password (lihat Bagian 8).")

H("3. Navigasi: menu &amp; tampilan", sH1, 1)
H("3.1. Halaman Home (beranda)", sH2, 2)
story.append(Paragraph("Setelah login Anda tiba di <b>Home</b>: sapaan nama + tanggal, <b>Quicklinks</b> "
                       "(tautan favorit Anda), dan <b>Recents</b> (halaman yang baru dibuka). "
                       "Tombol <b>Manage widgets</b> mengatur isi beranda.", sBody))
img("staff_03_beranda.png", "Beranda: sapaan, Quicklinks, Recents. / Home page.")
H("3.2. Menu kiri (sidebar)", sH2, 2)
bullets(["<b>New work item</b>, tombol cepat membuat pekerjaan baru.",
         "<b>Home, Drafts, Your work</b>, beranda, draf tersimpan, dan semua pekerjaan yang ditugaskan "
         "kepada Anda.",
         "<b>Stickies</b>, catatan tempel pribadi.",
         "<b>Workspace</b>, area perusahaan: <b>Projects</b> (daftar divisi, klik divisi Anda), "
         "<b>Dashboards, Initiatives, Chat, Wiki</b> (fitur tambahan), <b>More</b>.",
         "Bagian bawah: jalan pintas divisi di <b>Projects / LAINNYA</b> (contoh: [IT])."])
H("3.3. Menu dalam divisi", sH2, 2)
story.append(Paragraph("Setelah membuka divisi (misalnya IT), submenu kiri berubah:", sBody))
bullets(["<b>Work items</b>, papan semua pekerjaan divisi (halaman utama kerja harian).",
         "<b>Cycles, Modules, Views</b>, pengelompokan &amp; tampilan lain (opsional).",
         "<b>Pages</b>, halaman dokumen. <b>Intake</b>, kotak masuk permintaan dari divisi lain.",
         "<b>Approvals</b>, halaman persetujuan (Bagian 6-7)."])
H("3.4. Bagian atas (header)", sH2, 2)
bullets(["Kolom <b>Search commands...</b>, mencari pekerjaan/perintah dengan cepat.",
         "Kanan atas: notifikasi, bantuan, dan <b>foto/huruf nama Anda</b>, klik untuk menu profil, "
         "pengaturan, dan keluar (log out)."])
H("3.5. Siapa bisa apa (peran)", sH2, 2)
grid([[hcell("Peran"), hcell("Bisa apa")],
      [c("Staf"), c("Membuat work item dan menugaskannya <b>kepada diri sendiri</b>; melihat status "
        "pengajuan di Approvals → My requests; mengajukan ulang bila ditolak.")],
      [c("Atasan (supervisor / manajer / direktur divisi)"),
       c("Semua hak staf, plus <b>menyetujui/menolak</b> pengajuan staf di Approvals → Needs my decision.")]])

H("4. Alur kerja sehari-hari", sH1, 1)
steps(["<b>Buat</b> work item untuk pekerjaan Anda (Bagian 5). Karena pelaksananya diri sendiri, "
       "statusnya otomatis <b>Awaiting approval</b>.",
       "<b>Atasan</b> membuka Approvals dan menyetujui/menolak (Bagian 7).",
       "<b>Disetujui</b> → kerjakan, geser statusnya (Backlog → Todo → In Progress → selesai).",
       "<b>Ditolak</b> → baca alasan, perbaiki, <b>ajukan ulang</b>."])
bullets(["Staf hanya menugaskan pekerjaan <b>kepada diri sendiri</b>.",
         "Penolakan <b>wajib beralasan</b> tertulis.",
         "Tidak ada yang bisa menyetujui pekerjaannya sendiri."])

H("5. Membuat work item baru", sH1, 1)
steps(["Buka divisi → <b>Work items</b>. Klik tombol biru <b>Add work item</b> (atau <b>+ New work item</b> "
       "di tiap kolom).",
       "Jendela <b>Create new work item</b> terbuka. Isi:<br/>"
       "• <b>Title</b>, judul singkat &amp; jelas, mis. <i>Ganti toner printer lantai 2</i>.<br/>"
       "• <b>Description</b>, penjelasan tambahan (tidak wajib).<br/>"
       "• <b>Pelaksana</b>, otomatis nama Anda. <b>Jangan diubah.</b><br/>"
       "• <b>Status awal</b>, biarkan <i>Backlog</i>. <b>Priority</b>, biarkan <i>None</i> kecuali "
       "diminta atasan.<br/>"
       "• <b>Labels, Start/Due date, Cycle, Modules</b>, opsional.",
       "Klik <b>Save</b> (<b>Discard</b> untuk batal; <b>Create more</b> bila ingin langsung membuat lagi).",
       "Kartu muncul di <b>Backlog</b> dengan nomor (mis. <b>IT-27</b>) dan label <b>Awaiting approval</b>."])
img("staff_07_form_baru.png", "Form 'Create new work item'. / New work item form.")
img("staff_08_form_terisi.png", "Form terisi: judul + pelaksana (nama sendiri), siap klik Save. / Filled form.")
callout("tip", "<b>Tips judul:</b> diawali kata kerja, <i>Perbaiki AC ruang meeting, Siapkan laporan "
               "stok Maret, Hubungi vendor X untuk penawaran</i>.")
img("staff_05_daftar_work_item.png", "Papan Work items: kolom Backlog/Todo/In Progress, kartu bernomor + label "
     "status, tombol Add work item, penanda Pending approval. / Work items board.")
img("staff_09_hasil_buat.png", "Kartu baru IT-27 berlabel 'Awaiting approval'. / New card awaiting approval.")

H("5.4. Khusus atasan: membuat work item untuk bawahan", sH2, 2)
story.append(Paragraph("Atasan memakai jendela yang sama, tetapi bisa memilih <b>pelaksana lain</b>: "
                       "anggota divisinya (bawahan). Caranya:", sBody))
steps(["Klik <b>Add work item</b> dan isi <b>Title</b> seperti biasa.",
       "Klik tombol <b>Assignees</b> (pelaksana). Terbuka daftar anggota: <b>You</b> (diri sendiri) "
       "plus nama bawahan/anggota divisi. Ketik di kolom <b>Search</b> bila daftar panjang.",
       "Klik <b>nama bawahan</b> yang ditugaskan (bertanda centang). Bisa pilih lebih dari satu orang. "
       "Klik di luar daftar untuk menutupnya.",
       "Lengkapi lainnya bila perlu, klik <b>Save</b>."])
img("mgr_30_form_atasan.png", "Form yang sama dari akun atasan, tombol 'Assignees' untuk memilih pelaksana. / Same form from a manager account.")
img("mgr_31_pilih_pelaksana.png", "Klik 'Assignees': muncul daftar 'You' + anggota divisi. / Assignee dropdown with division members.")
img("mgr_32_pelaksana_terpilih.png", "Judul terisi + bawahan (Marvel) terpilih (centang), siap klik Save. / Subordinate selected.")
callout("info", "Pekerjaan yang dibuat <b>atasan tidak perlu persetujuan</b>, baik ditugaskan ke bawahan "
                "maupun ke diri sendiri, dan langsung muncul di papan <b>tanpa</b> label “Awaiting approval”. "
                "Persetujuan hanya berlaku bila <b>staf menugaskan ke dirinya sendiri</b>. Atasan hanya bisa "
                "menugaskan ke anggota <b>divisinya sendiri</b>.")
H("6. Melihat status pekerjaan", sH1, 1)
H("6.1. Di papan Work items", sH2, 2)
story.append(Paragraph("Tiap kartu menampilkan <b>nomor, judul, pelaksana, status</b>, plus label prioritas "
                       "(mis. <i>Urgent</i>) dan tanggal. Label kuning <b>Awaiting approval</b> = menunggu "
                       "atasan. Label hijau <b>Approved</b> = sudah disetujui. "
                       "Kartu yang <b>ditolak hilang dari papan</b> (kembali menjadi draf tak-terlihat), "
                       "lihat statusnya di halaman Approvals.", sBody))
img("staff_15_papan_disetujui.png", "Sesudah disetujui: label hijau 'Approved' (IT-27, IT-28). "
     "IT-26 masih 'Awaiting approval'. / Approved badges on board.")
img("staff_13_papan_setelah_keputusan.png", "Efek penolakan: IT-27 yang ditolak hilang dari papan "
     "(menjadi draf); IT-28 yang disetujui berlabel Approved. / Rejected item leaves the board.")
H("6.2. Di halaman Approvals → My requests", sH2, 2)
steps(["Buka divisi → <b>Approvals</b>.",
       "Klik <b>My requests</b> (Pengajuan saya) di atas daftar.",
       "Terlihat semua pengajuan Anda: <b>menunggu / disetujui / ditolak + alasan</b>. "
       "Yang ditolak bisa <b>diajukan ulang (resubmit)</b> setelah diperbaiki."])
callout("info", "Jika daftar Approvals tampak memuat lama atau berkedip, itu gangguan tampilan yang sudah "
                "dilaporkan ke IT, klik <b>Reload</b> dan tunggu sebentar; data pengajuan Anda aman.")

H("7. Persetujuan (untuk atasan)", sH1, 1)
H("7.1. Membuka antrean", sH2, 2)
steps(["Buka divisi → <b>Approvals</b>. Pastikan <b>Needs my decision</b> aktif.",
       "Tiap baris berisi: <b>nomor &amp; judul, nama pengaju, tanggal</b>, kolom alasan, "
       "dan tombol <b>Approve / Reject</b>."])
img("mgr_21_antrean.png", "Antrean atasan: 3 pengajuan menunggu, tiap kartu ada kolom alasan + tombol "
     "Approve/Reject. / Manager queue with decision buttons.")
H("7.2. Menyetujui / menolak", sH2, 2)
steps(["Isi kolom alasan bila perlu. <b>Menolak wajib diisi</b>, staf membutuhkannya untuk memperbaiki; "
       "menyetujui boleh dikosongkan.",
       "Klik <b>Approve</b> atau <b>Reject</b>.",
       "Baris hilang dari antrean; status berubah di sisi staf (Approved di papan, atau hilang + alasan "
       "di My requests)."])
H("7.3. Siklus lengkap", sH2, 2)
story.append(Paragraph("Contoh nyata dari sistem ini. IT-27 <i>“Ganti toner printer lantai 2”</i>: staf "
                       "membuat → atasan <b>menolak</b> dengan alasan → staf memperbaiki &amp; <b>mengajukan "
                       "ulang</b> → atasan <b>menyetujui</b> → kartu berlabel hijau <b>Approved</b>. "
                       "Jika staf bertanya “kenapa ditolak?”, arahkan ke <b>Approvals → My requests</b>.", sBody))

H("8. Pengaturan &amp; preferensi", sH1, 1)
steps(["Klik <b>foto/huruf nama Anda</b> kanan atas → pilih <b>Profile/Settings</b>.",
       "<b>Profile (Umum)</b>, nama depan/belakang, nama tampilan (Display name), foto, email.",
       "<b>Preferences (Preferensi)</b>, <b>Theme</b> (terang/gelap), <b>Timezone</b> "
       "(pastikan <i>UTC+07:00 Jakarta</i>), <b>Language</b>, <b>First day of the week</b>.",
       "<b>Notifications (Notifikasi)</b>, saklar email: perubahan properti, pindah status, komentar, "
       "disebut (mentions), dan <b>Approval decisions</b>. Disarankan tetap aktif.",
       "<b>Security (Keamanan)</b>, ganti password: isi password lama + password baru dua kali, klik "
       "<b>Change password</b>.",
       "Keluar dari aplikasi: klik foto profil → <b>Log out</b>."])
img("staff_set_21_umum.png", "Pengaturan Profile: nama, display name, email. / General profile settings.")
img("staff_set_22_preferensi.png", "Preferences: Theme, Timezone (Jakarta), Language, awal pekan. / Preferences.")
img("staff_set_23_notifikasi.png", "Notifikasi email, termasuk 'Approval decisions'. / Email notifications.")
img("staff_set_24_keamanan.png", "Security: ganti password. / Change password.")

H("9. Bantuan cepat (FAQ)", sH1, 1)
grid([[hcell("Masalah"), hcell("Solusi")],
      [c("Tidak bisa login"), c("Periksa email &amp; password (huruf besar/kecil). Masih gagal? Hubungi IT.")],
      [c("Tidak melihat divisi lain"), c("Normal. Anda hanya bisa melihat divisi sendiri.")],
      [c("Tombol Save tidak jalan"), c("Judul masih kosong, isi dulu kolom Title.")],
      [c("Macet di “Awaiting approval”"), c("Menunggu atasan. Ingatkan atasan membuka Approvals.")],
      [c("Pengajuan ditolak"), c("Baca alasan di Approvals → My requests, perbaiki, ajukan ulang.")]])
grid([[hcell("Masalah (lanjutan)"), hcell("Solusi (lanjutan)")],
      [c("Tanggal terlihat aneh"), c("Preferences → Timezone = UTC+07:00 Jakarta.")],
      [c("Daftar Approvals kedip/lama"), c("Klik Reload, tunggu sebentar. Sudah dilaporkan ke IT; data aman.")],
      [c("Lupa password"), c("Security → Change password (perlu password lama), atau hubungi IT untuk reset.")],
      [c("Butuh bantuan lain"), c("Hubungi IT dengan menyebutkan nomor work item (mis. IT-27).")]])

# ============================================================
# PART B. ENGLISH
# ============================================================
H("PART B. English User Guide", sH1en, 0)

H("1. Introduction &amp; requirements", sH1, 1)
story.append(Paragraph("Paradise Task Tracker is PT Paradise Perkasa's internal app for recording and tracking "
                       "office work, opened in a browser at "
                       f"<b>{APP_URL}</b>. A unit of work is called a <b>work item</b> (job card). "
                       "Each division (IT, Sales, HRGA, etc.) has its <b>own workspace (project)</b>, "
                       "you only see your own division.", sBody))
story.append(Paragraph("Before you start, make sure you have:", sBody))
bullets(["The app address: <b>https://space.paradiseperkasa.com</b> (open it in a browser).",
         "Your office email account + initial password from IT.",
         "Office internet/intranet connection."])
story.append(Paragraph("Common terms (the app uses English):", sBody))
grid([[hcell("On-screen term"), hcell("Meaning")],
      [c("Work item"), c("Job/task card")],
      [c("Add work item"), c("Create a new job")],
      [c("Approvals"), c("Approval queue")],
      [c("Needs my decision"), c("Items waiting for your decision (managers)")],
      [c("My requests"), c("Your own submissions (staff)")],
      [c("Awaiting approval"), c("Waiting for the manager's decision")],
      [c("Approved"), c("Approved, you may start working")],
      [c("Backlog / Todo / In Progress"), c("Queued / Not started / Being worked on")],
      [c("Assignee"), c("The person doing the work")],
      [c("Save / Discard"), c("Save / Cancel")]])

H("2. Signing in", sH1, 1)
steps(["Open <b>https://space.paradiseperkasa.com</b> in your browser. It greets you with "
       "<i>“Selamat datang / Welcome back”</i>.",
       "Type your <b>office email</b> in the Email field, click <b>Continue</b>.",
       "Type your <b>password</b>, click <b>Continue</b>.",
       "If an error appears, recheck your typing (upper/lower case). Still stuck? Contact IT.",
       "You land in the <b>PT Paradise Perkasa</b> workspace."])
img("staff_01_login.png", "Sign-in page, enter your office email, then Continue.")
img("staff_02_password.png", "Password page.")
H("2.1. Signing in with an OTP code (no password)", sH2, 2)
story.append(Paragraph("Besides a password, you can sign in with an <b>OTP code</b> sent to your email. "
                       "How:", sBody))
steps(["On the password page, click <b>Sign in with unique code</b>.",
       "An OTP code is sent to your <b>office email</b>. Open your inbox and copy the code.",
       "Back in the app, enter the code in the field provided, click <b>Continue</b>.",
       "Codes expire within minutes. If yours expires, request a new one with the resend button."])
callout("warn", "<b>Security:</b> Never share your password with anyone, including your manager. "
                "Change it after your first sign-in (see Section 8).")

H("3. Navigation: menus &amp; layout", sH1, 1)
H("3.1. Home page", sH2, 2)
story.append(Paragraph("After signing in you reach <b>Home</b>: a greeting with your name and date, "
                       "<b>Quicklinks</b> (your favourite links), and <b>Recents</b> (recently opened pages). "
                       "Use <b>Manage widgets</b> to customise it.", sBody))
img("staff_03_beranda.png", "Home: greeting, Quicklinks, Recents.")
H("3.2. Left menu (sidebar)", sH2, 2)
bullets(["<b>New work item</b>, quick button to create a job.",
         "<b>Home, Drafts, Your work</b>, home, saved drafts, and every job assigned to you.",
         "<b>Stickies</b>, personal sticky notes.",
         "<b>Workspace</b>, company area: <b>Projects</b> (division list, click your division), "
         "<b>Dashboards, Initiatives, Chat, Wiki</b> (extras), <b>More</b>.",
         "Bottom: shortcuts to your division under <b>Projects / LAINNYA</b> (e.g. [IT])."])
H("3.3. Inside a division", sH2, 2)
bullets(["<b>Work items</b>, the board of all division jobs (your daily home page).",
         "<b>Cycles, Modules, Views</b>, groupings &amp; alternative views (optional).",
         "<b>Pages</b>, documents. <b>Intake</b>, inbox for requests from other divisions.",
         "<b>Approvals</b>, the approval queue (Sections 6-7)."])
H("3.4. Top bar (header)", sH2, 2)
bullets(["<b>Search commands...</b>, quickly find jobs/commands.",
         "Top right: notifications, help, and <b>your photo/initial</b>, click for profile, settings, "
         "and sign out (log out)."])
H("3.5. Who can do what (roles)", sH2, 2)
grid([[hcell("Role"), hcell("Allowed to")],
      [c("Staff"), c("Create work items assigned <b>to themselves</b>; track submissions in Approvals → "
        "My requests; resubmit when rejected.")],
      [c("Manager (division supervisor / manager / director)"),
       c("Everything staff can, plus <b>approve/reject</b> staff submissions in Approvals → Needs my decision.")]])

H("4. Daily workflow", sH1, 1)
steps(["<b>Create</b> a work item for your job (Section 5). Since you assign it to yourself, it "
       "automatically becomes <b>Awaiting approval</b>.",
       "Your <b>manager</b> opens Approvals and approves/rejects it (Section 7).",
       "<b>Approved</b> → do the work, moving its status (Backlog → Todo → In Progress → done).",
       "<b>Rejected</b> → read the reason, fix it, <b>resubmit</b>."])
bullets(["Staff may only assign work <b>to themselves</b>.",
         "Rejections <b>must include a written reason</b>.",
         "Nobody can approve their own work."])

H("5. Creating a new work item", sH1, 1)
steps(["Open your division → <b>Work items</b>. Click the blue <b>Add work item</b> button (or "
       "<b>+ New work item</b> under any column).",
       "The <b>Create new work item</b> window opens. Fill in:<br/>"
       "• <b>Title</b>, short &amp; clear, e.g. <i>Replace 2nd-floor printer toner</i>.<br/>"
       "• <b>Description</b>, extra details (optional).<br/>"
       "• <b>Assignee</b>, already your name. <b>Do not change it.</b><br/>"
       "• <b>Initial state</b>, leave <i>Backlog</i>. <b>Priority</b>, leave <i>None</i> unless your "
       "manager says otherwise.<br/>"
       "• <b>Labels, Start/Due date, Cycle, Modules</b>, optional.",
       "Click <b>Save</b> (<b>Discard</b> cancels; <b>Create more</b> starts another one right away).",
       "The card appears in <b>Backlog</b> with a number (e.g. <b>IT-27</b>) and an "
       "<b>Awaiting approval</b> label."])
img("staff_07_form_baru.png", "'Create new work item' form (empty).")
img("staff_08_form_terisi.png", "Filled form: title + yourself as assignee, ready to Save.")
callout("tip", "<b>Good titles</b> start with a verb, <i>Fix the meeting-room AC, Prepare the March "
               "stock report, Call vendor X for a quote</i>.")
img("staff_05_daftar_work_item.png", "Work items board: Backlog/Todo/In Progress columns, numbered cards with "
     "status labels, Add work item button, Pending approval indicator.")
img("staff_09_hasil_buat.png", "New card IT-27 labelled 'Awaiting approval'.")

H("5.4. For managers: creating work items for subordinates", sH2, 2)
story.append(Paragraph("Managers use the same window, but can pick <b>other assignees</b>: members of their "
                       "division (subordinates). How:", sBody))
steps(["Click <b>Add work item</b> and fill in <b>Title</b> as usual.",
       "Click the <b>Assignees</b> button. A member list opens: <b>You</b> (yourself) plus division "
       "members/subordinates. Type in <b>Search</b> if the list is long.",
       "Click the <b>subordinate's name</b> (a checkmark appears). You may select more than one person. "
       "Click outside the list to close it.",
       "Complete the rest if needed, click <b>Save</b>."])
img("mgr_30_form_atasan.png", "Same form from a manager account, the 'Assignees' button picks the worker.")
img("mgr_31_pilih_pelaksana.png", "Click 'Assignees': a list of 'You' + division members appears.")
img("mgr_32_pelaksana_terpilih.png", "Title filled + subordinate (Marvel) selected (checkmarked), ready to Save.")
callout("info", "Jobs created by a <b>manager need no approval</b>, whether assigned to a subordinate or to "
                "themselves, and appear on the board <b>without</b> an “Awaiting approval” label. Approval "
                "only applies when <b>staff assign work to themselves</b>. Managers can only assign members of "
                "<b>their own division</b>.")
H("6. Tracking your work status", sH1, 1)
H("6.1. On the Work items board", sH2, 2)
story.append(Paragraph("Each card shows <b>number, title, assignee, state</b>, plus priority labels "
                       "(e.g. <i>Urgent</i>) and dates. A yellow <b>Awaiting approval</b> label means it waits "
                       "for your manager. A green <b>Approved</b> label means approved, go ahead. "
                       "A <b>rejected</b> card disappears from the board (back to an invisible draft), "
                       "track it in Approvals instead.", sBody))
img("staff_15_papan_disetujui.png", "After approval: green 'Approved' labels (IT-27, IT-28). "
     "IT-26 still 'Awaiting approval'.")
img("staff_13_papan_setelah_keputusan.png", "Rejection effect: rejected IT-27 leaves the board (draft); "
     "approved IT-28 shows Approved.")
H("6.2. In Approvals → My requests", sH2, 2)
steps(["Open your division → <b>Approvals</b>.",
       "Click <b>My requests</b> above the list.",
       "You see all your submissions: <b>pending / approved / rejected + reason</b>. "
       "Rejected ones can be <b>resubmitted</b> after fixing."])
callout("info", "If the Approvals list seems slow or flickers, it is a known display issue already reported "
                "to IT, click <b>Reload</b> and wait a moment; your data is safe.")

H("7. Approvals (for managers)", sH1, 1)
H("7.1. Opening the queue", sH2, 2)
steps(["Open your division → <b>Approvals</b>. Make sure <b>Needs my decision</b> is active.",
       "Each row shows: <b>number &amp; title, requester, date</b>, a reason field, and "
       "<b>Approve / Reject</b> buttons."])
img("mgr_21_antrean.png", "Manager queue: 3 pending requests, each with reason field + Approve/Reject buttons.")
H("7.2. Approving / rejecting", sH2, 2)
steps(["Fill the reason field if needed. <b>Rejecting requires a reason</b>, staff need it to fix their "
       "work; approving may leave it empty.",
       "Click <b>Approve</b> or <b>Reject</b>.",
       "The row leaves the queue; the status changes for staff (Approved on the board, or gone + reason "
       "in My requests)."])
H("7.3. Full cycle", sH2, 2)
story.append(Paragraph("Real example from this system. IT-27 <i>“Ganti toner printer lantai 2”</i>: staff "
                       "created → manager <b>rejected</b> with a reason → staff fixed &amp; <b>resubmitted</b> "
                       "→ manager <b>approved</b> → green <b>Approved</b> card on the board. If staff ask "
                       "“why was it rejected?”, point them to <b>Approvals → My requests</b>.", sBody))

H("8. Settings &amp; preferences", sH1, 1)
steps(["Click <b>your photo/initial</b> top-right → choose <b>Profile/Settings</b>.",
       "<b>Profile (General)</b>, first/last name, display name, photo, email. Complete it so colleagues "
       "recognise you.",
       "<b>Preferences</b>, <b>Theme</b> (light/dark look), <b>Timezone</b> (should be "
       "<i>UTC+07:00 Jakarta</i>), <b>Language</b> (app language), <b>First day of the week</b>.",
       "<b>Notifications</b>, email switches: property changes, state moves, comments, mentions, and "
       "<b>Approval decisions</b>. Keep them on.",
       "<b>Security</b>, change password: enter current + new password twice, click "
       "<b>Change password</b>.",
       "Sign out: click your profile photo → <b>Log out</b>."])
img("staff_set_21_umum.png", "Profile settings: name, display name, email.")
img("staff_set_22_preferensi.png", "Preferences: Theme, Timezone (Jakarta), Language, week start.")
img("staff_set_23_notifikasi.png", "Email notifications, incl. 'Approval decisions'.")
img("staff_set_24_keamanan.png", "Security: change password.")

H("9. Quick help (FAQ)", sH1, 1)
grid([[hcell("Problem"), hcell("Solution")],
      [c("Cannot sign in"), c("Recheck email &amp; password (case matters). Still stuck? Contact IT.")],
      [c("Cannot see other divisions"), c("Normal, you only see your own division.")],
      [c("Save button does nothing"), c("Title is empty, fill the Title field first.")],
      [c("Stuck on “Awaiting approval”"), c("Waiting for your manager. Remind them to open Approvals.")],
      [c("Request rejected"), c("Read the reason in Approvals → My requests, fix, resubmit.")],
      [c("Dates look wrong"), c("Preferences → Timezone = UTC+07:00 Jakarta.")],
      [c("Approvals list flickers/slow"), c("Click Reload and wait. Reported to IT; your data is safe.")],
      [c("Forgot password"), c("Security → Change password (needs old password), or ask IT for a reset.")],
      [c("Other help needed"), c("Contact IT (internal support) and mention the work item number (e.g. IT-27).")]])

story.append(Spacer(1, 8))
story.append(Paragraph(", End of guide. This document is internal to PT Paradise Perkasa.<br/>"
                       ", Akhir panduan. Dokumen ini bersifat internal PT Paradise Perkasa.", sCap))

# ---------- sisipkan TOC + template ----------
story.insert(TOC_AT[0] + 1, Paragraph('<a name="toc"/>',
                                      ParagraphStyle("anchtoc", parent=sBody, fontSize=1, leading=2,
                                                     spaceAfter=0, spaceBefore=0)))
for _e in reversed(build_toc()):
    story.insert(TOC_AT[0] + 2, _e)


def header_footer(canvas, doc):
    canvas.saveState()
    # header: brand + garis merah
    if doc.page > 1:
        if os.path.exists(LOGO):
            try:
                canvas.drawImage(LOGO, ML, PH - 15 * mm, width=9 * mm, height=9 * mm,
                                 preserveAspectRatio=True, mask="auto")
            except Exception:
                pass
        canvas.setFont("Geist-Bold", 7.5)
        canvas.setFillColor(RED)
        canvas.drawString(ML + 11 * mm, PH - 11.5 * mm, "Space Paradise Perkasa  •  Task Tracker Guide")
        canvas.setFont("Geist", 7.5)
        canvas.setFillColor(GREY)
        canvas.drawRightString(PW - MR, PH - 11.5 * mm, f"{TGL_ID}  •  App {APP_VER}")
        canvas.setStrokeColor(RED)
        canvas.setLineWidth(0.8)
        canvas.line(ML, PH - 17 * mm, PW - MR, PH - 17 * mm)
    # footer merah
    canvas.setFillColor(RED)
    canvas.rect(0, 0, PW, 12 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Geist", 7.5)
    back_txt = "« Kembali ke Daftar Isi / Back to Contents"
    canvas.drawString(ML, 5 * mm, back_txt)
    _bw = canvas.stringWidth(back_txt, "Geist", 7.5)
    canvas.linkRect(back_txt, "toc", (ML, 3.2 * mm, ML + _bw, 8 * mm), relative=0)
    _rt = f"Halaman {doc.page}"
    canvas.drawRightString(PW - MR, 5 * mm, _rt)
    canvas.restoreState()


class GuideDoc(BaseDocTemplate):
    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and getattr(flowable, "_bmkey", None):
            self.canv.bookmarkPage(flowable._bmkey)
            self.canv.addOutlineEntry(flowable._bmplain, flowable._bmkey, flowable._bmlevel, closed=0)


doc = GuideDoc(OUT, pagesize=A4, leftMargin=ML, rightMargin=MR, topMargin=MT, bottomMargin=MB,
               title="Space Paradise Perkasa Task Tracker Guide", author="PT Paradise Perkasa")
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=header_footer)])
doc.build(story)
print("OK:", OUT, os.path.getsize(OUT), "bytes,", fig[0], "gambar,", len(HEADS), "bookmark")
