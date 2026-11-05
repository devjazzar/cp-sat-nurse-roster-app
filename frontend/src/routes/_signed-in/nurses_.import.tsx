import { zodResolver } from "@hookform/resolvers/zod"
import { createFileRoute, Link, useBlocker } from "@tanstack/react-router"
import { useEffect, useRef, useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { ApiError } from "@/api/fetcher"
import {
  getDownloadNurseImportTemplateUrl,
  useConfirmNurseImport,
  usePreviewNurseImport,
} from "@/api/generated/endpoints"
import { Role, type ImportPreview, type ImportRow, type SheetRow } from "@/api/generated/model"
import { FormField } from "@/components/form-field"
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { FieldGroup } from "@/components/ui/field"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { serverErrors, showServerErrors } from "@/lib/server-errors"
import { cn, scrollableRegion } from "@/lib/utils"
import { onlyFor } from "@/session"

export const Route = createFileRoute("/_signed-in/nurses_/import")({
  beforeLoad: onlyFor(Role.cno),
  staticData: { title: "Import nurses" },
  component: ImportPage,
})

// As in backend/nurses/importing.py, which has the last word. Here so a large file is not sent for nothing.
const MAX_ROWS = 500
const MAX_MEGABYTES = 1
const COULD_NOT_CHECK = "That did not work. Check your connection and try again."
const COLUMN_NAMES: Record<string, string> = {
  hospital_id: "Hospital ID",
  full_name: "Full name",
  gender: "Gender",
  unit: "Unit",
  start_date: "Start date",
}
const CELL = "max-w-64 whitespace-normal wrap-anywhere"

const nurseCount = (count: number) => (count === 1 ? "1 nurse" : `${count} nurses`)

/** The file as it was when checked, and what the check said. Held as bytes, so that what is confirmed is what was
 *  read, whatever happens to the file on disk. Nothing of it is kept anywhere else. */
type CheckedFile = { bytes: Blob; preview: ImportPreview }

const fileSchema = z.object({
  file: z.custom<FileList | null>()
    .refine((files) => !!files?.length, "Choose a CSV file.")
    .refine((files) => !files?.[0] || files[0].size <= MAX_MEGABYTES * 1024 * 1024,
      `This file is larger than ${MAX_MEGABYTES} MB, which is more than ${MAX_ROWS} nurses need.`),
})
type FileChoice = z.infer<typeof fileSchema>

function CheckFileForm({ busy, onChecked }: { busy: boolean; onChecked: (checked: CheckedFile) => void }) {
  const check = usePreviewNurseImport({ mutation: { gcTime: 0 } })
  const form = useForm<FileChoice>({ resolver: zodResolver(fileSchema), defaultValues: { file: null } })
  const [reading, setReading] = useState(false)
  const { errors } = form.formState

  const submit = form.handleSubmit(async ({ file: files }) => {
    let bytes: Blob
    setReading(true)
    try {
      bytes = new Blob([await (files as FileList)[0].arrayBuffer()])
    } catch {
      // A browser refuses to read a file that was saved again after it was chosen.
      form.setError("file", { message: "This file changed after you chose it. Choose it again." }, { shouldFocus: true })
      return
    } finally {
      setReading(false)
    }
    check.mutate({ data: { file: bytes } }, {
      onSuccess: (preview) => {
        check.reset()
        onChecked({ bytes, preview })
      },
      onError: (error) => showServerErrors(form, error),
    })
  })

  return (
    <form onSubmit={submit} noValidate>
      <FieldGroup>
        <FormField label="CSV file" type="file" accept=".csv,text/csv" registration={form.register("file")} error={errors.file} />
        {check.isError && serverErrors(check.error).length === 0 && <p role="alert" className="text-sm text-destructive">{COULD_NOT_CHECK}</p>}
        <div>
          <Button type="submit" disabled={busy || reading || check.isPending}>{check.isPending ? "Checking…" : "Check file"}</Button>
        </div>
      </FieldGroup>
    </form>
  )
}

function RowsTable({ rows, label }: { rows: ImportRow[]; label: string }) {
  const hasProblems = rows.some((row) => row.problems.length > 0)
  return (
    <Table container={scrollableRegion(label)}>
      <TableHeader>
        <TableRow>
          <TableHead>Line</TableHead>
          {hasProblems && <TableHead>Problems</TableHead>}
          <TableHead>Hospital ID</TableHead>
          <TableHead>Full name</TableHead>
          <TableHead>Gender</TableHead>
          <TableHead>Unit</TableHead>
          <TableHead>Start date</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.line}>
            <TableCell className="tabular-nums">{row.line}</TableCell>
            {hasProblems && (
              <TableCell className="min-w-64 whitespace-normal text-destructive">
                <ul className="flex flex-col gap-1">
                  {row.problems.map((problem) => (
                    <li key={`${problem.column}-${problem.message}`}>
                      {problem.column ? `${COLUMN_NAMES[problem.column]}: ` : ""}{problem.message}
                    </li>
                  ))}
                </ul>
              </TableCell>
            )}
            <TableCell translate="no" className={CELL}>{row.hospital_id}</TableCell>
            <TableCell className={cn(CELL, "min-w-32")}>{row.full_name}</TableCell>
            <TableCell className={CELL}>{row.gender}</TableCell>
            <TableCell className={CELL}>{row.unit}</TableCell>
            <TableCell className={cn(CELL, "min-w-24 tabular-nums")}>{row.start_date}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

function Preview({ file, changed, adding, refusal, onAdd }: {
  file: CheckedFile
  changed: boolean
  adding: boolean
  refusal: string | null
  onAdd: (token: string) => void
}) {
  const heading = useRef<HTMLHeadingElement>(null)
  const { rows, token } = file.preview
  const withProblems = rows.filter((row) => row.problems.length > 0)
  const fine = rows.length - withProblems.length

  useEffect(() => { heading.current?.focus() }, [file])

  return (
    <Card>
      <CardHeader>
        <CardTitle><h2 ref={heading} tabIndex={-1} className="outline-none">
          {token ? `${nurseCount(rows.length)} ready to add` : `${withProblems.length} of ${rows.length} ${rows.length === 1 ? "line" : "lines"} ${withProblems.length === 1 ? "has" : "have"} a problem`}
        </h2></CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {changed && <p role="alert" className="text-sm text-destructive">Something changed since the last check, so nothing was saved. This is how the file stands now.</p>}
        {token ? (
          <p>Nothing is saved until you add them.</p>
        ) : (
          <p>
            Nothing can be saved until every line is right. Correct the file, choose it above and check it again.
            {fine > 0 && ` The other ${fine === 1 ? "line has" : `${fine} lines have`} no problem.`}
          </p>
        )}
        {token && (
          <div className="flex flex-col items-start gap-2">
            <Button onClick={() => onAdd(token)} disabled={adding}>{adding ? "Adding…" : `Add ${nurseCount(rows.length)}`}</Button>
            <p role="status" className="text-sm text-muted-foreground empty:sr-only">
              {adding && "Making each password takes a moment on purpose, so a large file can take a few minutes. Keep this page open."}
            </p>
            {refusal && <p role="alert" className="text-sm text-destructive">{refusal}</p>}
          </div>
        )}
        <RowsTable rows={token ? rows : withProblems} label="Lines of the file" />
      </CardContent>
    </Card>
  )
}

/** A spreadsheet would run a pasted cell that starts like a formula, as `safe_cell` in backend/nurses/spreadsheets.py
 *  says, and a tab or a line break in a name would start a new cell. */
function pasteSafe(cell: string) {
  const oneCell = cell.replace(/[\t\r\n]+/g, " ")
  return /^ *[=+\-@＝＋－＠]/.test(oneCell) ? `'${oneCell}` : oneCell
}

function PasswordSheetCard({ rows, onDone }: { rows: SheetRow[]; onDone: () => void }) {
  const [copied, setCopied] = useState("")
  const heading = useRef<HTMLHeadingElement>(null)
  const region = scrollableRegion("Passwords")

  useEffect(() => { heading.current?.focus() }, [])

  async function copy() {
    const lines = rows.map((row) => [row.hospital_id, row.full_name, row.unit, row.generated_password].map(pasteSafe).join("\t"))
    try {
      await navigator.clipboard.writeText(["Hospital ID\tFull name\tUnit\tPassword", ...lines].join("\n"))
      setCopied("Copied.")
    } catch {
      setCopied("They could not be copied. Print the sheet, or select the table by hand.")
    }
  }

  return (
    <Card className="print:border-0 print:shadow-none">
      <CardHeader>
        <CardTitle><h2 ref={heading} tabIndex={-1} className="outline-none">Passwords for {nurseCount(rows.length)}</h2></CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <p className="print:hidden">
          The nurses are added. This is the only time these passwords are shown, so print or copy them before you close this.
          Each nurse must choose a new one at their next login.
        </p>
        <div className="flex flex-wrap gap-2 print:hidden">
          <Button onClick={() => window.print()}>Print</Button>
          <Button variant="outline" onClick={copy}>Copy all</Button>
          <Button variant="outline" onClick={onDone}>Done</Button>
        </div>
        <p role="status" className="text-sm text-muted-foreground empty:sr-only print:hidden">{copied}</p>
        <Table container={{ ...region, className: cn(region.className, "print:overflow-visible") }}>
          <TableHeader>
            <TableRow>
              <TableHead>Hospital ID</TableHead>
              <TableHead>Full name</TableHead>
              <TableHead>Unit</TableHead>
              <TableHead>Password</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.hospital_id} className="break-inside-avoid">
                <TableCell translate="no">{row.hospital_id}</TableCell>
                <TableCell className={cn(CELL, "min-w-32")}>{row.full_name}</TableCell>
                <TableCell className={CELL}>{row.unit}</TableCell>
                <TableCell translate="no" className="font-mono">{row.generated_password}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

function LeaveDialog({ open, title, action, onStay, onLeave }: { open: boolean; title: string; action: string; onStay: () => void; onLeave: () => void }) {
  return (
    <AlertDialog open={open} onOpenChange={(next) => { if (!next) onStay() }}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>
            Nobody can see these passwords again. A nurse without theirs needs a password reset, one at a time, on the Nurses page.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <Button variant="outline" onClick={onStay}>Stay</Button>
          <Button variant="destructive" onClick={onLeave}>{action}</Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}

function ImportPage() {
  const [file, setFile] = useState<CheckedFile | null>(null)
  const [changed, setChanged] = useState(false)
  const confirm = useConfirmNurseImport({ mutation: { gcTime: 0 } })
  const [sheet, setSheet] = useState<SheetRow[] | null>(null) // The passwords live in this state and nowhere else.
  const [finishing, setFinishing] = useState(false)
  const [done, setDone] = useState("")
  const heading = useRef<HTMLHeadingElement>(null)

  const holding = sheet !== null || confirm.isPending
  const blocker = useBlocker({ shouldBlockFn: () => holding, enableBeforeUnload: () => holding, withResolver: true, disabled: !holding })

  function add(token: string) {
    if (!file) return
    confirm.mutate({ data: { file: file.bytes, token } }, {
      onSuccess: (answer) => {
        confirm.reset() // The mutation holds its answer until told otherwise, and that answer holds passwords.
        setFile(null)
        setSheet(answer.rows)
      },
      onError: (error) => {
        if (error instanceof ApiError && error.status === 409) {
          confirm.reset()
          setChanged(true)
          setFile({ ...file, preview: error.body as ImportPreview })
        }
      },
    })
  }

  const refusal = confirm.isError ? (serverErrors(confirm.error)[0]?.message
    ?? "It is not known whether these nurses were added. Check the file again: a nurse who was added shows as already in use, and the Nurses page can reset their password.") : null

  function finish() {
    setDone(`${nurseCount(sheet?.length ?? 0)} added.`)
    setSheet(null)
    setFinishing(false)
    heading.current?.focus()
  }

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-4">
      <h1 ref={heading} tabIndex={-1} className="text-xl font-medium outline-none">Import nurses</h1>
      <p role="status" className="text-sm text-muted-foreground empty:sr-only print:hidden">{done}</p>
      {sheet ? (
        <PasswordSheetCard rows={sheet} onDone={() => setFinishing(true)} />
      ) : (
        <>
          <Card className="max-w-xl">
            <CardHeader><CardTitle><h2>Choose a file</h2></CardTitle></CardHeader>
            <CardContent className="flex flex-col gap-4">
              <p>
                <a href={getDownloadNurseImportTemplateUrl()} download className="underline underline-offset-4">Download the template</a>,
                {" "}fill in one nurse per line, up to {MAX_ROWS} in a file, and save it as CSV UTF-8.
                Or go back to <Link to="/nurses" className="underline underline-offset-4">Nurses</Link>.
              </p>
              <dl className="grid gap-x-4 gap-y-1 text-sm sm:grid-cols-[auto_1fr]">
                <dt className="font-medium">Hospital ID</dt>
                <dd className="mb-2 text-muted-foreground sm:mb-0">It becomes their username and cannot be corrected later. In Excel, format the column as Text so it keeps any leading zeros.</dd>
                <dt className="font-medium">Gender</dt>
                <dd className="mb-2 text-muted-foreground sm:mb-0">F or M.</dd>
                <dt className="font-medium">Unit</dt>
                <dd className="mb-2 text-muted-foreground sm:mb-0">Its name on the Units page.</dd>
                <dt className="font-medium">Start date</dt>
                <dd className="text-muted-foreground">YYYY-MM-DD, such as 2027-01-31. In Excel, format the column as yyyy-mm-dd, or saving changes the dates.</dd>
              </dl>
              <CheckFileForm busy={confirm.isPending} onChecked={(next) => { setDone(""); setChanged(false); confirm.reset(); setFile(next) }} />
            </CardContent>
          </Card>
          {file && <Preview file={file} changed={changed} adding={confirm.isPending} refusal={refusal} onAdd={add} />}
        </>
      )}
      <LeaveDialog open={blocker.status === "blocked"} title="Leave without the passwords?" action="Leave"
        onStay={() => blocker.reset?.()} onLeave={() => blocker.proceed?.()} />
      <LeaveDialog open={finishing} title="Close these passwords?" action="Close passwords"
        onStay={() => setFinishing(false)} onLeave={finish} />
    </div>
  )
}
