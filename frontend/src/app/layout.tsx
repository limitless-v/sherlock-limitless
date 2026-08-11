import type { Metadata } from "next";
import "@/styles/globals.css";
import { Providers } from "@/components/layouts/providers";
import Header from "@/components/layouts/Header";

export const metadata: Metadata = {
  title: "Sherlock OSINT",
  description: "Local AI face recognition with optional public OSINT discovery",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-background font-sans antialiased">
        <Providers>
          <Header />
          <main>{children}</main>
        </Providers>
      </body>
    </html>
  );
}