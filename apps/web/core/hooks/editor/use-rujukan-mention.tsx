/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback } from "react";
import { Hash, Lock, Users } from "lucide-react";
// plane editor
import type { TMentionSection } from "@plane/editor";
import { useTranslation } from "@plane/i18n";
// services
import { ChatService } from "@/services/chat.service";
// local
import { setRujukanLabel } from "./rujukan-label-cache";

const chatService = new ChatService();

// Kata kunci yang memunculkan @all: awalan "all", "everyone", atau "semua".
const EVERYONE_KEYWORDS = ["all", "everyone", "semua"];

export const isEveryoneQuery = (query: string): boolean => {
  const q = query.trim().toLowerCase();
  return q === "" || EVERYONE_KEYWORDS.some((word) => word.startsWith(q));
};

type TArgs = {
  workspaceSlug?: string;
};

// Paradise (KEP-91): bagian "Everyone" untuk `@` dan pencarian `#` (kanal + work item).
export const useRujukanMention = ({ workspaceSlug }: TArgs) => {
  const { t } = useTranslation();

  const getEveryoneSection = useCallback(
    (query: string): TMentionSection[] =>
      isEveryoneQuery(query)
        ? [
            {
              key: "everyone",
              title: t("rujukan_ui.section_everyone"),
              items: [
                {
                  id: "everyone",
                  entity_identifier: "all",
                  entity_name: "everyone_mention",
                  icon: <Users className="size-3.5 text-secondary" />,
                  title: "@all",
                  subTitle: t("rujukan_ui.everyone_project"),
                },
              ],
            },
          ]
        : [],
    [t]
  );

  const fetchHashMentions = useCallback(
    async (query: string): Promise<TMentionSection[]> => {
      if (!workspaceSlug) return [];
      const res = await chatService.cariRujukan(workspaceSlug, query, 5);
      const sections: TMentionSection[] = [];
      if (res.kanal.length > 0) {
        sections.push({
          key: "channels",
          title: t("rujukan_ui.section_channels"),
          items: res.kanal.map((kanal) => {
            setRujukanLabel("channel_mention", kanal.id, kanal.nama);
            return {
              id: kanal.id,
              entity_identifier: kanal.id,
              entity_name: "channel_mention" as const,
              icon:
                kanal.tipe === "privat" ? (
                  <Lock className="size-3.5 text-secondary" />
                ) : (
                  <Hash className="size-3.5 text-secondary" />
                ),
              title: kanal.nama,
            };
          }),
        });
      }
      if (res.tugas.length > 0) {
        sections.push({
          key: "work-items",
          title: t("rujukan_ui.section_work_items"),
          items: res.tugas.map((tugas) => {
            setRujukanLabel("issue_mention", tugas.id, tugas.nomor);
            return {
              id: tugas.id,
              entity_identifier: tugas.id,
              entity_name: "issue_mention" as const,
              icon: <Hash className="size-3.5 text-secondary" />,
              subTitle: tugas.nomor,
              title: tugas.judul,
            };
          }),
        });
      }
      return sections;
    },
    [t, workspaceSlug]
  );

  return {
    getEveryoneSection,
    fetchHashMentions,
    tip: t("rujukan_ui.tip_short"),
  };
};
