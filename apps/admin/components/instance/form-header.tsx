/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

type FormHeaderProps = {
  heading: string;
  subHeading: string;
  /** Paradise: small accent label above the heading, as on the web sign-in. */
  eyebrow?: string;
};

export function FormHeader({ heading, subHeading, eyebrow }: FormHeaderProps) {
  if (eyebrow) {
    return (
      <div className="flex flex-col">
        <span className="text-13 font-medium text-accent-primary">{eyebrow}</span>
        <h1 className="mt-2 font-heading text-32 leading-tight font-semibold tracking-tight text-primary">{heading}</h1>
        <p className="mt-2 text-14 text-secondary">{subHeading}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1.5">
      <h2 className="font-heading text-24 leading-8 font-semibold tracking-tight text-primary">{heading}</h2>
      <p className="text-14 leading-6 text-secondary">{subHeading}</p>
    </div>
  );
}
