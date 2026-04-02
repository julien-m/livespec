# TaskFlow

## Description

TaskFlow is a lightweight project management tool designed for small engineering teams. It provides task tracking, sprint planning, and team velocity analytics through a clean web interface backed by a REST API and PostgreSQL database.

## Target Users

- **Engineering Leads**: manage sprints, assign tasks, review team velocity and burndown charts
- **Developers**: create and update tasks, log time, track personal workload across sprints
- **Product Managers**: define epics, prioritize the backlog, and monitor delivery progress

## Core Problem

Small teams (3-10 engineers) need a task tracker that is fast, opinionated, and developer-friendly. Existing tools are either too heavy (Jira) or too minimal (sticky notes). TaskFlow sits in the middle: structured enough for sprint ceremonies, lightweight enough that devs actually use it.

## Constraints

- Must support PostgreSQL 16 as the sole data store
- API response time under 200ms for all CRUD operations at p95
- Single-tenant deployment (one database per team instance)
- No external authentication provider dependency; built-in email/password auth with JWT
- Frontend must be server-rendered for initial load, with client-side hydration for interactivity
