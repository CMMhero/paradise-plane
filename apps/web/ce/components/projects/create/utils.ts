/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { RANDOM_EMOJI_CODES } from "@plane/constants";
import type { IInstanceConfig, IProject } from "@plane/types";
import { getRandomCoverImage } from "@/helpers/cover-image.helper";

/**
 * Nilai awal formulir "Create project".
 *
 * Paradise: visibilitas, zona waktu, arsip/tutup otomatis, dan akses guest
 * mengikuti bawaan project yang diatur Super Admin di God Mode
 * (`paradise_project_defaults`). Server lama tanpa bawaan itu = perilaku upstream.
 */
export const getProjectFormValues = (config?: IInstanceConfig): Partial<IProject> => {
  const bawaan = config?.paradise_project_defaults;
  return {
    cover_image_url: getRandomCoverImage(),
    description: "",
    logo_props: {
      in_use: "emoji",
      emoji: {
        value: RANDOM_EMOJI_CODES[Math.floor(Math.random() * RANDOM_EMOJI_CODES.length)],
      },
    },
    identifier: "",
    name: "",
    network: bawaan?.network ?? 2,
    project_lead: null,
    ...(bawaan && {
      timezone: bawaan.timezone,
      archive_in: bawaan.archive_in,
      close_in: bawaan.close_in,
      guest_view_all_features: bawaan.guest_view_all_features,
    }),
  };
};
