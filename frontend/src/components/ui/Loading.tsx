import { cn } from '@/lib/utils';
import { Coby } from '@/components/mascot/Coby';

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'animate-pulse bg-cobweb-surface2 border-2 border-cobweb-border',
        className,
      )}
    />
  );
}

export function LoadingSpinner({ label = 'Loading...' }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16">
      <Coby size={72} />
      <p className="font-pixel text-[9px] uppercase tracking-wider text-gray-400 animate-pulse">
        {label}
      </p>
    </div>
  );
}
