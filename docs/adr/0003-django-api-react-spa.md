---
status: accepted
date: 2026-11-04
---
# Django backend with a JSON API; React single-page frontend

The backend is Django. Accounts, password hashing, sessions, roles and permissions, the ORM
with migrations, logging and CSRF come maintained and out of the box, and the solver's
Python contract can be imported directly rather than re-implemented. The API is served through
Django Ninja (Pydantic schemas, generated OpenAPI); Django REST Framework is the fallback if
Ninja proves limiting.

The frontend is a React + TypeScript single-page application built with Vite, compiled into
the application image at build time and served by the web container. The central screen is an
interactive roster grid (nurse × date with pinning, re-plan diffs and violations), which
server-rendered templates would make hard; everything else is forms.

## Considered options

- FastAPI: would need auth, sessions, ORM, migrations and admin assembled from separate packages.
- A non-Python backend: duplicates the solver's schema and validation in a second language.
- Django templates + HTMX for the frontend: fewer moving parts but a poor fit for the grid.
