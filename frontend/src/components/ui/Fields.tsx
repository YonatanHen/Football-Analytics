import type { ReactNode } from 'react'
import { ChevronDown, type LucideIcon } from 'lucide-react'

export function IconInput({
  icon: Icon, value, onChange, placeholder, className = '',
}: {
  icon: LucideIcon; value: string; onChange: (v: string) => void
  placeholder: string; className?: string
}) {
  return (
    <label className={`relative block ${className}`}>
      <Icon size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-dim" />
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="field w-full pl-9 pr-3"
      />
    </label>
  )
}

export function Select({
  value, onChange, children, className = '', prefix, size = 'md',
}: {
  value: string; onChange: (v: string) => void; children: ReactNode
  className?: string; prefix?: string; size?: 'sm' | 'md'
}) {
  return (
    <label className={`relative block ${className}`}>
      {prefix && (
        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 font-mono text-[10px] text-dim">
          {prefix}
        </span>
      )}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={`field w-full appearance-none pr-8 ${size === 'sm' ? 'h-8 text-xs' : ''} ${prefix ? 'pl-7' : 'pl-3'} ${
          value ? 'text-ink' : 'text-dim'
        }`}
      >
        {children}
      </select>
      <ChevronDown size={14} className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-dim" />
    </label>
  )
}
