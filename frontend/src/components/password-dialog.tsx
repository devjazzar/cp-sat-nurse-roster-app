import { useBlocker } from "@tanstack/react-router"
import { useRef, useState } from "react"

import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

/** The password from a creation or a reset. It lives in this state and nowhere else, until Done. */
export type Shown = { username: string; full_name: string; password: string }

export function PasswordDialog({ shown, onDone }: { shown: Shown | null; onDone: () => void }) {
  const [copied, setCopied] = useState("")
  const passwordBox = useRef<HTMLInputElement>(null)
  // Going back or reloading would lose a password nobody can see again.
  useBlocker({ shouldBlockFn: () => shown !== null, enableBeforeUnload: () => shown !== null, disabled: shown === null })

  async function copy() {
    try {
      await navigator.clipboard.writeText(shown?.password ?? "")
      setCopied("Copied.")
    } catch {
      setCopied("It could not be copied. It is selected in the box: copy it by hand.")
      passwordBox.current?.select()
    }
  }

  // Only Done closes this: nobody can see the password again, so Escape must not lose it either.
  return (
    <AlertDialog open={shown !== null}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Password for {shown?.username}</AlertDialogTitle>
          <AlertDialogDescription>
            This is the only time it is shown. Give it to {shown?.full_name}, who must choose a new one at their next login.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <Input ref={passwordBox} readOnly translate="no" aria-label="Generated password" value={shown?.password ?? ""}
          autoComplete="off" spellCheck={false} onFocus={(event) => event.target.select()}
          className="text-center font-mono text-base md:text-base" />
        <p role="status" className="text-sm text-muted-foreground empty:sr-only">{copied}</p>
        <AlertDialogFooter>
          <Button variant="outline" onClick={copy}>Copy password</Button>
          <Button onClick={() => { setCopied(""); onDone() }}>Done</Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
