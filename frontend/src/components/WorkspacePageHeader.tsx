import React from 'react'

type PageMetric = { label: string; value: React.ReactNode }

interface WorkspacePageHeaderProps {
  title: React.ReactNode
  description?: React.ReactNode
  actions?: React.ReactNode
  metrics?: PageMetric[]
}

const WorkspacePageHeader: React.FC<WorkspacePageHeaderProps> = ({ title, description, actions, metrics }) => (
  <section className="workspace-page-header">
    <div className="workspace-page-header__main">
      <h1>{title}</h1>
      {description && <p>{description}</p>}
    </div>
    {actions && <div className="workspace-page-header__actions">{actions}</div>}
    {!!metrics?.length && <div className="workspace-page-header__metrics" aria-label="页面关键信息">
      {metrics.map((metric) => <div className="workspace-page-header__metric" key={metric.label}>
        <span>{metric.label}</span><strong>{metric.value}</strong>
      </div>)}
    </div>}
  </section>
)

export default WorkspacePageHeader
