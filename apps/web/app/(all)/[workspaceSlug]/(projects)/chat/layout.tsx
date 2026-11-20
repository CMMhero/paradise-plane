/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// components
import { Outlet } from "react-router";
import { AppHeader } from "@/components/core/app-header";
import { ContentWrapper } from "@/components/core/content-wrapper";
// local imports
import { ChatHeader } from "./header";

export default function ChatLayout() {
  return (
    <>
      <AppHeader header={<ChatHeader />} />
      {/* Obrolan menggulir daftar pesannya sendiri. Kotak gulir luar bawaan ContentWrapper
          akan ikut menggulirkan seluruh obrolan (kotak tulis ikut naik) begitu isinya
          lebih tinggi satu piksel pun. `clip` melarang gulir itu, juga yang dipicu
          skrip (scrollIntoView, fokus). */}
      <ContentWrapper className="overflow-clip">
        <Outlet />
      </ContentWrapper>
    </>
  );
}
