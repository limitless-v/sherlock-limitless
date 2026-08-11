'use client';

import Link from 'next/link';
import { useSearchHistory } from '@/hooks/useSearch';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge, type BadgeVariant } from '@/components/ui/Badge';
import { Upload, Search, History, Settings, TrendingUp, Clock, CheckCircle, AlertTriangle } from 'lucide-react';
import { cn } from '@/utils/cn';
import { LoadingOverlay } from '@/components/ui/Spinner';

const STATUS_COLORS: Record<string, BadgeVariant> = {
  completed: 'completed',
  degraded: 'degraded',
  failed: 'failed',
  running: 'running',
  pending: 'pending',
};

export default function DashboardPage() {
  const { data: history, isLoading } = useSearchHistory(1, 5);

  const recentSearches = history?.items.slice(0, 5) || [];
  const totalSearches = history?.total || 0;
  const completedSearches = history?.items.filter(s => s.status === 'completed').length || 0;
  const runningSearches = history?.items.filter(s => s.status === 'running').length || 0;

  const stats = [
    {
      label: 'Total Searches',
      value: totalSearches.toString(),
      icon: Search,
      color: 'text-primary',
    },
    {
      label: 'Completed',
      value: completedSearches.toString(),
      icon: CheckCircle,
      color: 'text-success',
    },
    {
      label: 'Running',
      value: runningSearches.toString(),
      icon: Clock,
      color: 'text-primary',
    },
    {
      label: 'Success Rate',
      value: totalSearches > 0 ? `${Math.round((completedSearches / totalSearches) * 100)}%` : '0%',
      icon: TrendingUp,
      color: 'text-success',
    },
  ];

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="mt-2 text-muted-foreground">
          Overview of your face search and OSINT investigations
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-8">
        {stats.map((stat) => (
          <Card key={stat.label}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">{stat.label}</p>
                  <p className="text-3xl font-bold mt-1">{stat.value}</p>
                </div>
                <div className={cn('p-3 rounded-xl', stat.color)}>
                  <stat.icon className="h-6 w-6" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <h2 className="text-lg font-semibold">Quick Actions</h2>
            <p className="text-sm text-muted-foreground">Start a new investigation</p>
          </CardHeader>
          <CardContent className="space-y-3">
            <Link href="/upload">
              <Button className="w-full justify-start gap-3" size="lg">
                <Upload className="h-5 w-5" />
                <div className="text-left">
                  <p className="font-medium">Upload Image & Search</p>
                  <p className="text-sm text-muted-foreground">Start a new face search with an image</p>
                </div>
              </Button>
            </Link>
            <Link href="/history">
              <Button variant="outline" className="w-full justify-start gap-3" size="lg">
                <History className="h-5 w-5" />
                <div className="text-left">
                  <p className="font-medium">View Search History</p>
                  <p className="text-sm text-muted-foreground">Browse and manage past searches</p>
                </div>
              </Button>
            </Link>
            <Link href="/settings">
              <Button variant="outline" className="w-full justify-start gap-3" size="lg">
                <Settings className="h-5 w-5" />
                <div className="text-left">
                  <p className="font-medium">Settings</p>
                  <p className="text-sm text-muted-foreground">Configure search and appearance</p>
                </div>
              </Button>
            </Link>
          </CardContent>
        </Card>

        {/* Recent Searches */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">Recent Searches</h2>
              <p className="text-sm text-muted-foreground">Latest search activity</p>
            </div>
            <Link href="/history">
              <Button variant="ghost" size="sm">View All</Button>
            </Link>
          </CardHeader>
          <CardContent>
            <LoadingOverlay isLoading={isLoading}>
              {recentSearches.length === 0 ? (
                <div className="text-center py-8">
                  <Search className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-semibold mb-2">No Searches Yet</h3>
                  <p className="text-muted-foreground mb-4">
                    Start your first face search investigation
                  </p>
                  <Link href="/upload">
                    <Button>Upload Image</Button>
                  </Link>
                </div>
              ) : (
                <div className="space-y-3">
                  {recentSearches.map((search) => (
                    <Link
                      key={search.id}
                      href={`/search/${search.id}/results`}
                      className="flex items-center justify-between p-3 rounded-lg hover:bg-muted transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <img
                          src={search.uploaded_image}
                          alt="Search preview"
                          className="h-10 w-10 rounded-lg object-cover"
                        />
                        <div>
                          <p className="font-medium">Search #{search.id}</p>
                          <p className="text-sm text-muted-foreground">
                            {new Date(search.created_at).toLocaleString()}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={STATUS_COLORS[search.status as keyof typeof STATUS_COLORS] || 'default'}>
                          {search.status}
                        </Badge>
                        <Search className="h-4 w-4 text-muted-foreground" />
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </LoadingOverlay>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}