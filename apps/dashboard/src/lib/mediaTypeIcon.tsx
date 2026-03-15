import {
  AudioWaveform,
  Database,
  FileCode,
  FileText,
  Image,
  Table,
  Video,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const TABULAR_MIMES = new Set([
  'text/csv',
  'application/csv',
  'application/vnd.ms-excel',
  'application/vnd.apache.parquet',
  'application/x-parquet',
]);

const DATABASE_MIMES = new Set([
  'application/x-sqlite3',
  'application/vnd.sqlite3',
  'application/sqlite',
]);

const YAML_MIMES = new Set([
  'text/yaml',
  'text/x-yaml',
  'application/x-yaml',
  'application/yaml',
]);

export function getIconForMediaType(mediaType: string): LucideIcon {
  const m = mediaType.toLowerCase().trim();
  if (TABULAR_MIMES.has(m)) return Table;
  if (m.startsWith('application/vnd.openxmlformats-officedocument.spreadsheetml.'))
    return Table;
  if (DATABASE_MIMES.has(m)) return Database;
  if (YAML_MIMES.has(m)) return FileCode;
  if (m.startsWith('image/')) return Image;
  if (m.startsWith('audio/')) return AudioWaveform;
  if (m.startsWith('video/')) return Video;
  if (m.startsWith('text/')) return FileText;
  if (m === 'application/pdf') return FileText;
  return FileText;
}

const STROKE_WIDTH = 2.25;

interface MediaTypeIconProps {
  mediaType: string;
  className?: string;
}

export function MediaTypeIcon({ mediaType, className }: MediaTypeIconProps) {
  const Icon = getIconForMediaType(mediaType);
  return (
    <Icon
      className={cn('block', className)}
      strokeWidth={STROKE_WIDTH}
    />
  );
}
