/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { redirect } from "react-router";
import type { Route } from "./+types/dashboards";

export const clientLoader = ({ params }: Route.ClientLoaderArgs) => {
  const { workspaceSlug } = params;
  throw redirect(`/${workspaceSlug}/kinerja/dasbor/`);
};

export default function Dashboards() {
  return null;
}
