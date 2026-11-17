import type { Metadata } from "next";
import { IBM_Plex_Sans } from "next/font/google";
import "./globals.css";
import { SceneProvider } from "@/context/SceneContext";

const ibmPlex = IBM_Plex_Sans({
  weight: ["300", "400", "500", "600", "700"],
  subsets: ["latin"],
  variable: "--font-ibm",
  display: "swap",
});

export const metadata: Metadata = {
  title: "OceanTrace AI — Maritime Oil Spill Intelligence",
  description:
    "AI-powered satellite SAR oil spill detection, drift modelling, AIS vessel correlation, and investigation reporting for maritime intelligence operations.",
  keywords: ["oil spill", "SAR", "maritime", "AIS", "drift model", "satellite"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${ibmPlex.variable} dark`} suppressHydrationWarning>
      <head>
        <link
          rel="stylesheet"
          href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
          crossOrigin=""
        />
      </head>
      <body className="font-ibm bg-maritime-900 text-slate-100 antialiased overflow-hidden" suppressHydrationWarning>
        <SceneProvider>{children}</SceneProvider>
      </body>
    </html>
  );
}
