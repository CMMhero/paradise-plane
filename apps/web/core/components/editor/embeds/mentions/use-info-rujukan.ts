/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useParams } from "next/navigation";
import useSWR from "swr";
// hooks
import { setRujukanLabel } from "@/hooks/editor/rujukan-label-cache";
// services
import { ChatService } from "@/services/chat.service";

const chatService = new ChatService();

// Paradise (KEP-91): detail satu kanal/work item yang dirujuk, di-cache SWR per id.
export const useInfoKanal = (id: string) => {
  const { workspaceSlug } = useParams();
  const slug = workspaceSlug?.toString();
  const { data, isLoading } = useSWR(slug && id ? ["rujukan-kanal", slug, id] : null, async () => {
    const res = await chatService.infoRujukan(slug!, [id], []);
    const info = res.kanal[id];
    if (info?.boleh && info.nama) setRujukanLabel("channel_mention", id, info.nama);
    return info;
  });
  return { slug, info: data, isLoading };
};

export const useInfoTugas = (id: string) => {
  const { workspaceSlug } = useParams();
  const slug = workspaceSlug?.toString();
  const { data, isLoading } = useSWR(slug && id ? ["rujukan-tugas", slug, id] : null, async () => {
    const res = await chatService.infoRujukan(slug!, [], [id]);
    const info = res.tugas[id];
    if (info?.boleh && info.nomor) setRujukanLabel("issue_mention", id, info.nomor);
    return info;
  });
  return { slug, info: data, isLoading };
};
