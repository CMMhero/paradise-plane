# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Markdown pesan obrolan dan pengumuman
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Markdown di `PesanLangsung.isi` jadi teks polos atau HTML email.

Pasangannya di peramban: `apps/web/core/lib/markdown/`. Keduanya memakai dialek
yang sama (CommonMark + tabel + coret) dengan konstruksi yang sama dimatikan,
supaya teks yang diketik orang di obrolan tidak hilang atau berubah arti:

* HTML mentah dan entitas tetap teks (`<jam 12>`, `&amp;`);
* baris menjorok bukan blok kode, garis `---` di bawah kalimat bukan judul;
* `[PENTING]: segera` bukan definisi tautan (yang tidak ditampilkan sama sekali).

Kesamaan teks polosnya dijaga `plane/tests/data/markdown_polos.json`, dibaca tes
Python dan tes web.
"""

import re
from html import escape

import nh3
from markdown_it import MarkdownIt
from markdown_it.token import Token
from markdown_it.tree import SyntaxTreeNode

from plane.utils.email_merek import FONT, FONT_MONO, GAYA, UKURAN, WARNA

_SKEMA_TAUTAN = ("http://", "https://", "mailto:")
_ALAMAT = re.compile(r"://[^\s<>\"'`]+")
_SKEMA_WEB = re.compile(r"(?<![A-Za-z])https?$", re.IGNORECASE)
_EKOR = re.compile(r"[.,;:!?)\]}*_~]+$")
_CENTANG = re.compile(r"^\[([ xX])\][ \t]+")


def _alamat_telanjang(state, silent) -> bool:
    """Alamat http(s) jadi tautan utuh, seperti di peramban.

    Sebagai aturan sebaris (dipicu `:`), bukan sesudah diurai: `_` di dalam alamat
    (`.../__init__.py`) kalau tidak, dibaca sebagai penanda tebal.
    """
    if state.linkLevel > 0 or not state.src.startswith("://", state.pos):
        return False
    skema = _SKEMA_WEB.search(state.pending)
    if not skema:
        return False
    ekor = _EKOR.sub("", _ALAMAT.match(state.src[: state.posMax], state.pos).group(0))
    if len(ekor) <= 3:
        return False
    if not silent:
        alamat = skema.group(0) + ekor
        state.pending = state.pending[: skema.start()]
        state.push("link_open", "a", 1).attrs = {"href": state.md.normalizeLink(alamat)}
        state.push("text", "", 0).content = alamat
        state.push("link_close", "a", -1)
    state.pos += len(ekor)
    return True


def _pengurai() -> MarkdownIt:
    md = MarkdownIt("commonmark", {"html": False, "breaks": True})
    md.enable(["table", "strikethrough"])
    md.disable(["code", "lheading", "reference", "entity"])
    # Semua `[label](alamat)` diurai sebagai tautan, sama dengan peramban. Skema yang
    # boleh diklik disaring saat dirender (`_rapikan_sebaris`, lalu nh3).
    md.validateLink = lambda alamat: True
    md.inline.ruler.before("link", "alamat_telanjang", _alamat_telanjang)
    return md


_MD = _pengurai()


# ---------------------------------------------------------------- teks polos


def _sebaris(simpul) -> str:
    if simpul.type in ("text", "code_inline"):
        return simpul.content
    if simpul.type in ("softbreak", "hardbreak"):
        return "\n"
    # Gambar: anak-anaknya adalah teks alt.
    return "".join(_sebaris(anak) for anak in simpul.children)


def _gabung(bagian, pemisah) -> str:
    return pemisah.join(b for b in bagian if b)


def _daftar(simpul) -> str:
    berurut = simpul.type == "ordered_list"
    nomor = int(simpul.attrs.get("start", 1)) if berurut else 0
    butir = []
    for i, item in enumerate(simpul.children):
        isi = _gabung((_blok(anak) for anak in item.children), "\n")
        centang = _CENTANG.match(isi)
        if centang:
            isi = ("☐ " if centang.group(1) == " " else "☑ ") + isi[centang.end() :]
        awalan = f"{nomor + i}. " if berurut else "• "
        butir.append(awalan + isi.replace("\n", "\n  "))
    return "\n".join(butir)


def _blok(simpul) -> str:
    jenis = simpul.type
    if jenis in ("bullet_list", "ordered_list"):
        return _daftar(simpul)
    if jenis in ("paragraph", "heading"):
        return _gabung((_sebaris(anak) for anak in simpul.children), "").strip()
    if jenis in ("fence", "code_block"):
        return simpul.content.rstrip("\n")
    if jenis == "hr":
        return "---"
    if jenis == "table":
        baris = [tr for bagian in simpul.children for tr in bagian.children]
        return "\n".join(" | ".join(_sebaris(sel).strip() for sel in tr.children) for tr in baris)
    return _gabung((_blok(anak) for anak in simpul.children), "\n\n")


def teks_dari_markdown(isi) -> str:
    """Teks tanpa sintaks Markdown, baris dipertahankan. Untuk cuplikan, subjek, dan email teks."""
    sumber = (isi or "").strip()
    if not sumber:
        return ""
    # Tidak pernah mengosongkan pesan yang ada isinya (mis. hanya "#").
    return _blok(SyntaxTreeNode(_MD.parse(sumber))).strip() or sumber


# ---------------------------------------------------------------- HTML email


_F = f"font-family:{FONT};"
_TEKS = f"{_F}font-size:{UKURAN['isi_2']}px;line-height:1.55;color:{WARNA['teks']};"
_JARAK = "margin:0 0 10px;"


def _judul(ukuran) -> str:
    return f"{_JARAK}{_F}font-size:{ukuran}px;line-height:1.35;font-weight:700;color:{WARNA['teks']};"


# Inline semua: Gmail membuang <style> di sebagian klien dan Outlook mengabaikan kelas.
_GAYA_TAG = {
    "p": f"{_JARAK}{_TEKS}",
    "h1": _judul(18),
    "h2": _judul(16),
    "h3": _judul(15),
    "h4": _judul(14),
    "h5": _judul(14),
    "h6": _judul(14),
    "ul": f"{_JARAK}padding:0 0 0 22px;{_TEKS}",
    "ol": f"{_JARAK}padding:0 0 0 22px;{_TEKS}",
    "li": f"margin:0 0 4px;{_TEKS}",
    "blockquote": f"{_JARAK}padding:0 0 0 12px;border-left:3px solid {WARNA['garis']};color:{WARNA['teks_2']};",
    "a": GAYA["tautan"],
    "code": f"font-family:{FONT_MONO};font-size:13px;background-color:{WARNA['permukaan']};padding:1px 4px;",
    "pre": (
        f"{_JARAK}padding:10px 12px;background-color:{WARNA['permukaan']};border:1px solid {WARNA['garis']};"
        f"font-family:{FONT_MONO};font-size:13px;line-height:1.5;white-space:pre-wrap;"
    ),
    "table": f"{_JARAK}border-collapse:collapse;",
    "th": f"padding:5px 9px;border:1px solid {WARNA['garis']};text-align:left;font-weight:700;{_TEKS}",
    "td": f"padding:5px 9px;border:1px solid {WARNA['garis']};{_TEKS}",
    "hr": f"margin:12px 0;border:0;border-top:1px solid {WARNA['garis']};",
}
_TAG_HTML = {*_GAYA_TAG, "br", "strong", "em", "s", "thead", "tbody", "tr"}
_ATRIBUT = {tag: {"style"} for tag in _GAYA_TAG} | {"a": {"style", "href"}, "ol": {"style", "start"}}


def _tautan_boleh(alamat) -> bool:
    return str(alamat or "").lower().startswith(_SKEMA_TAUTAN)


def _rapikan_sebaris(anak) -> list:
    """Tautan yang skemanya tidak diizinkan tinggal teksnya; gambar tinggal teks alt."""
    hasil, dibuang = [], []
    for token in anak:
        if token.type == "link_open":
            dibuang.append(not _tautan_boleh(token.attrs.get("href")))
            if not dibuang[-1]:
                hasil.append(token)
        elif token.type == "link_close":
            if not dibuang.pop():
                hasil.append(token)
        elif token.type == "image":
            # Tanpa gambar: alamatnya bisa dari mana saja.
            hasil.append(Token("text", "", 0, content=token.content))
        else:
            hasil.append(token)
    return hasil


def _beri_gaya(token) -> None:
    gaya = _GAYA_TAG.get(token.tag)
    if gaya and token.nesting >= 0:
        # `style` bawaan markdown-it (perataan kolom tabel) diletakkan paling belakang supaya menang.
        token.attrSet("style", gaya + str(token.attrs.get("style") or ""))


def _blok_kode(self, tokens, idx, options, env) -> str:
    isi = escape(tokens[idx].content.rstrip("\n"), quote=False)
    return f'<pre style="{_GAYA_TAG["pre"]}">{isi}</pre>'


_MD_HTML = _pengurai()
_MD_HTML.add_render_rule("fence", _blok_kode)
_MD_HTML.add_render_rule("code_block", _blok_kode)


def html_email_dari_markdown(isi) -> str:
    """HTML aman bergaya inline untuk email. HTML mentah di sumber di-escape, lalu disaring nh3."""
    sumber = (isi or "").strip()
    if not sumber:
        return ""
    tokens = _MD_HTML.parse(sumber)
    for token in tokens:
        _beri_gaya(token)
        if token.type == "inline":
            token.children = _rapikan_sebaris(token.children or [])
            for anak in token.children:
                _beri_gaya(anak)
    # Blok tingkat atas terakhir tanpa jarak bawah, supaya kotaknya tidak bolong.
    for token in reversed(tokens):
        if token.level == 0 and token.nesting >= 0 and token.attrs.get("style"):
            token.attrSet("style", f"{token.attrs['style']}margin-bottom:0;")
            break
    html = _MD_HTML.renderer.render(tokens, _MD_HTML.options, {})
    return nh3.clean(html, tags=_TAG_HTML, attributes=_ATRIBUT, url_schemes={"http", "https", "mailto"}).strip()
