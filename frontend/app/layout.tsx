import type { Metadata } from "next";
import { IBM_Plex_Sans, Manrope } from "next/font/google";

import "@/app/globals.css";

import { QueryProvider } from "@/components/providers/query-provider";
import { Sidebar } from "@/components/layout/sidebar";

const headingFont = Manrope({ subsets: ["latin", "cyrillic"], variable: "--font-heading" });
const bodyFont = IBM_Plex_Sans({ subsets: ["latin", "cyrillic"], weight: ["400", "500", "600"], variable: "--font-body" });

export const metadata: Metadata = {
  title: "Dashboard by arccos",
  description: "Analytics workspace for Telegram and VK comments."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body className={`${headingFont.variable} ${bodyFont.variable} font-[var(--font-body)]`}>
        <QueryProvider>
          <div className="app-shell min-h-screen xl:grid xl:grid-cols-[20rem_1fr]">
            <Sidebar />
            <main className="relative p-5 md:p-8 xl:p-10">
              <div className="app-panel-strong min-h-[calc(100vh-3rem)] p-5 md:p-8 xl:p-10">{children}</div>
            </main>
          </div>
        </QueryProvider>
      </body>
    </html>
  );
}
