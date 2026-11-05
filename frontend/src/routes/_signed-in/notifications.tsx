import { useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"

import {
  getCountUnreadNotificationsQueryKey, getListNotificationsQueryKey, useListNotifications, useMarkAllNotificationsRead,
  useMarkNotificationRead,
} from "@/api/generated/endpoints"
import type { NotificationLink, NotificationRow } from "@/api/generated/model"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { cn, hospitalTime } from "@/lib/utils"

/** Every role's: each user reads only their own. */
export const Route = createFileRoute("/_signed-in/notifications")({
  staticData: { title: "Notifications" },
  component: NotificationsPage,
})

const LINK = "underline underline-offset-3"

function Open({ link, onOpen }: { link: NotificationLink; onOpen: () => void }) {
  switch (link.page) {
    case "roster":
      return <Link to="/roster" search={{ month: link.month }} onClick={onOpen} className={LINK}>Open the roster</Link>
    case "my_roster":
      return <Link to="/my-roster" search={{ month: link.month }} onClick={onOpen} className={LINK}>Open My roster</Link>
    case "unit_roster":
      return <Link to="/unit-roster" search={{ unit: link.unit_id ?? undefined, month: link.month }} onClick={onOpen} className={LINK}>Open the roster</Link>
  }
}

function useRefreshed() {
  const queryClient = useQueryClient()
  // On the hook, not on `mutate`, so it still runs once the page has been left by the link that marked one read.
  return {
    mutation: {
      onSettled: () => Promise.all([
        queryClient.invalidateQueries({ queryKey: getListNotificationsQueryKey() }),
        queryClient.invalidateQueries({ queryKey: getCountUnreadNotificationsQueryKey() }),
      ]),
    },
  }
}

function Row({ note }: { note: NotificationRow }) {
  const markRead = useMarkNotificationRead(useRefreshed())
  const onOpen = () => { if (!note.read) markRead.mutate({ notificationId: note.id }) }
  return (
    <li className={cn("flex flex-col gap-1 border-b py-3 last:border-b-0", note.read && "text-muted-foreground")}>
      <p className={cn(!note.read && "font-medium text-foreground")}>
        {!note.read && <Badge className="me-2 align-middle">New</Badge>}
        {note.text}
      </p>
      <p className="flex flex-wrap gap-x-3 text-sm">
        <span className="text-muted-foreground">{hospitalTime(note.created_at)}</span>
        {note.link && <Open link={note.link} onOpen={onOpen} />}
        {!note.read && !note.link && (
          <Button variant="link" size="sm" className="h-auto p-0" onClick={onOpen} disabled={markRead.isPending}>Mark as read</Button>
        )}
      </p>
    </li>
  )
}

function NotificationsPage() {
  const list = useListNotifications()
  const markAll = useMarkAllNotificationsRead(useRefreshed())
  const answer = list.data
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <h1 className="text-xl font-medium">Notifications</h1>
      {list.isPending && <p>Loading…</p>}
      {list.isError && <p role="alert">Your notifications could not be read. Reload the page to try again.</p>}
      {answer && answer.items.length === 0 && <p>You have no notifications.</p>}
      {answer && answer.items.length > 0 && (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <p role="status">{answer.unread === 0 ? "All read." : `${answer.unread} unread.`}</p>
            {answer.unread > 0 && (
              <Button variant="outline" size="sm" onClick={() => markAll.mutate()} disabled={markAll.isPending}>Mark all as read</Button>
            )}
          </div>
          <ul aria-label="Notifications, newest first">
            {answer.items.map((note) => <Row key={note.id} note={note} />)}
          </ul>
        </>
      )}
    </div>
  )
}
