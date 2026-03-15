import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDisplayName(name: string): string {
  if (!name) return '';

  // Check for raw/UUID-- pattern or just UUID-- pattern
  // Matches: raw/0013c092-afba-438c-ad51-195ad6ce882b--...
  // Returns: 0013c092
  const uuidPattern = /(?:^|\/)([0-9a-f]{8})[0-9a-f-]{28}--/;
  const match = name.match(uuidPattern);
  
  if (match) {
    return match[1];
  }

  return name;
}
