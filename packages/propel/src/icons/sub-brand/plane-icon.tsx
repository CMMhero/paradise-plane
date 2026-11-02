/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import * as React from "react";

import { IconWrapper } from "../icon-wrapper";
import type { ISvgIcons } from "../type";

// Glyph rumah Paradise Perkasa satu warna (ikut `currentColor`), menggantikan
// glyph dua kotak milik Plane. Koordinat diukur dari Company_Logo/Paradise_Perkasa.png
// (652x582), viewBox dibuat persegi supaya tetap pas di slot ikon 16x16.
export function PlaneNewIcon({ color = "currentColor", ...rest }: ISvgIcons) {
  return (
    <IconWrapper color={color} viewBox="0 -35 652 652" {...rest}>
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M326 0L652 120V237L554 201V500L652 537V582H0V537L97 500V201L0 237V120L326 0ZM227 153L326 116L423 153V195L326 158L227 195V153ZM227 278L326 237L423 278V497H227V278Z"
        fill={color}
      />
    </IconWrapper>
  );
}
