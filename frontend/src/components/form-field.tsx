import type { ComponentProps, ReactNode } from "react"
import type { FieldError as HookFormError, UseFormRegisterReturn } from "react-hook-form"

import { Field, FieldDescription, FieldError, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"

type FormFieldProps = {
  label: string
  description?: ReactNode
  registration: UseFormRegisterReturn
  /** Client-side validation's error for this field. */
  error?: HookFormError
} & Omit<ComponentProps<typeof Input>, keyof UseFormRegisterReturn>

/** A labelled input wired to React Hook Form, with its description and its error. */
export function FormField({ label, description, registration, error, ...input }: FormFieldProps) {
  const id = `field-${registration.name}`
  const descriptionId = description ? `${id}-description` : undefined
  const errorId = error ? `${id}-error` : undefined
  return (
    <Field data-invalid={!!error || undefined}>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <Input id={id} aria-invalid={!!error || undefined}
        aria-describedby={[errorId, descriptionId].filter(Boolean).join(" ") || undefined}
        {...input} {...registration} />
      {description && <FieldDescription id={descriptionId}>{description}</FieldDescription>}
      {/* Tied to its input and read when the input takes focus, so not an alert of its own. */}
      <FieldError id={errorId} role={undefined} errors={error ? [error] : undefined} />
    </Field>
  )
}
