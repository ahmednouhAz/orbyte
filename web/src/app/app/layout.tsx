import { redirect } from "next/navigation";
import type { Route } from "next";
import { unstable_noStore as noStore } from "next/cache";
import { requireAuth } from "@/lib/auth/svcSS";
import { ProjectsProvider } from "@/providers/ProjectsContext";
import AppSidebar from "@/sections/sidebar/AppSidebar";
import { RootLayout } from "@opal/layouts";
import AppChrome from "@/layouts/chromes/AppChrome";

export interface LayoutProps {
  children: React.ReactNode;
}

export default async function Layout({ children }: LayoutProps) {
  noStore();

  // Only check authentication - data fetching is done client-side via SWR hooks
  const authResult = await requireAuth();

  if (authResult.redirect) {
    redirect(authResult.redirect as Route);
  }

  return (
    <ProjectsProvider>
      <RootLayout.Root>
        <AppSidebar />
        <AppChrome>{children}</AppChrome>
      </RootLayout.Root>
    </ProjectsProvider>
  );
}
