/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pratinjau email di God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import { APIService } from "../api.service";

export type TEmailPreviewLang = "id" | "en";

export type TEmailPreviewItem = {
  key: string;
  subject: string;
  /** The template threw while rendering; `subject` holds the error class. */
  error: boolean;
};

export type TEmailPreviewList = {
  lang: TEmailPreviewLang;
  results: TEmailPreviewItem[];
};

export type TEmailPreview = {
  key: string;
  lang: TEmailPreviewLang;
  subject: string;
  /** Full HTML document, inline images already rewritten to data: URIs. */
  html: string;
  text: string;
  attachments: string[];
};

/** Read-only: renders sample emails on the server, never opens SMTP. */
export class InstanceEmailPreviewService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async list(lang: TEmailPreviewLang): Promise<TEmailPreviewList> {
    return this.get("/api/instances/email-preview/", { params: { lang } })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data ?? error;
      });
  }

  async retrieve(key: string, lang: TEmailPreviewLang): Promise<TEmailPreview> {
    return this.get(`/api/instances/email-preview/${encodeURIComponent(key)}/`, { params: { lang } })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data ?? error;
      });
  }
}
