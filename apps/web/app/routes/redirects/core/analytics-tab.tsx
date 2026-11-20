/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { redirect } from "react-router";
import type { Route } from "./+types/analytics-tab";

export const clientLoader = ({ params }: Route.ClientLoaderArgs) => {
  const { workspaceSlug, tabId } = params;
  throw redirect(`/${workspaceSlug}/kinerja/analitik/${tabId}/`);
};

export default function AnalyticsTab() {
  return null;
}
