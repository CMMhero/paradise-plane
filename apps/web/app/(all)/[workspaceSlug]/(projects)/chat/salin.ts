/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: salin isi pesan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/** Cara lama lewat textarea tersembunyi + execCommand. Usang, tapi satu-satunya
 * yang jalan di halaman non-HTTPS (server lokal lewat IP LAN), tempat
 * `navigator.clipboard` tidak ada sama sekali. */
const salinCaraLama = (teks: string): boolean => {
  const area = document.createElement("textarea");
  area.value = teks;
  area.setAttribute("readonly", "");
  area.style.position = "fixed";
  area.style.top = "0";
  area.style.left = "0";
  area.style.opacity = "0";
  document.body.appendChild(area);
  area.select();
  try {
    return document.execCommand("copy");
  } catch {
    return false;
  } finally {
    document.body.removeChild(area);
  }
};

/**
 * Salin teks ke papan klip. Kembalikan true kalau berhasil.
 *
 * `copyTextToClipboard` dari @plane/utils hanya jatuh ke cara lama kalau API-nya
 * tidak ada, bukan kalau API-nya MENOLAK (izin, dokumen tidak fokus). Di sini
 * keduanya jatuh ke cara lama, supaya toast "Disalin" tidak pernah berbohong.
 */
export const salinTeks = async (teks: string): Promise<boolean> => {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(teks);
      return true;
    } catch {
      return salinCaraLama(teks);
    }
  }
  return salinCaraLama(teks);
};
