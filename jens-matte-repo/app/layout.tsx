import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "JENS MATTE – matteeventyr for 5.–7. trinn",
  description: "Et adaptivt mattespill med 500 oppgaver, visuelle modeller og forklaringer steg for steg.",
  applicationName: "JENS MATTE",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "JENS MATTE",
  },
  icons: {
    icon: [
      { url: "/icons/icon.svg", type: "image/svg+xml" },
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
    ],
    apple: "/icons/icon-192.png",
  },
  manifest: "/manifest.webmanifest",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#0b1021",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="nb">
      <body>{children}</body>
    </html>
  );
}
