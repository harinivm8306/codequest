import type { Metadata, Viewport } from "next";
// Self-hosted fonts (no CDN): Mukta Malar covers Tamil + Latin, Mukta covers Devanagari.
// Each file loads only for the scripts actually on screen (unicode-range).
import "@fontsource/mukta-malar/400.css";
import "@fontsource/mukta-malar/600.css";
import "@fontsource/mukta-malar/700.css";
import "@fontsource/mukta/devanagari-400.css";
import "@fontsource/mukta/devanagari-600.css";
import "@fontsource/mukta/devanagari-700.css";
import "./globals.css";
import { LangProvider } from "@/lib/lang";
import { RegisterSW } from "@/components/RegisterSW";

export const metadata: Metadata = {
  title: "SchemeSathi",
  description: "Speak in Tamil, Hindi or English and find the government welfare schemes you qualify for.",
  manifest: "/manifest.json",
  icons: { icon: "/icons/icon-192.png", apple: "/icons/icon-192.png" },
};

export const viewport: Viewport = { themeColor: "#4B2E83", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <LangProvider>{children}</LangProvider>
        <RegisterSW />
      </body>
    </html>
  );
}
