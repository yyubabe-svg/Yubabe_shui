import { FolderSearch } from 'lucide-react'

export default function Projects() {
  return (
    <div className="page-container max-w-3xl">
      <div className="page-header">
        <h1>历史工程</h1>
        <p>检索历史工程档案，对比工程参数与设计方案</p>
      </div>
      <div className="border border-neutral-200 bg-white">
        <div className="empty-state">
          <FolderSearch className="empty-state-icon" strokeWidth={1.5} />
          <p className="empty-state-text">请通过「文档入库」上传历史工程报告后进行检索</p>
        </div>
      </div>
    </div>
  )
}
