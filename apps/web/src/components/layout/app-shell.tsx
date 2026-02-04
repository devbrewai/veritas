import { NavHeader } from "./nav-header";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <NavHeader />
      <main className="flex-1">
        {children}
      </main>
    </div>
  );
}
