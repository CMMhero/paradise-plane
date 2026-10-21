/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

type TPageHeader = {
  title?: string;
  description?: string;
};

export function PageHeader(props: TPageHeader) {
  const { title = "God Mode, Paradise Task Tracker", description = "Panel administrasi instance." } = props;

  return (
    <>
      <title>{title}</title>
      <meta name="description" content={description} />
    </>
  );
}
