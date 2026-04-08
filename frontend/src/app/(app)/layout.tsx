import Sidebar from "@/components/Sidebar";
import CommandPalette from "@/components/CommandPalette";
import { ClaimsProvider } from "@/components/ClaimsContext";
import FeedbackFooter from "@/components/FeedbackFooter";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClaimsProvider>
      <Sidebar />
      <CommandPalette />
      <main className="lg:ml-64 min-h-screen">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-8 pt-16 lg:pt-8">
          {children}
          <FeedbackFooter />
        </div>
      </main>
    </ClaimsProvider>
  );
}
