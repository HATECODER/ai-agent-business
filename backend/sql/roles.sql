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

ALTER ROLE bizpilot_runtime NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS;
ALTER ROLE bizpilot_worker NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS;
ALTER ROLE bizpilot_authenticator NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS;

REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO bizpilot_runtime;
GRANT USAGE ON SCHEMA public TO bizpilot_authenticator;
