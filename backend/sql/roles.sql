-- Run once per dedicated BizPilot database as a role allowed to create roles.
-- Passwords are provisioned by the deployment secret manager, never here.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'bizpilot_runtime') THEN
        CREATE ROLE bizpilot_runtime NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'bizpilot_worker') THEN
        CREATE ROLE bizpilot_worker NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'bizpilot_authenticator') THEN
        CREATE ROLE bizpilot_authenticator NOLOGIN;
    END IF;
END
$$;

-- Managed PostgreSQL providers do not expose real superuser access. New roles
-- default to NOSUPERUSER, NOREPLICATION and NOBYPASSRLS; deployment tooling
-- verifies those catalog flags instead of attempting superuser-only ALTERs.
ALTER ROLE bizpilot_runtime NOCREATEDB NOCREATEROLE NOINHERIT NOLOGIN;
ALTER ROLE bizpilot_worker NOCREATEDB NOCREATEROLE NOINHERIT NOLOGIN;
ALTER ROLE bizpilot_authenticator NOCREATEDB NOCREATEROLE NOINHERIT NOLOGIN;

REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO bizpilot_runtime;
GRANT USAGE ON SCHEMA public TO bizpilot_authenticator;
