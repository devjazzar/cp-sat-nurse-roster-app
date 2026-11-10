# Installing and running the nurse roster

For the hospital's IT. One installation serves one hospital, as one `docker compose` stack on one server: Caddy in front,
the web application, the queue worker, the solver and PostgreSQL (docs/ARCHITECTURE.md, section 2). Every command here runs
in this `deploy/` directory on the server.

## Install

You need Docker with Compose v2.24 or later, ports 80 and 443 open to the people who use it, and, for a real certificate, a
name whose DNS points at the server. For pushes, the server must also reach the browsers' push services over HTTPS; a
server that cannot loses pushes and nothing else ([Pushes](#pushes)).

```bash
cp .env.example .env
```

Fill in the four required values in `.env` (the file says how to generate them), and `DOMAIN` if the server has a name. Then:

```bash
docker compose up -d
```

Five services come up: `caddy`, `web`, `worker`, `solver` and `db`. Check them through Caddy:

```bash
curl -k https://localhost/api/health
```

The answer is `{"status": "ok", "database": true, "solver": {"reachable": true}}`. The solver's version and threads are on the
System Admin's health page, not here: anyone can read this one.

Open `https://<server>/` and log in as `admin` with `INITIAL_ADMIN_PASSWORD`. You must choose a new password at once; from
then on the variable is ignored.

**On a server reachable from the internet, set `DOMAIN`.** Without it Caddy issues a self-signed certificate for any name a
client sends, and each adds files to the `caddy_data` volume.

### At the first real install

These cannot be proven anywhere but on the hospital's own server.

- **Let's Encrypt.** With `DOMAIN` set and its DNS pointing here, Caddy obtains a certificate by itself at the first start.
  Open `https://<DOMAIN>/` in a browser and look at the certificate: it must be issued by Let's Encrypt, not by "Caddy Local
  Authority". If it is not, `docker compose logs caddy` says why (most often port 80 or 443 is not reachable from the
  internet, or the DNS does not point here yet). This has never been proven: no certificate was issued while building, for want
  of a real name.
- **The 500-row nurse import against gunicorn's timeout.** Confirming an import hashes one password a nurse, about half a
  second each, four at once, in one request, and gunicorn gives a request 300 seconds (`--timeout 300` in `compose.yaml`).
  500 rows took 62.5 seconds on 8 cores of a development machine; no hospital server has been measured. Before any real
  nurse is added, take a backup (`docker compose exec worker python manage.py backup`, which prints its name), import 500
  made-up nurses from the template on the Nurses page and time the confirmation, then restore that backup
  (`./restore.sh <name>`), since nothing in the application deletes a nurse. Well under 300 seconds is fine. Near it, keep
  imports smaller, or raise `--timeout` in `compose.yaml`.
- **The install checklist** below.

### The install checklist: what only the hospital's people can check

- [ ] The roster's Excel file opened in Excel on Windows with a `;` list separator (a European locale), not only the default `,`.
- [ ] The roster's print page printed on a real printer: A4 landscape, a 31-day month on one page, the header row repeated.
- [ ] One pass of the main pages with the keyboard alone and with a screen reader.
- [ ] Caddy in a browser at the hospital's own address: the certificate (Let's Encrypt with `DOMAIN`, or the self-signed one), and the app through it.
- [ ] Time a solve, a draft's read and a re-plan's comparison on a 60-nurse unit on the real server.
- [ ] Time the audit log filtered by user on the real database.
- [ ] The 500-row import, timed as above.
- [ ] A backup restored with `./restore.sh` on the real server, and the application checked afterwards.
- [ ] Pushes, at the hospital's own address ([Pushes](#pushes)): turn them on in an ordinary Chrome on a computer and on a
      phone (an iPhone after adding the app to the Home Screen), then have a colleague propose a swap to that nurse. One push
      shows one notification, with no second one from the browser saying the site "has been updated in the background"; a tap
      opens Swaps; and the health page's Pushes card counts it as sent, with no failure. This has never been seen on a real
      host name: while building, only a Chrome started by hand against a self-signed certificate received one.

## Upgrade

```bash
docker compose pull && docker compose up -d
```

`web` runs the migrations as it starts.

## Backups

The worker takes a backup every night at the System Admin's backup time (02:00 hospital time unless changed on Technical
settings) and keeps the System Admin's number of days (30 unless changed), always keeping the newest whatever its age. A worker
that was down takes the missed one when it comes back, at most five minutes late. The first is taken within five minutes of
the first start.

A backup is the whole database in `pg_dump`'s custom format, named for when it was taken in UTC, for instance
`nurse-roster-20261105T230000Z.dump`. They live in the `backups` volume, which only `worker` (writing) and `web` (reading)
mount, and only the System Admin sees them: listed on the health page with sizes and dates and the time of the last one, and
downloaded from there. Each download is in the audit log.

**A backup holds everything:** every account's password hash and every nurse's leave. Keep any copy as safe as the server.

**Copies off the server are the hospital's job.** A disk that fails takes the backups with it. Copy them somewhere else every
day, for instance:

```bash
docker compose cp worker:/backups ./backups-copy
```

or download one from the health page.

### Restore a backup

Restore is a script on the server, not a button:

```bash
./restore.sh nurse-roster-20261105T230000Z.dump
```

It takes either the name of a backup the server keeps (the names are on the health page) or the path of a file, such as an
off-site copy. It asks you to type `RESTORE`, then:

1. stops `web` and `worker`, so nothing writes (Caddy stays up and answers 502 meanwhile);
2. takes a backup of the database as it stands, kept beside the others, so a wrong choice can be undone by restoring that one;
3. restores into a new database, and only once that has worked puts it in place of the old one: the old one is renamed
   aside, the restored one renamed in, and the old one dropped last;
4. starts `web` and `worker` again. A backup from an older version is migrated forward as `web` starts.

If it fails, or is stopped, before step 3 ends, the database is as it was and the application starts again on it. Everything
done since the backup is gone: solves running then start again from the queue, and anything a user did since must be done
again.

Should the server itself go down in the middle of step 3, a database called `nurse_roster_replaced` may be left, holding the
data as it was before the restore, and the script refuses to run again while it exists. If `nurse_roster` is missing, rename it
back (`docker compose exec db psql -U nurse_roster -d postgres -c "ALTER DATABASE nurse_roster_replaced RENAME TO nurse_roster"`);
if both exist, check the application, then drop the old one (`… -c "DROP DATABASE nurse_roster_replaced"`).

## Reset the System Admin's password

For a lost password, or the System Admin's account locked by five wrong passwords (a lock lasts 15 minutes, and anyone can
cause one):

```bash
./reset-admin-password.sh
```

It prints a new password once, which must be changed at the next login, ends the account's sessions and lifts the lock. The
audit log records it as done from the server. It needs the `db` service running; `web` may be down. `--username <name>` resets another System Admin account. Other accounts'
passwords are reset in the application.

## Logs

Every container logs to standard output: `web`, `worker` and `solver` as one JSON object a line, Caddy as JSON of its own,
and PostgreSQL in its own plain format:

```bash
docker compose logs -f worker
```

**The worker's log can hold names and dates:** a solver's error or a refusal's words can name a nurse and a day. Treat these
logs as personal data: keep them only as long as you need, let only the people who run the server read them, and send them
nowhere the hospital's rules on personal data do not allow. `compose.yaml` rotates each container's log at 10 MB and keeps
five files; change `x-logging` there to keep less.

## Metrics

`web` answers `/metrics` in Prometheus's text format, with no sign-in, on the internal network only: Caddy refuses the path,
and the application refuses anything that came through Caddy. A Prometheus that scrapes it joins the stack's `frontend` network
(`nurse-roster_frontend` unless the project has another name), for instance in a `compose.override.yaml` beside `compose.yaml`:

```yaml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    networks: [frontend]
```

with `prometheus.yml` scraping `web:8000`. What it reads is what the health page shows: whether the database and the solver
answer, the queue's jobs and workers, solves by state, the database's size, the disk's free space, and the backups kept with
the time of the last one (`nurse_roster_last_backup_timestamp_seconds`, worth an alert when it is more than a day old), and
the pushes sent and failed in the last 24 hours (`nurse_roster_push_attempts{outcome="sent"}` and `{outcome="failed"}`; a
failed count that keeps climbing while sent stays at zero says the push services cannot be reached).

## Pushes

A user may turn pushes on for a phone or a computer, on the Notifications page. The application then tells that device when
something with a deadline waits for them (a swap to answer, requests open, a roster to approve), through the push service of
the device's own browser: Google's, Mozilla's, Apple's or Microsoft's. A push says only which kind of thing waits, never a
name, a date or a unit, and nothing is sent to any other third party.

**Only the worker sends them,** over HTTPS (port 443), through the stack's `egress` network, the one network of an application
service that is not internal. `web`, the database and the solver stay on internal networks and reach nothing outside. If the
server's outbound connections are filtered, allow HTTPS from the server to these names, and nothing else is needed:

- `fcm.googleapis.com`: Google's, for Chrome and most browsers on Android;
- `push.services.mozilla.com` and `*.push.services.mozilla.com`: Mozilla's, for Firefox;
- `*.push.apple.com`: Apple's, for Safari and every browser on an iPhone or iPad;
- `*.notify.windows.com`: Microsoft's, for Edge on Windows.

The application sends to these hosts and refuses any other (`backend/notifications/subscriptions.py`); a test of the
application fails when this list and that one differ.

**A firewall that blocks them loses pushes and nothing else.** Every page works as before and every notification is still on
the bell; a nurse is only not told on her phone. Nothing is queued for later: a push that cannot be sent is tried again three
times over about ten minutes, then dropped.

**The check is the health page's Pushes card:** pushes sent and failed in the last 24 hours, and why the last one failed.
Each send to one device counts, and so does each try again, so one push to a blocked service counts four failures.

- `Unreachable`, with failures climbing and nothing sent: the worker cannot reach the push services. Look at the firewall, and
  at `docker compose exec worker python -c "import urllib.request as u; u.urlopen('https://fcm.googleapis.com', timeout=10)"`,
  which must not end in a timeout or a refused connection (an HTTP error such as 404 is an answer, and is fine).
- `Refused`: the push service answered and would not take the push. Expect it for a while after the key pair is replaced
  (below), until each device has opened the application again.
- `Gone`: a device's subscription had ended, as when notifications are turned off in its browser. It is removed at once, and
  nothing needs doing.

**The installation's push key pair** names it to the push services. It is made at the first start with no step of yours
(`web` logs "Made the installation's push key pair." once), lives in the database, and so comes back from a backup together
with the devices bound to it. If the database or a backup may have been read by someone who should not have, replace it:

```bash
docker compose exec web python manage.py rotate_push_keys
```

No one has to turn pushes on again: each device takes the new key the next time its user opens the application, and gets no
push until then. The audit log records the replacement as done from the server.

## What the queue keeps

The worker removes, every day: queue rows of jobs that ended well or were stopped more than seven days ago, and of failed jobs
more than thirty days ago (so the health page's failed jobs are the last month's); notifications older than a year; sessions
past their twelve idle hours; and the record of each push sent or failed, which holds a time and an outcome and nothing of a
user or a device, after seven days. A backup that cannot be taken is tried again every five minutes, each try a failed job, until it
works: a failed count that climbs by twelve an hour says so, and `docker compose logs worker` says why.
