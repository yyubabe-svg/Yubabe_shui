interface StreamingTextProps {
  text: string
  className?: string
}

export default function StreamingText({ text, className = '' }: StreamingTextProps) {
  return (
    <span className={className}>
      {text}
      <span className="inline-block w-1.5 h-4 bg-brand-500 animate-pulse ml-0.5 align-middle" />
    </span>
  )
}
