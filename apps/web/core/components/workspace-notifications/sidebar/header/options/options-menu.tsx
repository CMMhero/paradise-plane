/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: satu menu opsi Inbox
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ReactElement } from "react";
import { observer } from "mobx-react";
import { CheckCircle, Clock, MoreVertical, RefreshCw } from "lucide-react";
// plane imports
import type { ENotificationFilterType } from "@plane/constants";
import { ENotificationLoader, ENotificationQueryParamType, FILTER_TYPE_OPTIONS } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { IconButton } from "@plane/propel/icon-button";
import { ArchiveIcon, CheckIcon } from "@plane/propel/icons";
import { Popover } from "@plane/propel/popover";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Spinner } from "@plane/ui";
// hooks
import { useWorkspaceNotifications } from "@/hooks/store/notifications";

type TOptionRow = {
  icon: ReactElement;
  label: string;
  isChecked?: boolean;
  onClick: () => void;
};

function OptionRow({ icon, label, isChecked, onClick }: TOptionRow) {
  return (
    <Button
      variant="ghost"
      size="sm"
      prependIcon={icon}
      appendIcon={isChecked ? <CheckIcon /> : undefined}
      aria-pressed={isChecked}
      onClick={onClick}
      className="w-full justify-start"
    >
      <span className="min-w-0 flex-1 truncate text-left">{label}</span>
    </Button>
  );
}

function SectionLabel({ children }: { children: string }) {
  return <p className="px-2 pt-2 pb-1 text-caption-sm-medium text-tertiary">{children}</p>;
}

/**
 * Refresh + filter jenis + filter tampilan (belum dibaca / diarsip / ditunda).
 * Menggabungkan dua PopoverMenu upstream (`filters/menu`, `header/options/menu-option`).
 *
 * propel Popover (Base UI), bukan PopoverMenu headless: di dalam popover lonceng
 * ia menjadi popover bersarang di pohon floating yang sama, jadi klik di menu
 * tidak menutup popover Inbox. Menu tetap terbuka sesudah filter diklik supaya
 * beberapa filter bisa dipasang sekaligus.
 */
export const NotificationOptionsMenu = observer(function NotificationOptionsMenu({
  workspaceSlug,
}: {
  workspaceSlug: string;
}) {
  const { t } = useTranslation();
  const { loader, filters, getNotifications, updateFilters, updateBulkFilters } = useWorkspaceNotifications();
  const isFiltered =
    Object.values(filters.type || {}).some(Boolean) || filters.read || filters.archived || filters.snoozed;
  const label = t("notification_ui.inbox_options");

  const handleRefresh = async () => {
    if (loader) return;
    try {
      await getNotifications(workspaceSlug, ENotificationLoader.MUTATION_LOADER, ENotificationQueryParamType.CURRENT);
    } catch (error) {
      console.error(error);
      setToast({ type: TOAST_TYPE.ERROR, title: t("common.error.label"), message: t("common.error.message") });
    }
  };

  const toggleType = (type: ENotificationFilterType) =>
    updateFilters("type", { ...filters.type, [type]: !filters.type?.[type] });

  return (
    <Popover>
      <div className="relative flex shrink-0">
        <Popover.Button
          render={<IconButton variant="ghost" size="base" icon={MoreVertical} aria-label={label} title={label} />}
        />
        {isFiltered && (
          // Penanda filter aktif: daftar yang tersaring tidak terlihat beda dari daftar kosong.
          <span
            aria-hidden
            className="pointer-events-none absolute top-1 right-1 size-1.5 rounded-full bg-accent-primary"
          />
        )}
      </div>
      <Popover.Panel
        side="bottom"
        align="end"
        sideOffset={4}
        positionerClassName="z-40"
        className="flex max-h-[min(28rem,calc(100dvh-6rem))] w-60 flex-col gap-0.5 overflow-y-auto rounded-popover border-[0.5px] border-strong bg-surface-1 p-1.5 shadow-raised-200"
      >
        <OptionRow
          icon={loader === ENotificationLoader.MUTATION_LOADER ? <Spinner /> : <RefreshCw />}
          label={t("notification.options.refresh")}
          onClick={() => void handleRefresh()}
        />

        <SectionLabel>{t("notification_ui.filter_heading")}</SectionLabel>
        {FILTER_TYPE_OPTIONS.map((option) => (
          <OptionRow
            key={option.value}
            icon={<CheckCircle />}
            label={t(option.i18n_label)}
            isChecked={!!filters.type?.[option.value]}
            onClick={() => toggleType(option.value)}
          />
        ))}

        <SectionLabel>{t("notification_ui.view_heading")}</SectionLabel>
        <OptionRow
          icon={<CheckCircle />}
          label={t("notification.options.show_unread")}
          isChecked={filters.read}
          onClick={() => updateFilters("read", !filters.read)}
        />
        <OptionRow
          icon={<ArchiveIcon />}
          label={t("notification.options.show_archived")}
          isChecked={filters.archived}
          onClick={() => updateBulkFilters({ archived: !filters.archived, snoozed: false })}
        />
        <OptionRow
          icon={<Clock />}
          label={t("notification.options.show_snoozed")}
          isChecked={filters.snoozed}
          onClick={() => updateBulkFilters({ snoozed: !filters.snoozed, archived: false })}
        />
      </Popover.Panel>
    </Popover>
  );
});
