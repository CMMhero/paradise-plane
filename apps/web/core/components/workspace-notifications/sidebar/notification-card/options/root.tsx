/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import type { ReactElement } from "react";
import { observer } from "mobx-react";
import { ArchiveRestore, CalendarClock, Clock, MailCheck, MailOpen, MoreHorizontal } from "lucide-react";
// plane imports
import { NOTIFICATION_SNOOZE_OPTIONS } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { IconButton } from "@plane/propel/icon-button";
import { ArchiveIcon } from "@plane/propel/icons";
import { Popover } from "@plane/propel/popover";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
// hooks
import { useNotification } from "@/hooks/store/notifications/use-notification";
// local imports
import type { TNotificationItemVariant } from "../item";
import { NotificationSnoozeModal } from "./snooze";

type TNotificationItemActions = {
  workspaceSlug: string;
  notificationId: string;
  variant: TNotificationItemVariant;
};

type TActionRow = {
  icon: ReactElement;
  label: string;
  onClick: () => void;
};

function ActionRow({ icon, label, onClick }: TActionRow) {
  return (
    <Button variant="ghost" size="sm" prependIcon={icon} onClick={onClick} className="w-full justify-start">
      <span className="min-w-0 flex-1 truncate text-left">{label}</span>
    </Button>
  );
}

/**
 * Kustomisasi Paradise: satu tombol "..." per baris menggantikan tiga ikon 20px
 * yang hanya muncul saat kursor lewat. Ikon-ikon itu tidak pernah terlihat di
 * layar sentuh (tidak ada hover), dan popover snooze lamanya `absolute` di dalam
 * daftar yang menggulir sehingga terpotong di baris bawah.
 *
 * Panelnya propel Popover (Base UI): diportal, jadi tidak terpotong, dan saat
 * dipakai di dalam popover Inbox ia ikut pohon floating yang sama, sehingga
 * klik di sini tidak dianggap "klik di luar" yang menutup popover Inbox.
 *
 * Snooze "Custom" membuka modal (ModalCore) yang BUKAN bagian pohon itu; di
 * varian popover pilihan itu disembunyikan dan tersedia di tampilan penuh.
 */
export const NotificationItemActions = observer(function NotificationItemActions({
  workspaceSlug,
  notificationId,
  variant,
}: TNotificationItemActions) {
  const { t } = useTranslation();
  const notification = useNotification(notificationId);
  const {
    asJson: data,
    markNotificationAsRead,
    markNotificationAsUnRead,
    archiveNotification,
    unArchiveNotification,
    snoozeNotification,
    unSnoozeNotification,
  } = notification;
  const [isOpen, setIsOpen] = useState(false);
  const [isCustomSnoozeOpen, setIsCustomSnoozeOpen] = useState(false);

  const snoozeOptions = NOTIFICATION_SNOOZE_OPTIONS.filter(
    (option) => option.value !== undefined || variant === "split"
  );

  const run = async (action: () => Promise<unknown>, successTitle: string) => {
    setIsOpen(false);
    try {
      await action();
      setToast({ type: TOAST_TYPE.SUCCESS, title: successTitle });
    } catch (error) {
      console.error(error);
      setToast({ type: TOAST_TYPE.ERROR, title: t("common.error.label"), message: t("common.error.message") });
    }
  };

  const handleRead = () =>
    data.read_at
      ? run(() => markNotificationAsUnRead(workspaceSlug), t("notification.toasts.unread"))
      : run(() => markNotificationAsRead(workspaceSlug), t("notification.toasts.read"));

  const handleArchive = () =>
    data.archived_at
      ? run(() => unArchiveNotification(workspaceSlug), t("notification.toasts.unarchived"))
      : run(() => archiveNotification(workspaceSlug), t("notification.toasts.archived"));

  const handleSnooze = (snoozeTill: Date | undefined) =>
    snoozeTill
      ? run(() => snoozeNotification(workspaceSlug, snoozeTill), t("notification.toasts.snoozed"))
      : run(() => unSnoozeNotification(workspaceSlug), t("notification.toasts.unsnoozed"));

  const handleCustomSnooze = () => {
    setIsOpen(false);
    setIsCustomSnoozeOpen(true);
  };

  return (
    <>
      <Popover open={isOpen} onOpenChange={setIsOpen}>
        <Popover.Button
          render={
            <IconButton
              variant="ghost"
              size="sm"
              icon={MoreHorizontal}
              aria-label={t("notification_ui.item_actions")}
              title={t("notification_ui.item_actions")}
              // Tersembunyi sampai baris disorot/difokus; selalu tampil di layar sentuh
              // dan selama menunya terbuka. opacity, bukan hidden, supaya tetap bisa di-Tab.
              className="shrink-0 opacity-0 group-focus-within:opacity-100 group-hover:opacity-100 focus-visible:opacity-100 data-[popup-open]:opacity-100 sentuh:opacity-100"
            />
          }
        />
        <Popover.Panel
          side="bottom"
          align="end"
          sideOffset={4}
          // z di positioner (elemen yang benar-benar diposisikan), di atas popover Inbox (z-30).
          positionerClassName="z-40"
          className="flex w-52 flex-col gap-0.5 rounded-popover border-[0.5px] border-strong bg-surface-1 p-1.5 shadow-raised-200"
        >
          <ActionRow
            icon={data.read_at ? <MailOpen /> : <MailCheck />}
            label={data.read_at ? t("notification.options.mark_unread") : t("notification.options.mark_read")}
            onClick={() => void handleRead()}
          />
          <ActionRow
            icon={data.archived_at ? <ArchiveRestore /> : <ArchiveIcon />}
            label={data.archived_at ? t("notification.options.mark_unarchive") : t("notification.options.mark_archive")}
            onClick={() => void handleArchive()}
          />
          <p className="px-2 pt-2 pb-1 text-caption-sm-medium text-tertiary">{t("notification_ui.snooze_heading")}</p>
          {data.snoozed_till && (
            <ActionRow
              icon={<Clock />}
              label={t("notification.options.mark_unsnooze")}
              onClick={() => void handleSnooze(undefined)}
            />
          )}
          {snoozeOptions.map((option) => (
            <ActionRow
              key={option.key}
              icon={option.value ? <Clock /> : <CalendarClock />}
              label={t(option.i18n_label)}
              onClick={() => (option.value ? void handleSnooze(option.value()) : handleCustomSnooze())}
            />
          ))}
        </Popover.Panel>
      </Popover>
      {variant === "split" && (
        <NotificationSnoozeModal
          isOpen={isCustomSnoozeOpen}
          onClose={() => setIsCustomSnoozeOpen(false)}
          onSubmit={async (snoozeTill) => {
            setIsCustomSnoozeOpen(false);
            await handleSnooze(snoozeTill);
          }}
        />
      )}
    </>
  );
});
