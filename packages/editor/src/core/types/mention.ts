/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane types
import type { TSearchEntities } from "@plane/types";

export type TMentionSuggestion = {
  entity_identifier: string;
  entity_name: TSearchEntities;
  icon: React.ReactNode;
  id: string;
  // Paradise: penanda saja (mis. orang di luar departemen). Tampil abu-abu dan tidak bisa dipilih.
  isDisabled?: boolean;
  subTitle?: string;
  title: string;
};

export type TMentionSection = {
  key: string;
  title?: string;
  items: TMentionSuggestion[];
};

export type TCallbackMentionComponentProps = Pick<TMentionSuggestion, "entity_identifier" | "entity_name">;

export type TMentionHandler = {
  getMentionedEntityDetails?: (entity_identifier: string) => { display_name: string } | undefined;
  renderComponent: (props: TCallbackMentionComponentProps) => React.ReactNode;
  searchCallback?: (query: string) => Promise<TMentionSection[]>;
  // Paradise (KEP-91): pencarian untuk pemicu `#` (kanal chat dan work item).
  searchHashCallback?: (query: string) => Promise<TMentionSection[]>;
  // Paradise (KEP-91): teks petunjuk di kaki dropdown (editor tak punya i18n, teks dari app web).
  tip?: string;
  // Paradise (KEP-91): label teks untuk mention non-orang (@all, #kanal, #nomor) saat disalin/diserialisasi.
  getMentionedEntityLabel?: (entity_name: string, entity_identifier: string) => string | undefined;
};
