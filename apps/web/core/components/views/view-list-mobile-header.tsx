/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Dipindah dari rute Views departemen supaya halaman Views workspace memakai
 * komponen yang sama (Kustomisasi Paradise).
 */

import { observer } from "mobx-react";
// icons
import { ListFilter } from "lucide-react";
import { ChevronDownIcon } from "@plane/propel/icons";
// components
import { Row } from "@plane/ui";
import { FiltersDropdown } from "@/components/issues/issue-layouts/filters";
// hooks
import { useProjectView } from "@/hooks/store/use-project-view";
// local imports
import { ViewFiltersSelection } from "./filters/filter-selection";
import { ViewOrderByDropdown } from "./filters/order-by";

type Props = {
  /** Anggota yang ditawarkan di filter "Created by". */
  memberIds: string[] | undefined;
};

export const ViewListMobileHeader = observer(function ViewListMobileHeader({ memberIds }: Props) {
  // store hooks
  const { filters, updateFilters } = useProjectView();

  return (
    <div className="z-[13] flex justify-evenly border-b border-subtle bg-surface-1 py-2 md:hidden">
      <Row className="flex flex-grow items-center justify-center border-l border-subtle text-13 text-secondary">
        <ViewOrderByDropdown
          sortBy={filters.sortBy}
          sortKey={filters.sortKey}
          onChange={(val) => {
            if (val.key) updateFilters("sortKey", val.key);
            if (val.order) updateFilters("sortBy", val.order);
          }}
          isMobile
        />
      </Row>
      <div className="flex flex-grow items-center justify-center border-l border-subtle text-13 text-secondary">
        <FiltersDropdown
          icon={<ListFilter className="h-3 w-3" />}
          title="Filters"
          placement="bottom-end"
          isFiltersApplied={false}
          menuButton={
            <Row className="flex items-center text-13 text-secondary">
              Filters
              <ChevronDownIcon className="ml-2 h-4 w-4 text-secondary" strokeWidth={2} />
            </Row>
          }
        >
          <ViewFiltersSelection filters={filters} handleFiltersUpdate={updateFilters} memberIds={memberIds} />
        </FiltersDropdown>
      </div>
    </div>
  );
});
