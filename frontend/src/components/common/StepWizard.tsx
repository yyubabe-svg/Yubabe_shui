import { CheckCircle2, type LucideIcon } from 'lucide-react'

export interface StepItem {
  key: string
  label: string
  icon?: LucideIcon
}

interface StepWizardProps {
  steps: readonly StepItem[]
  activeStep: string
  className?: string
}

export default function StepWizard({ steps, activeStep, className = '' }: StepWizardProps) {
  const currentIdx = steps.findIndex(s => s.key === activeStep)

  return (
    <div className={`flex items-center ${className}`}>
      {steps.map((step, i) => {
        const Icon = step.icon
        const isActive = activeStep === step.key
        const isDone = currentIdx > i

        return (
          <div key={step.key} className="flex items-center flex-1 last:flex-none">
            <div className="flex items-center gap-2">
              <div className={`step-dot ${
                isDone ? 'bg-success text-white' :
                isActive ? 'bg-brand-600 text-white' :
                'bg-neutral-100 text-neutral-400'
              }`}>
                {isDone ? (
                  <CheckCircle2 className="w-4 h-4" />
                ) : Icon ? (
                  <Icon className="w-3.5 h-3.5" />
                ) : (
                  <span className="text-xs">{i + 1}</span>
                )}
              </div>
              <span className={`text-sm whitespace-nowrap ${
                isActive ? 'text-neutral-900 font-medium' :
                isDone ? 'text-success' :
                'text-neutral-400'
              }`}>
                {step.label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div className={`step-line ${isDone ? 'bg-success' : 'bg-neutral-200'}`} />
            )}
          </div>
        )
      })}
    </div>
  )
}
