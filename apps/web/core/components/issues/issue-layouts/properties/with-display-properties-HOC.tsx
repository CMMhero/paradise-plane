/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ReactNode } from "react";
import { observer } from "mobx-react";
import { isDisplayPropertyAvailable } from "@plane/constants";
import type { IIssueDisplayProperties } from "@plane/types";

interface IWithDisplayPropertiesHOC {
  displayProperties: IIssueDisplayProperties;
  shouldRenderProperty?: (displayProperties: IIssueDisplayProperties) => boolean;
  displayPropertyKey: keyof IIssueDisplayProperties | (keyof IIssueDisplayProperties)[];
  children: ReactNode;
}

export const WithDisplayPropertiesHOC = observer(function WithDisplayPropertiesHOC({
  displayProperties,
  shouldRenderProperty,
  displayPropertyKey,
  children,
}: IWithDisplayPropertiesHOC) {
  // Kustomisasi Paradise: properti milik modul yang dimatikan di God Mode tak pernah tampil.
  const keys = Array.isArray(displayPropertyKey) ? displayPropertyKey : [displayPropertyKey];
  const shouldDisplayPropertyFromFilters = keys.every(
    (key) => !!displayProperties[key] && isDisplayPropertyAvailable(key)
  );

  const renderProperty =
    shouldDisplayPropertyFromFilters && (shouldRenderProperty ? shouldRenderProperty(displayProperties) : true);

  if (!renderProperty) return null;

  return <>{children}</>;
});
