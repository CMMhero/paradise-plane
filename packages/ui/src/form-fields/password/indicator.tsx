/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { CircleCheck } from "lucide-react";
import React from "react";
import { E_PASSWORD_STRENGTH } from "@plane/constants";
import { cn, getPasswordStrength, getPasswordCriteria } from "@plane/utils";

export interface PasswordStrengthIndicatorProps {
  password: string;
  isFocused?: boolean;
  /** Translated criteria labels keyed by criterion key (length). */
  criteriaLabels?: Partial<Record<string, string>>;
}

/** Password requirements. Hidden once they are met and the field loses focus. */
export function PasswordStrengthIndicator({
  password,
  isFocused = false,
  criteriaLabels,
}: PasswordStrengthIndicatorProps) {
  if (!isFocused && getPasswordStrength(password) === E_PASSWORD_STRENGTH.STRENGTH_VALID) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {getPasswordCriteria(password).map((criterion) => {
        const textColor = criterion.isValid ? "text-success-primary" : "text-primary";
        return (
          <div key={criterion.key} className="flex items-center gap-1.5">
            <div className="flex items-center justify-center p-0.5">
              <CircleCheck className={cn("h-3 w-3 flex-shrink-0", textColor)} />
            </div>
            <span className={cn("!text-11", textColor)}>{criteriaLabels?.[criterion.key] ?? criterion.label}</span>
          </div>
        );
      })}
    </div>
  );
}
