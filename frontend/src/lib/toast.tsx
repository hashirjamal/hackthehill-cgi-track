import { AlertCircle, CheckCircle2, Info, Loader2 } from 'lucide-react'
import { Toaster } from 'sonner'

/** Toasts in the app's style: whitish card, soft shadow, no border, a coloured icon for the kind of message. */
export function AppToaster() {
  return (
    <Toaster
      position="bottom-right"
      gap={12}
      visibleToasts={4}
      icons={{
        success: <CheckCircle2 className="h-5 w-5" />,
        error: <AlertCircle className="h-5 w-5" />,
        info: <Info className="h-5 w-5" />,
        loading: <Loader2 className="h-5 w-5 animate-spin" />,
      }}
      toastOptions={{
        unstyled: true,
        duration: 5000,
        classNames: {
          toast:
            'group flex w-[23rem] max-w-[calc(100vw-2rem)] items-start gap-3 rounded-2xl bg-card px-4 py-3.5 font-sans shadow-xl shadow-gray-900/15',
          icon: 'mt-0.5 shrink-0 group-data-[type=success]:text-emerald-600 group-data-[type=error]:text-red-600 group-data-[type=info]:text-brand group-data-[type=loading]:text-brand',
          content: 'flex min-w-0 flex-1 flex-col gap-0.5',
          title: 'text-sm font-semibold text-gray-900',
          description: 'text-sm leading-snug text-gray-600',
          actionButton: 'ml-2 shrink-0 self-center rounded-lg bg-brand px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-dark',
          cancelButton: 'ml-2 shrink-0 self-center rounded-lg bg-gray-100 px-3 py-1.5 text-xs font-semibold text-gray-600 hover:bg-gray-200',
        },
      }}
    />
  )
}
