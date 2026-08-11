'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/utils/cn';
import { ChevronRight, Upload, History, Settings, Search, Network, BarChart2 } from 'lucide-react';

const navigation = [
  { name: 'Upload', href: '/upload', icon: Upload },
  { name: 'Search', href: '/search', icon: Search, hidden: true }, // Dynamic route
  { name: 'History', href: '/history', icon: History },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export default function Header() {
  const pathname = usePathname();

  return (
    <header className="border-b border-border bg-background/80 backdrop-blur sticky top-0 z-40">
      <nav className="mx-auto max-w-7xl px-4" aria-label="Main navigation">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center gap-8">
            <Link href="/upload" className="flex items-center gap-2 font-semibold text-lg">
              <Search className="h-6 w-6 text-primary" />
              <span>Sherlock</span>
            </Link>
            <div className="hidden md:flex items-center gap-1">
              {navigation.map((item) => (
                !item.hidden && (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={cn(
                      'flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                      pathname === item.href || (item.href === '/search' && pathname.startsWith('/search/'))
                        ? 'bg-primary/10 text-primary'
                        : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                    )}
                  >
                    <item.icon className="h-4 w-4" />
                    {item.name}
                  </Link>
                )
              ))}
            </div>
          </div>
          <div className="flex items-center gap-4">
            <span className="hidden sm:block text-sm text-muted-foreground">
              OSINT Face Search
            </span>
          </div>
        </div>
      </nav>
    </header>
  );
}