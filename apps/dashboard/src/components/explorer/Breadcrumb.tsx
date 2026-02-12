import { Database, FileText, Folder, FolderOpen, Settings } from 'lucide-react';
import { MediaTypeIcon } from '@/lib/mediaTypeIcon';
import { StackItem } from './types';

interface BreadcrumbProps {
  item: StackItem;
  onSettingsClick?: (e: React.MouseEvent) => void;
  onClick?: () => void;
  isActive?: boolean;
}

export function Breadcrumb({ item, onSettingsClick, onClick, isActive }: BreadcrumbProps) {
  // Flat design: No borders, use background grouping
  // Icons: strokeWidth={2.25}, matching text color (dark on light)
  
  return (
    <div
      className={`flex items-baseline gap-2 shadow-flat-muted p-2 rounded-xl hover:bg-hover transition-colors duration-300 group cursor-pointer text-sm ${isActive ? 'bg-selected' : 'bg-card'}`}
      data-card-shell="true"
      data-flip-id={`card-${item.id.trim()}`}
      data-crumb-target={item.type === 'root' ? 'root:root' : `${item.type}:${item.id}`}
      onClick={onClick}
    >
      <div
        className="flex items-baseline gap-2 w-full"
        data-card-content="true"
      >
        <div 
          className="flex items-center justify-center shrink-0 self-baseline"
          data-flip-id={`icon-${item.id}`}
          style={{ width: '1em', height: '1em' }}
        >
          {item.type === 'root' && <Database className="w-full h-full text-muted-foreground block" strokeWidth={2.25} />}
          {item.type === 'corpus' && <FolderOpen className="w-full h-full text-muted-foreground block" strokeWidth={2.25} />}
          {item.type === 'item' && <MediaTypeIcon mediaType={(item as any).data.mediaType} className="w-full h-full text-muted-foreground" />}
        </div>
        
        <div className="flex flex-col min-w-0 flex-1">
        <div className="flex items-baseline gap-2">
            <span 
                className="font-bold text-foreground truncate block flex-1 leading-none"
                data-flip-id={`title-text-${item.id}`}
            >
                {item.title}
            </span>

            {/* Settings Icon for Root - In flow, baseline aligned */}
            {/* Always rendered but hidden via opacity/pointer-events if not root to prevent layout shifts during transitions? 
                No, Flip handles enter/leave. 
                But if it disappears during morph, it might be because the Breadcrumb ID morphs but this inner element is removed.
                If we want it to stay or fade nicely, we should give it a stable ID or container.
                Let's give it a flip ID so it fades out properly.
            */}
            {item.type === 'root' && (
                <div 
                    className="text-muted-foreground hover:text-foreground transition-colors shrink-0 flex items-center justify-center self-baseline flip-animate"
                    data-flip-id={`settings-${item.id}`}
                    style={{ width: '1em', height: '1em' }}
                    onClick={(e) => {
                        e.stopPropagation();
                        onSettingsClick?.(e);
                    }}
                >
                    <Settings className="w-full h-full block" strokeWidth={2.25} />
                </div>
            )}
        </div>
        
        {/* Dynamic Metadata / Stats - Information Line */}
          <div 
              className="flex items-center gap-2 mt-1 text-[10px] text-muted-foreground font-bold h-4"
              data-flip-id={`meta-row-${item.id}`}
          >
              {item.type === 'root' && (
                  <span className="flex items-center gap-1">
                      <Folder className="w-3 h-3" strokeWidth={2.25} /> {(item as any).cachedCorpora?.length ?? '?'}
                  </span>
              )}

              {item.type === 'corpus' && (
                  <span className="flex items-center gap-1">
                      <FileText className="w-3 h-3" strokeWidth={2.25} /> {(item as any).data.itemCount ?? 0}
                  </span>
              )}

              {item.type === 'item' && (
                  <span className="flex items-center gap-2">
                      <span className="uppercase">
                          {(item as any).data.mediaType}
                      </span>
                      <span>
                          {((item as any).data.bytes / 1024).toFixed(0)} KB
                      </span>
                  </span>
              )}
          </div>
        </div>
      </div>
    </div>
  );
}
