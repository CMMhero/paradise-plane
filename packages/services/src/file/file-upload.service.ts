/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import axios from "axios";
// api service
import { APIService } from "../api.service";
// local imports
import { retryTransient } from "./upload-error";

/**
 * Service class for handling file upload operations
 * Handles file uploads
 * @extends {APIService}
 */
export class FileUploadService extends APIService {
  private cancelSource: ReturnType<typeof axios.CancelToken.source> | undefined;

  constructor() {
    super("");
  }

  /**
   * Uploads a file to the specified signed URL
   * @param {string} url - The URL to upload the file to
   * @param {FormData} data - The form data to upload
   * @returns {Promise<void>} Promise resolving to void
   * @throws {TUploadError} If the request fails after the transient-failure retries
   * (code "cancelled" when the upload was canceled, so callers do not mark it as uploaded)
   */
  async uploadFile(url: string, data: FormData): Promise<void> {
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
      }).then((response) => response?.data)
    );
  }

  /**
   * Cancels the upload
   */
  cancelUpload() {
    this.cancelSource?.cancel("Upload canceled");
  }
}
