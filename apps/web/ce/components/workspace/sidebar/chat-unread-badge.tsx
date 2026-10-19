/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: lencana pesan belum dibaca
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import useSWR from "swr";
// components
import { CountChip } from "@/components/common/count-chip";
// services
import { ChatService, KUNCI_BELUM_DIBACA } from "@/services/chat.service";

const chatService = new ChatService();

// Bunyi dan pop-up TIDAK lagi di sini. Keduanya pindah ke PenjagaNotifikasi,
// yang memakai kunci SWR yang sama persis dengan berkas ini. Kalau bunyinya
// dikembalikan ke sini, satu pesan masuk akan berbunyi DUA KALI: SWR menyajikan
// data yang sama ke kedua komponen, dan keduanya melihat angka yang sama naik.
//
// Lencana ini TIDAK memutar jamnya sendiri. PenjagaNotifikasi memakai kunci SWR
// yang persis sama dan menyegarkannya tiap 15 detik dari halaman mana pun, jadi
// menambahkan `refreshInterval` di sini cuma menggandakan permintaan tanpa
// membuat angkanya lebih baru sedetik pun. Saat percakapan dibuka, halaman
// Obrolan memanggil mutate pada kunci yang sama sehingga angkanya turun
// seketika, tanpa menunggu putaran berikutnya.

type Props = { workspaceSlug: string };

export const ChatUnreadBadge = observer(function ChatUnreadBadge({ workspaceSlug }: Props) {
  const { data: status } = useSWR(
    workspaceSlug ? KUNCI_BELUM_DIBACA : null,
    workspaceSlug ? () => chatService.getStatus(workspaceSlug) : null
  );

  const jumlah = status?.jumlah ?? 0;

  if (jumlah <= 0) return <></>;

  return (
    <div className="ml-auto">
      <CountChip count={jumlah > 99 ? "99+" : `${jumlah}`} />
    </div>
  );
});
