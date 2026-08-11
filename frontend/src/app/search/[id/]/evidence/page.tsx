'use client';

import { useEffect, useRef, useState } from 'react';
import { useParams } from 'next/navigation';
import { ChevronRight, ZoomIn, ZoomOut, RotateCcw, Download, Search as SearchIcon, Filter } from 'lucide-react';
import { cn } from '@/utils/cn';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Select } from '@/components/ui/Select';
import { Input } from '@/components/ui/Input';
import { LoadingOverlay } from '@/components/ui/Spinner';
import { useSearch, useSearchEvidence } from '@/hooks/useSearch';
import type { EvidenceGraph, EvidenceNode, EvidenceEdge } from '@/types/search';
import cytoscape from 'cytoscape';
import cose from 'cytoscape-cose-bilkent';

// Register the layout
if (typeof window !== 'undefined') {
  cytoscape.use(cose);
}

const NODE_COLORS: Record<string, string> = {
  image: '#0ea5e9',
  url: '#f59e0b',
  domain: '#8b5cf6',
  profile: '#22c55e',
  username: '#ec4899',
  website: '#06b6d4',
  organization: '#ef4444',
  location: '#84cc16',
  default: '#64748b',
};

const NODE_LABELS: Record<string, string> = {
  image: 'Image',
  url: 'URL',
  domain: 'Domain',
  profile: 'Profile',
  username: 'Username',
  website: 'Website',
  organization: 'Org',
  location: 'Location',
};

export default function EvidenceGraphPage() {
  const params = useParams();
  const searchId = parseInt(params.id as string, 10);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [selectedNode, setSelectedNode] = useState<EvidenceNode | null>(null);
  const [filterType, setFilterType] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const { data: search, isLoading: searchLoading } = useSearch(searchId);
  const { data: evidence, isLoading: evidenceLoading } = useSearchEvidence(searchId);

  const nodes = evidence?.nodes || [];
  const edges = evidence?.edges || [];

  const filteredNodes = nodes.filter((node) => {
    const typeMatch = filterType === 'all' || node.type === filterType;
    const searchMatch = !searchQuery || 
      node.entity_value.toLowerCase().includes(searchQuery.toLowerCase()) ||
      node.type.toLowerCase().includes(searchQuery.toLowerCase());
    return typeMatch && searchMatch;
  });

  const filteredNodeIds = new Set(filteredNodes.map((n) => n.id));
  const filteredEdges = edges.filter((e) => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target));

  // Initialize cytoscape
  useEffect(() => {
    if (!containerRef.current || filteredNodes.length === 0) return;

    const cy = cytoscape({
      container: containerRef.current,
      elements: [
        ...filteredNodes.map((node) => ({
          data: {
            id: node.id.toString(),
            label: node.entity_value.length > 30 ? node.entity_value.slice(0, 30) + '...' : node.entity_value,
            fullLabel: node.entity_value,
            type: node.type,
            source_url: node.source_url,
            ...node.attributes,
          },
          classes: node.type,
        })),
        ...filteredEdges.map((edge) => ({
          data: {
            id: edge.id.toString(),
            source: edge.source.toString(),
            target: edge.target.toString(),
            label: edge.type,
            type: edge.type,
            source_url: edge.source_url,
            confidence: edge.confidence,
          },
          classes: edge.type,
        })),
      ],
      style: [
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'font-size': '10px',
            'font-weight': 500,
            'text-valign': 'bottom',
            'text-halign': 'center',
            'text-wrap': 'wrap',
            'text-max-width': '80px',
            'background-color': (ele: cytoscape.NodeSingular) => NODE_COLORS[ele.data('type')] || NODE_COLORS.default,
            'color': '#fff',
            'text-outline-color': (ele: cytoscape.NodeSingular) => NODE_COLORS[ele.data('type')] || NODE_COLORS.default,
            'text-outline-width': 2,
            'width': 40,
            'height': 40,
            'border-width': 2,
            'border-color': '#fff',
          },
        },
        {
          selector: 'node:selected',
          style: {
            'border-width': 4,
            'border-color': '#fff',
            'background-color': (ele: cytoscape.NodeSingular) => NODE_COLORS[ele.data('type')] || NODE_COLORS.default,
            'width': 50,
            'height': 50,
          },
        },
        {
          selector: 'edge',
          style: {
            'width': 1.5,
            'line-color': '#94a3b8',
            'target-arrow-shape': 'triangle',
            'target-arrow-color': '#94a3b8',
            'curve-style': 'bezier',
            'label': 'data(label)',
            'font-size': '8px',
            'color': '#64748b',
            'text-background-color': '#fff',
            'text-background-opacity': 0.8,
            'text-background-padding': '2px',
          },
        },
        {
          selector: 'edge:selected',
          style: {
            'width': 3,
            'line-color': '#0ea5e9',
            'target-arrow-color': '#0ea5e9',
          },
        },
      ],
      layout: {
        name: 'cose-bilkent',
        fit: true,
        padding: 50,
      } as any,
      minZoom: 0.1,
      maxZoom: 2,
      zoomingEnabled: true,
      userZoomingEnabled: true,
      panningEnabled: true,
      userPanningEnabled: true,
      boxSelectionEnabled: true,
      selectionType: 'single',
    });

    cyRef.current = cy;

    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      const nodeData = nodes.find((n) => n.id === parseInt(node.id(), 10));
      if (nodeData) {
        setSelectedNode(nodeData);
      }
    });

    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        setSelectedNode(null);
      }
    });

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [filteredNodes, filteredEdges, nodes, edges]);

  // Fit to viewport when nodes change
  useEffect(() => {
    if (cyRef.current && filteredNodes.length > 0) {
      cyRef.current.fit('50%');
    }
  }, [filteredNodes.length]);

  if (searchLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="h-12 w-12 animate-spin border-4 border-primary border-t-transparent rounded-full" />
          <p>Loading search...</p>
        </div>
      </div>
    );
  }

  if (!search) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="max-w-md w-full mx-4">
          <CardContent className="p-6 text-center">
            <h2 className="text-xl font-semibold mb-2">Search Not Found</h2>
            <p className="text-muted-foreground">The search you're looking for doesn't exist.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const nodeTypes = [...new Set(nodes.map((n) => n.type))];

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="border-b border-border bg-background/80 backdrop-blur sticky top-0 z-40">
        <div className="mx-auto max-w-7xl px-4 py-3 flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" onClick={() => window.history.back()}>
              <ChevronRight className="h-4 w-4 rotate-180" />
            </Button>
            <div>
              <h1 className="font-semibold">Evidence Graph</h1>
              <p className="text-sm text-muted-foreground">Search #{searchId} • {nodes.length} nodes • {edges.length} connections</p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant="primary">{search.mode}</Badge>
            <Badge variant={search.status === 'completed' ? 'success' : 'default'}>
              {search.status}
            </Badge>
          </div>
        </div>
      </header>

      <main className="flex-1 flex flex-col mx-auto max-w-7xl px-4 py-4 w-full">
        <div className="flex flex-col lg:flex-row gap-4 h-full min-h-0">
          {/* Graph View */}
          <div className="flex-1 lg:w-3/4 h-full min-h-0 relative">
            <Card className="h-full">
              <CardContent className="p-0 h-full">
                <div 
                  ref={containerRef} 
                  className="w-full h-full"
                  style={{ minHeight: '500px' }}
                />
                {filteredNodes.length === 0 && !evidenceLoading && (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <p className="text-muted-foreground">No evidence graph data available</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Controls & Details Panel */}
          <div className="lg:w-1/4 flex flex-col gap-4 h-full min-h-0 max-h-full">
            <Card>
              <CardContent className="p-4">
                <div className="space-y-3">
                  <div>
                    <label className="text-sm font-medium mb-1 block">Filter by Type</label>
                    <Select
                      value={filterType}
                      onChange={(e) => setFilterType(e.target.value)}
                      options={[
                        { value: 'all', label: 'All Types' },
                        ...nodeTypes.map((t) => ({ value: t, label: NODE_LABELS[t] || t })),
                      ]}
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium mb-1 block">Search Nodes</label>
                    <Input
                      placeholder="Search by value or type..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => cyRef.current?.fit('50%')}>
                      <RotateCcw className="h-4 w-4 mr-1" />
                      Reset View
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => {
                      const blob = cyRef.current?.png({ output: 'blob' }) as Blob;
                      if (blob) {
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `evidence-graph-${searchId}.png`;
                        a.click();
                        URL.revokeObjectURL(url);
                      }
                    }}>
                      <Download className="h-4 w-4 mr-1" />
                      Export
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="flex-1 min-h-0">
              <CardContent className="p-4">
                <h3 className="font-semibold mb-3">Node Details</h3>
                {selectedNode ? (
                  <div className="space-y-3 max-h-[300px] overflow-y-auto">
                    <div className="flex items-center gap-2">
                      <span className={cn(
                        'px-2 py-1 rounded-full text-xs font-medium',
                        `bg-${NODE_COLORS[selectedNode.type] || NODE_COLORS.default}/15`,
                        `text-${NODE_COLORS[selectedNode.type] || NODE_COLORS.default}`
                      )}>
                        {NODE_LABELS[selectedNode.type] || selectedNode.type}
                      </span>
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground">Value</label>
                      <p className="font-mono text-sm break-all">{selectedNode.entity_value}</p>
                    </div>
                    {selectedNode.entity_id !== selectedNode.entity_value && (
                      <div>
                        <label className="text-xs text-muted-foreground">Entity ID</label>
                        <p className="font-mono text-sm break-all">{selectedNode.entity_id}</p>
                      </div>
                    )}
                    {selectedNode.source_url && (
                      <div>
                        <label className="text-xs text-muted-foreground">Source URL</label>
                        <a
                          href={selectedNode.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-primary hover:underline break-all block"
                        >
                          {selectedNode.source_url}
                        </a>
                      </div>
                    )}
                    {selectedNode.attributes && Object.keys(selectedNode.attributes).length > 0 && (
                      <div>
                        <label className="text-xs text-muted-foreground">Attributes</label>
                        <pre className="text-xs bg-muted p-2 rounded text-wrap">
                          {JSON.stringify(selectedNode.attributes, null, 2)}
                        </pre>
                      </div>
                    )}
                    <div className="text-xs text-muted-foreground">
                      Connected edges: {edges.filter(e => e.source === selectedNode.id || e.target === selectedNode.id).length}
                    </div>
                  </div>
                ) : (
                  <p className="text-muted-foreground text-sm text-center py-8">
                    Click a node to view details
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}