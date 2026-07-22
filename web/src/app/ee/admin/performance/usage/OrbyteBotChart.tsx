import SvgSimpleLoader from "@opal/icons/simple-loader";
import { getDatesList, useOrbyteBotAnalytics } from "../lib";
import { DateRangePickerValue } from "@/components/dateRangeSelectors/AdminDateRangeSelector";
import { Text } from "@opal/components";
import Title from "@/components/ui/title";
import CardSection from "@/components/admin/CardSection";
import { AreaChartDisplay } from "@/components/ui/areaChart";

export function OrbyteBotChart({
  timeRange,
}: {
  timeRange: DateRangePickerValue;
}) {
  const {
    data: orbyteBotAnalyticsData,
    isLoading: isOrbyteBotAnalyticsLoading,
    error: orbyteBotAnalyticsError,
  } = useOrbyteBotAnalytics(timeRange);

  let chart;
  if (isOrbyteBotAnalyticsLoading) {
    chart = (
      <div className="h-80 flex flex-col items-center justify-center">
        <SvgSimpleLoader className="h-6 w-6" />
      </div>
    );
  } else if (
    !orbyteBotAnalyticsData ||
    orbyteBotAnalyticsData[0] == undefined ||
    orbyteBotAnalyticsError
  ) {
    chart = (
      <div className="h-80 text-red-600 text-bold flex flex-col">
        <p className="m-auto">Failed to fetch feedback data...</p>
      </div>
    );
  } else {
    const initialDate =
      timeRange.from || new Date(orbyteBotAnalyticsData[0].date);
    const dateRange = getDatesList(initialDate);

    const dateToOrbyteBotAnalytics = new Map(
      orbyteBotAnalyticsData.map((orbyteBotAnalyticsEntry) => [
        orbyteBotAnalyticsEntry.date,
        orbyteBotAnalyticsEntry,
      ])
    );

    chart = (
      <AreaChartDisplay
        className="mt-4"
        data={dateRange.map((dateStr) => {
          const orbyteBotAnalyticsForDate = dateToOrbyteBotAnalytics.get(dateStr);
          return {
            Day: dateStr,
            "Total Queries": orbyteBotAnalyticsForDate?.total_queries || 0,
            "Automatically Resolved":
              orbyteBotAnalyticsForDate?.auto_resolved || 0,
          };
        })}
        categories={["Total Queries", "Automatically Resolved"]}
        index="Day"
        colors={["indigo", "fuchsia"]}
        yAxisWidth={60}
      />
    );
  }

  return (
    <CardSection className="mt-8">
      <Title>Slack Channel</Title>
      <Text as="p">Total Queries vs Auto Resolved</Text>
      {chart}
    </CardSection>
  );
}
