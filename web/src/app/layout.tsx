import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MIXI",
  description: "Tìm kiếm thời trang bằng văn bản, giọng nói và hình ảnh",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="vi" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
