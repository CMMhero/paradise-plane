/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { IUserLite } from "../users";
import type {
  TInstanceAIConfigurationKeys,
  TInstanceParadiseConfigurationKeys,
  TParadiseModule,
  TInstanceEmailConfigurationKeys,
  TInstanceImapConfigurationKeys,
  TInstanceImageConfigurationKeys,
  TInstanceAuthenticationKeys,
  TInstanceWorkspaceConfigurationKeys,
  TCoreLoginMediums,
} from "./";
import type { TExtendedLoginMediums } from "./auth-ee";

export interface IInstanceInfo {
  instance: IInstance;
  config: IInstanceConfig;
}

export interface IInstance {
  id: string;
  created_at: string;
  updated_at: string;
  instance_name: string | undefined;
  whitelist_emails: string | undefined;
  instance_id: string | undefined;
  license_key: string | undefined;
  current_version: string | undefined;
  latest_version: string | undefined;
  last_checked_at: string | undefined;
  namespace: string | undefined;
  is_telemetry_enabled: boolean;
  is_support_required: boolean;
  is_activated: boolean;
  is_setup_done: boolean;
  is_signup_screen_visited: boolean;
  user_count: number | undefined;
  is_verified: boolean;
  created_by: string | undefined;
  updated_by: string | undefined;
  workspaces_exist: boolean;
}

/** `config.paradise_limits` dari GET /api/instances/ (registry setelan God Mode). */
export type TParadiseLimits = {
  upload_max_mb?: number;
  chat_message_max_length?: number;
  chat_attachments_max?: number;
  /** Jam sesudah dikirim, pesan obrolan masih bisa disunting. 0 = tanpa batas. */
  chat_edit_window_hours?: number;
  /** Batas atas arsip otomatis dalam hari. 0 = instance tidak membatasi. */
  auto_archive_done_days?: number;
  chat_delete_window_hours?: number;
  office_timezone?: string;
};

export interface IInstanceConfig {
  enable_signup: boolean;
  is_workspace_creation_disabled: boolean;
  is_google_enabled: boolean;
  is_github_enabled: boolean;
  is_gitlab_enabled: boolean;
  is_gitea_enabled: boolean;
  is_magic_login_enabled: boolean;
  /** Deployment ini menjalankan bidang kendali SaaS (panel pemilik produk). */
  is_control_plane_enabled?: boolean;
  /** Modul yang dinyalakan/dimatikan Super Admin di God Mode > Features. Tidak ada = server lama, anggap menyala. */
  paradise_modules?: Partial<Record<TParadiseModule, boolean>>;
  /** Hari tenggang sesudah Due date sebelum terlambat (God Mode > Features). Tidak ada = server lama, 0. */
  paradise_overdue_grace_days?: number;
  /** KEP-84: tugas yang menunggu persetujuan selesai tidak terlambat (God Mode APPROVAL_PENDING_NOT_LATE). Tidak ada = server lama, false. */
  paradise_approval_pending_not_late?: boolean;
  /** Jam sesudah dikirim, pesan obrolan masih bisa dihapus pengirimnya. 0 = tanpa batas. Tidak ada = server lama, tanpa batas. */
  paradise_chat_delete_window_hours?: number;
  /** Batas yang diatur Super Admin di God Mode. Tidak ada = server lama, pakai bawaan klien. */
  paradise_limits?: TParadiseLimits;
  /** Bawaan project baru dari God Mode. Tidak ada = server lama, pakai bawaan formulir. */
  paradise_project_defaults?: {
    /** 2 = Public, 0 = Private. */
    network: 0 | 2;
    timezone: string;
    archive_in: number;
    close_in: number;
    guest_view_all_features: boolean;
  };
  is_email_password_enabled: boolean;
  github_app_name: string | undefined;
  slack_client_id: string | undefined;
  posthog_api_key: string | undefined;
  posthog_host: string | undefined;
  has_unsplash_configured: boolean;
  has_llm_configured: boolean;
  /** Client ID + secret Google Calendar terisi. Tidak ada = server lama, anggap terisi. */
  has_google_calendar_configured?: boolean;
  file_size_limit: number | undefined;
  is_smtp_configured: boolean;
  app_base_url: string | undefined;
  space_base_url: string | undefined;
  admin_base_url: string | undefined;
  is_self_managed: boolean;
  instance_changelog_url?: string;
}

export interface IInstanceAdmin {
  created_at: string;
  created_by: string;
  id: string;
  instance: string;
  role: string;
  updated_at: string;
  updated_by: string;
  user: string;
  user_detail: IUserLite;
}

export type TInstanceConfigurationKeys =
  | TInstanceAIConfigurationKeys
  | TInstanceEmailConfigurationKeys
  | TInstanceImapConfigurationKeys
  | TInstanceImageConfigurationKeys
  | TInstanceAuthenticationKeys
  | TInstanceWorkspaceConfigurationKeys
  | TInstanceParadiseConfigurationKeys;

export interface IInstanceConfiguration {
  id: string;
  created_at: string;
  updated_at: string;
  key: TInstanceConfigurationKeys;
  value: string;
  created_by: string | null;
  updated_by: string | null;
}

export type IFormattedInstanceConfiguration = {
  [key in TInstanceConfigurationKeys]: string;
};

export type TLoginMediums = TCoreLoginMediums | TExtendedLoginMediums;
