/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect } from "react";

type PageHeadTitleProps = {
  title?: string;
  description?: string;
};

export function PageHead(props: PageHeadTitleProps) {
  const { title } = props;

  // Nilai baliknya dulu KODE MATI: ia ditulis di belakang `??`, padahal
  // `if (title)` sudah menyingkirkan satu-satunya kasus yang bisa memicunya.
  // Akibatnya judul kosong tidak menyetel apa pun, dan judul halaman SEBELUMNYA
  // tertinggal di tab peramban. Terlihat di halaman wiki tanpa nama: tabnya
  // masih menulis judul halaman yang dibuka sebelumnya.
  //
  // Diperbaiki di sini, bukan di halaman pemanggilnya, karena SETIAP halaman
  // yang mengirim judul kosong terkena hal yang sama. Satu penjaga di tempat
  // semua pemanggil lewat lebih kecil daripada penjaga di tiap pemanggil.
  useEffect(() => {
    document.title = title || "Paradise Task Tracker | Manajemen proyek & issue internal kantor.";
  }, [title]);

  return null;
}
