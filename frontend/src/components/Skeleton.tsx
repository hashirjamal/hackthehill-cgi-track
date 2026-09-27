import { cn } from '../lib/cn'

/** A pulsing placeholder for something that is still loading. */
export default function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded-lg bg-gray-200/70', className)} aria-hidden />
}
