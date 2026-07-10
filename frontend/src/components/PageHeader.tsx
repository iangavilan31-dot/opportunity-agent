import type { ReactNode } from 'react'

/** One header voice for every surface — the same letterspaced caps that title
 * the Field and the Atlas, so the workflow never feels like another product. */
export default function PageHeader({ kicker, title, children }: {
  kicker?: string
  title: string
  children?: ReactNode
}) {
  return (
    <div className="flex items-center gap-4 px-6 py-[18px] border-b border-border-subtle shrink-0">
      <div className="text-[13px] font-bold tracking-[0.28em] uppercase text-muted select-none">
        {kicker && <>{kicker}&nbsp;</>}
        <b className="text-primary">{title}</b>
      </div>
      <div className="flex-1" />
      {children}
    </div>
  )
}
