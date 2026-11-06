export type StatusPaneRow = {
  id: string
  title: string
  risk: string
  next: string
}
export type StatusPaneGroup = { name: string; count: number; rows: StatusPaneRow[] }
export type StatusPaneAgent = { id: string; type: string; description: string }

declare module 'claude-code' {
  interface PluginState {
    'status-pane': {
      view: Shaped<{ mtimeMs: number; groups: StatusPaneGroup[] }>
      agents: Shaped<StatusPaneAgent[]>
    }
  }
}
