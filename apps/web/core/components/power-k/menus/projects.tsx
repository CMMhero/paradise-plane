/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React from "react";
// components
import { Logo } from "@plane/propel/emoji-icon-picker";
// plane imports
import type { TPartialProject } from "@plane/types";
// local imports
import { PowerKMenuBuilder } from "./builder";

function getProjectIconNode(project: TPartialProject) {
  return (
    <span className="shrink-0">
      <Logo logo={project.logo_props} size={14} />
    </span>
  );
}

type Props = {
  projects: TPartialProject[];
  onSelect: (project: TPartialProject) => void;
};

export function PowerKProjectsMenu({ projects, onSelect }: Props) {
  return (
    <PowerKMenuBuilder
      items={projects}
      getKey={(project) => project.id}
      getIconNode={getProjectIconNode}
      getValue={(project) => project.name}
      getLabel={(project) => project.name}
      onSelect={onSelect}
      emptyText="No departments found"
    />
  );
}
