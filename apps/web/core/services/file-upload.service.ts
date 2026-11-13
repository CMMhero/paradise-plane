/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { AxiosRequestConfig } from "axios";
import axios from "axios";
// plane imports
import { retryTransient } from "@plane/services";
// services
import { APIService } from "@/services/api.service";

export class FileUploadService extends APIService {
  private cancelSource: ReturnType<typeof axios.CancelToken.source> | undefined;

  constructor() {
    super("");
  }

  /**
   * Sends the file to its presigned URL.
   *
   * Paradise: a dropped connection or a 5xx from the proxy is retried (the presigned
   * POST is safe to repeat), and the error thrown is always a normalized TUploadError.
   * It used to be `error?.response?.data`, which is `undefined` for a network failure,
   * so the caller could not tell "offline" from "file rejected" and showed nothing.
   * A canceled upload now throws code "cancelled" instead of resolving, otherwise the
   * caller went on to mark the never-uploaded asset as uploaded.
   */
  async uploadFile(
    url: string,
    data: FormData,
    uploadProgressHandler?: AxiosRequestConfig["onUploadProgress"]
  ): Promise<void> {
    // oxlint-disable-next-line import/no-named-as-default-member -- kept as is: restructuring it is out of scope for this release
    const source = axios.CancelToken.source();
    this.cancelSource = source;
    return retryTransient(() =>
      this.post(url, data, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
        cancelToken: source.token,
        withCredentials: false,
        onUploadProgress: uploadProgressHandler,
      }).then((response) => response?.data)
    );
  }

  cancelUpload() {
    this.cancelSource?.cancel("Upload canceled");
  }
}
