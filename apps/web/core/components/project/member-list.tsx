/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
// plane imports
import { EUserPermissions, EUserPermissionsLevel, MEMBER_TRACKER_ELEMENTS } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { SearchIcon } from "@plane/propel/icons";
import { Input } from "@plane/ui";
// components
import { MembersSettingsLoader } from "@/components/ui/loader/settings/members";
// hooks
import { useMember } from "@/hooks/store/use-member";
import { useUserPermissions } from "@/hooks/store/user";
// local imports
import { MemberListFiltersDropdown } from "./dropdowns/filters/member-list";
import { ProjectMemberListItem } from "./member-list-item";
import { SendProjectInvitationModal } from "./send-project-invitation-modal";

type TProjectMemberListProps = {
  projectId: string;
  workspaceSlug: string;
};

export const ProjectMemberList = observer(function ProjectMemberList(props: TProjectMemberListProps) {
  const { projectId, workspaceSlug } = props;
  // states
  const [inviteModal, setInviteModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const {
    project: { projectMemberIds, getFilteredProjectMemberDetails, filters },
  } = useMember();
  const { allowPermissions } = useUserPermissions();

  const { t } = useTranslation();

  const searchedProjectMembers = (projectMemberIds ?? []).filter((userId) => {
    const memberDetails = projectId ? getFilteredProjectMemberDetails(userId, projectId.toString()) : null;

    if (!memberDetails?.member || !memberDetails.original_role) return false;

    const fullName = `${memberDetails?.member.first_name} ${memberDetails?.member.last_name}`.toLowerCase();
    const displayName = memberDetails?.member.display_name.toLowerCase();

    return displayName?.includes(searchQuery.toLowerCase()) || fullName.includes(searchQuery.toLowerCase());
  });

  const memberDetails = searchedProjectMembers?.map((memberId) =>
    projectId ? getFilteredProjectMemberDetails(memberId, projectId.toString()) : null
  );

  // layar sentuh: jangan fokus otomatis, keyboard virtual menutup separuh layar
  const autoFocusSearch = typeof window !== "undefined" && !window.matchMedia("(pointer: coarse)").matches;
  const isAdmin = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.PROJECT);

  // Handler for role filter updates
  const handleRoleFilterUpdate = (role: string) => {
    if (projectId) {
      const currentFilters = filters.getFilters(projectId);
      const currentRoles = currentFilters?.roles || [];
      const updatedRoles = currentRoles.includes(role)
        ? currentRoles.filter((r) => r !== role)
        : [...currentRoles, role];

      filters.updateFilters(projectId, {
        roles: updatedRoles.length > 0 ? updatedRoles : undefined,
      });
    }
  };

  // Get current role filters
  const appliedRoleFilters = projectId ? filters.getFilters(projectId)?.roles || [] : [];

  return (
    <>
      <SendProjectInvitationModal
        isOpen={inviteModal}
        onClose={() => setInviteModal(false)}
        projectId={projectId}
        workspaceSlug={workspaceSlug}
      />
      {/* Telepon: kontrol membungkus ke baris kedua, kolom cari memakai sisa lebar */}
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b border-subtle py-2">
        <div className="text-14 font-semibold">{t("common.members")}</div>
        <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:flex-nowrap">
          <div className="flex min-h-10 min-w-40 flex-1 items-center justify-start gap-1.5 search-field border border-subtle bg-surface-1 px-2 py-1 sm:min-h-0 sm:flex-none">
            <SearchIcon className="h-3.5 w-3.5" />
            <Input
              mode="true-transparent"
              className="w-full p-0 placeholder:text-placeholder sm:max-w-[234px]"
              placeholder="Search"
              value={searchQuery}
              // oxlint-disable-next-line jsx-a11y/no-autofocus -- autofocus is gated on non-touch pointers (autoFocusSearch)
              autoFocus={autoFocusSearch}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <MemberListFiltersDropdown
            appliedFilters={appliedRoleFilters}
            handleUpdate={handleRoleFilterUpdate}
            memberType="project"
          />
          {isAdmin && (
            <Button
              variant="primary"
              onClick={() => {
                setInviteModal(true);
              }}
              data-ph-element={MEMBER_TRACKER_ELEMENTS.HEADER_ADD_BUTTON}
            >
              {t("add_member")}
            </Button>
          )}
        </div>
      </div>
      {!projectMemberIds ? (
        <MembersSettingsLoader />
      ) : (
        <div className="divide-y divide-subtle overflow-x-auto">
          {searchedProjectMembers.length !== 0 && (
            <ProjectMemberListItem
              memberDetails={memberDetails ?? []}
              projectId={projectId}
              workspaceSlug={workspaceSlug}
            />
          )}
          {searchedProjectMembers.length === 0 && (
            <h4 className="mt-16 text-center text-13 text-placeholder">{t("no_matching_members")}</h4>
          )}
        </div>
      )}
    </>
  );
});
