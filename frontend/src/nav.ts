import { Bot, BookOpen, FolderSearch, Gauge, Layers, ListChecks, SlidersHorizontal, Users, type LucideIcon } from 'lucide-react'

export interface NavItem {
  to: string
  label: string
  icon: LucideIcon
}

export interface NavGroup {
  title: string
  items: NavItem[]
}

// One page for each view. Case detail (/cases/:id) opens from the Cases and Worklist pages.
export const navGroups: NavGroup[] = [
  {
    title: 'Work',
    items: [
      { to: '/worklist', label: 'Worklist', icon: ListChecks },
      { to: '/cases', label: 'Cases', icon: FolderSearch },
    ],
  },
  {
    title: 'Insights',
    items: [
      { to: '/backlog', label: 'Backlog', icon: Layers },
      { to: '/root-cause', label: 'Root cause', icon: Gauge },
      { to: '/accounts', label: 'Accounts', icon: Users },
      { to: '/profiles', label: 'Case profiles', icon: BookOpen },
    ],
  },
  {
    title: 'AI',
    items: [{ to: '/classification', label: 'Classification', icon: Bot }],
  },
  {
    title: 'Plan',
    items: [{ to: '/simulator', label: 'Simulator', icon: SlidersHorizontal }],
  },
]
