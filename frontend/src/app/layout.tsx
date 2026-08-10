import type { Metadata } from "next";
import "@/styles/globals.css";
import { Providers } from "@/components/layouts/providers";

export const metadata: Metadata = {
  title: "Face Search OSINT",
  description: "Local AI face recognition with optional public OSINT discovery",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
