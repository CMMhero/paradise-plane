/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import { useTranslation } from "@plane/i18n";
import { BarChart } from "@plane/propel/charts/bar-chart";
import { EmptyStateCompact } from "@plane/propel/empty-state";
import type { IUserProfileData } from "@plane/types";
import { Loader, Card } from "@plane/ui";
import { capitalizeFirstLetter } from "@plane/utils";

type Props = {
  userProfile: IUserProfileData | undefined;
};

// Kustomisasi Paradise: token prioritas, sama dengan ikon prioritas di seluruh aplikasi. Hex bawaan
// membuat "Urgent" (#991b1b, merah tua) nyaris hilang di kartu tema gelap dan "None" putih menyilaukan.
const priorityColors = {
  urgent: "var(--priority-urgent)",
  high: "var(--priority-high)",
  medium: "var(--priority-medium)",
  low: "var(--priority-low)",
  none: "var(--priority-none)",
};

export function ProfilePriorityDistribution({ userProfile }: Props) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col space-y-2">
      <h3 className="text-16 font-medium">{t("profile.stats.priority_distribution.title")}</h3>
      {userProfile ? (
        <Card>
          {userProfile.priority_distribution.length > 0 ? (
            <BarChart
              className="h-[300px] w-full"
              margin={{ top: 20, right: 30, bottom: 5, left: 0 }}
              data={userProfile.priority_distribution.map((priority) => ({
                key: priority.priority ?? "None",
                name: capitalizeFirstLetter(priority.priority ?? "None"),
                count: priority.priority_count,
              }))}
              bars={[
                {
                  key: "count",
                  label: "Count",
                  stackId: "bar-one",
                  fill: (payload: any) => priorityColors[payload.key as keyof typeof priorityColors], // TODO: fix types
                  textClassName: "",
                  showPercentage: false,
                  showTopBorderRadius: () => true,
                  showBottomBorderRadius: () => true,
                },
              ]}
              xAxis={{
                key: "name",
                label: t("common.priority"),
                // Hanya lima kategori: tampilkan semua label (bawaan recharts menyembunyikan "High").
                interval: 0,
              }}
              yAxis={{
                key: "count",
                label: "",
              }}
              barSize={20}
            />
          ) : (
            <EmptyStateCompact
              assetKey="priority"
              assetClassName="size-20"
              title={t("workspace_empty_state.your_work_by_priority.title")}
            />
          )}
        </Card>
      ) : (
        // Kustomisasi Paradise: kerangka di dalam Card yang sama dan setinggi
        // grafik (300px), supaya kartu tidak tumbuh ~45px saat data tiba.
        <Card>
          <Loader className="flex h-[300px] items-end justify-center gap-12">
            <Loader.Item width="30px" height="200px" />
            <Loader.Item width="30px" height="150px" />
            <Loader.Item width="30px" height="250px" />
            <Loader.Item width="30px" height="150px" />
            <Loader.Item width="30px" height="100px" />
          </Loader>
        </Card>
      )}
    </div>
  );
}
