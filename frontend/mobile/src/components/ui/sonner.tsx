import { useTheme } from '@shared/hooks/useTheme'
import { Toaster as Sonner, ToasterProps } from "sonner"

const Toaster = ({ ...props }: ToasterProps) => {
  const { theme } = useTheme()
  const sonnerTheme: ToasterProps["theme"] = theme === 'dark' ? 'dark' : 'light'

  return (
    <Sonner
      theme={sonnerTheme}
      richColors={true}
      position="top-center"
      className="toaster group"
      style={
        {
          zIndex: 99999,
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--border)",
          "--success-bg": "color-mix(in srgb, var(--color-success) 8%, var(--popover))",
          "--success-text": "var(--popover-foreground)",
          "--success-border": "var(--color-success)",
          "--error-bg": "color-mix(in srgb, var(--color-destructive) 8%, var(--popover))",
          "--error-text": "var(--popover-foreground)",
          "--error-border": "var(--color-destructive)",
          "--warning-bg": "color-mix(in srgb, var(--color-warning) 8%, var(--popover))",
          "--warning-text": "var(--popover-foreground)",
          "--warning-border": "var(--color-warning)",
          "--top-spacing": "1.5rem",
        } as React.CSSProperties
      }
      {...props}
    />
  )
}

export { Toaster }