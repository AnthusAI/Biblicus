/**
 * FileTreePanel - File tree with Shadcn UI
 */

import { useEffect, useState } from 'react';
import { localAPI, type CatalogItem } from '@/lib/local-api';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Folder, File, Search } from 'lucide-react';

export interface FileTreePanelProps {
  corpusName: string;
  onFileSelect: (file: { id: string; relpath: string; mediaType: string; title?: string }) => void;
  selectedFileId: string | null;
}

interface TreeNode {
  name: string;
  path: string;
  isDirectory: boolean;
  children?: TreeNode[];
  item?: CatalogItem;
}

export function FileTreePanel({
  corpusName,
  onFileSelect,
  selectedFileId,
}: FileTreePanelProps) {
  const [tree, setTree] = useState<TreeNode | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    const loadTree = async () => {
      try {
        const { items } = await localAPI.listCatalogItems(corpusName);

        const root: TreeNode = {
          name: corpusName,
          path: '',
          isDirectory: true,
          children: [],
        };

        items.forEach((item: CatalogItem) => {
          const pathParts = item.relpath.split('/');
          let currentNode = root;

          pathParts.forEach((part, index) => {
            const isLast = index === pathParts.length - 1;
            const childPath = pathParts.slice(0, index + 1).join('/');

            if (!currentNode.children) {
              currentNode.children = [];
            }

            let child = currentNode.children.find((c) => c.name === part);

            if (!child) {
              child = {
                name: part,
                path: childPath,
                isDirectory: !isLast,
                children: isLast ? undefined : [],
                item: isLast ? item : undefined,
              };
              currentNode.children.push(child);
            }

            currentNode = child;
          });
        });

        setTree(root);
        setLoading(false);
      } catch (err) {
        console.error('Failed to load file tree:', err);
        setLoading(false);
      }
    };

    loadTree();
  }, [corpusName]);

  const handleFileClick = (node: TreeNode) => {
    if (!node.item) return;

    onFileSelect({
      id: node.item.id,
      relpath: node.item.relpath,
      mediaType: node.item.media_type,
      title: node.item.title,
    });
  };

  const filterTree = (node: TreeNode, query: string): TreeNode | null => {
    if (!query) return node;

    const lowerQuery = query.toLowerCase();
    const matches = node.name.toLowerCase().includes(lowerQuery);

    const filteredChildren = node.children
      ?.map((child) => filterTree(child, query))
      .filter((child): child is TreeNode => child !== null);

    if (matches || (filteredChildren && filteredChildren.length > 0)) {
      return {
        ...node,
        children: filteredChildren,
      };
    }

    return null;
  };

  const renderNode = (node: TreeNode, depth: number = 0): JSX.Element => {
    const isSelected = node.item?.id === selectedFileId;
    const paddingLeft = depth * 16;

    if (!node.isDirectory) {
      return (
        <Button
          key={node.path}
          variant={isSelected ? 'secondary' : 'ghost'}
          className="w-full justify-start text-sm font-normal h-auto py-2 mb-0.5"
          style={{ paddingLeft }}
          onClick={() => handleFileClick(node)}
        >
          <File className="h-4 w-4 mr-2 flex-shrink-0" />
          <span className="truncate">{node.name}</span>
        </Button>
      );
    }

    return (
      <div key={node.path}>
        <Button
          variant="ghost"
          className="w-full justify-start text-sm font-medium h-auto py-2 mb-0.5"
          style={{ paddingLeft }}
        >
          <Folder className="h-4 w-4 mr-2 flex-shrink-0" />
          <span className="truncate">{node.name}</span>
        </Button>
        {node.children && (
          <div>{node.children.map((child) => renderNode(child, depth + 1))}</div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <p className="text-sm text-muted-foreground">Loading files...</p>
      </div>
    );
  }

  if (!tree) {
    return (
      <div className="flex items-center justify-center py-8">
        <p className="text-sm text-muted-foreground">Failed to load files</p>
      </div>
    );
  }

  const filteredTree = filterTree(tree, searchQuery);

  return (
    <div>
      <div className="mb-4">
        <h3 className="text-sm font-semibold mb-2 text-muted-foreground uppercase tracking-wide">
          Files
        </h3>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            type="text"
            placeholder="Search files..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      <div className="space-y-0.5">
        {filteredTree ? (
          filteredTree.children?.map((child) => renderNode(child, 0))
        ) : (
          <p className="text-sm text-muted-foreground text-center py-8">
            No files match your search
          </p>
        )}
      </div>
    </div>
  );
}
