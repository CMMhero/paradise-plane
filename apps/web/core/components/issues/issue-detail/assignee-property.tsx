/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: assignee yang bisa dibuka profilnya
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Baris Assignees di sidebar detail dan peek. Tiap assignee tampil sebagai nama
 * yang membuka kartu profil; pengubahan pindah ke tombol pensil di ujung baris.
 * Dulu seluruh baris adalah tombol dropdown, jadi klik nama orang selalu membuka
 * pemilih assignee dan profilnya tidak bisa dicapai dari sini.
 */

import { observer } from "mobx-react";
import { Pencil } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";
// components
import { MemberDropdown } from "@/components/dropdowns/member/dropdown";
import { MemberNameChip } from "@/components/member-profile";

type Props = {
  value: string[];
  onChange: (val: string[]) => void;
  disabled: boolean;
  memberIds?: string[];
  projectId: string;
  buttonClassName?: string;
};

export const AssigneeProperty = observer(function AssigneeProperty({
  value,
  onChange,
  disabled,
  memberIds,
  projectId,
  buttonClassName,
}: Props) {
  const { t } = useTranslation();
  const dropdownProps = {
    value,
    onChange,
    disabled,
    memberIds,
    projectId,
    placeholder: t("issue.add.assignee"),
    multiple: true as const,
  };

  // Belum ada assignee: tidak ada profil untuk dibuka, baris tetap tombol pemilih.
  if (value.length === 0)
    return (
      <MemberDropdown
        {...dropdownProps}
        buttonVariant="transparent-with-text"
        className="group w-full grow"
        buttonContainerClassName="w-full text-left h-7.5"
        buttonClassName={cn("justify-between text-placeholder", buttonClassName)}
        hideIcon
        dropdownArrow
        dropdownArrowClassName="h-3.5 w-3.5 hidden group-hover:inline"
      />
    );

  return (
    <div className="group flex w-full min-w-0 items-start gap-1 py-0.5">
      <div className="flex min-w-0 flex-1 flex-wrap items-center gap-x-1 gap-y-0.5">
        {value.map((id) => (
          <MemberNameChip key={id} userId={id} />
        ))}
      </div>
      {disabled ? null : (
        <MemberDropdown
          {...dropdownProps}
          buttonVariant="transparent-without-text"
          className="shrink-0"
          buttonContainerClassName="grid size-6 place-items-center rounded-sm text-tertiary hover:bg-layer-transparent-hover hover:text-primary"
          button={
            <>
              <Pencil className="size-3.5" aria-hidden />
              <span className="sr-only">{t("issue.add.assignee")}</span>
            </>
          }
        />
      )}
    </div>
  );
});
