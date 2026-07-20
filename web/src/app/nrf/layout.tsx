import { ProjectsProvider } from "@/providers/ProjectsContext";
import { VoiceModeProvider } from "@/providers/VoiceModeProvider";

export interface LayoutProps {
  children: React.ReactNode;
}

/**
 * NRF Root Layout - Shared by all NRF routes
 *
 * Provides ProjectsProvider (needed by NRFPage) without auth redirect.
 * Sidebar and chrome are handled by sub-layouts / individual pages.
 * VoiceModeProvider is required because AppInputBar (rendered inside NRF)
 * calls useVoiceMode() unconditionally.
 */
export default function Layout({ children }: LayoutProps) {
  return (
    <ProjectsProvider>
      <VoiceModeProvider>{children}</VoiceModeProvider>
    </ProjectsProvider>
  );
}
