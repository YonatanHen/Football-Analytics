import { initials } from '../../lib/format'

const SIZES = { sm: 'h-7 w-7 text-[9px]', md: 'h-12 w-12 text-sm', lg: 'h-16 w-16 text-lg' }

export default function Avatar({ name, size = 'sm' }: { name: string; size?: keyof typeof SIZES }) {
  return (
    <span
      className={`${SIZES[size]} inline-flex shrink-0 items-center justify-center rounded-full border border-line-strong bg-surface-2 font-mono text-muted`}
    >
      {initials(name)}
    </span>
  )
}
