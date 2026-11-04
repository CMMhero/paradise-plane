/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import { MAX_FILE_SIZE } from "@plane/constants";
// hooks
import { useInstance } from "@/hooks/store/use-instance";
import { useParadiseLimits } from "@/hooks/use-paradise-limits";

type TReturnProps = {
  maxFileSize: number;
};

export const useFileSize = (): TReturnProps => {
  // store hooks
  const { config } = useInstance();
  const { upload_max_mb } = useParadiseLimits();

  return {
    // file_size_limit = batas byte yang persis dijaga server (UPLOAD_MAX_MB dari God Mode,
    // dijepit batas proxy). upload_max_mb hanya cadangan untuk server lama tanpa angka byte.
    maxFileSize: config?.file_size_limit ?? (upload_max_mb ? upload_max_mb * 1024 * 1024 : MAX_FILE_SIZE),
  };
};
