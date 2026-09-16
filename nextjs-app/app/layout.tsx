import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GovBid Intelligence",
  description: "Live natural-language search over GeM (Government e-Marketplace) public bid data.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
