"""Build a NEW empty Neon app database; never run against the legacy Supabase DB."""
from pathlib import Path
import re

ROOT=Path(__file__).parent
HEADER='''-- Install once in each NEW Neon database, as its project owner.
-- Change PRODUCT_NAME below to bpo, procurement or vakil before running.
begin;
create schema gi_auth;
revoke all on schema gi_auth from public;
do $$ begin
 if not exists(select 1 from pg_roles where rolname='anon') then create role anon nologin; end if;
 if not exists(select 1 from pg_roles where rolname='authenticated') then create role authenticated nologin; end if;
 if not exists(select 1 from pg_roles where rolname='service_role') then create role service_role nologin; end if;
end $$;
grant anon,authenticated to current_user;
create table gi_auth.deployment(singleton boolean primary key default true check(singleton), product text not null check(product in ('bpo','procurement','vakil')));
insert into gi_auth.deployment values(true,'PRODUCT_NAME');
create table gi_auth.users(id text primary key, email text not null, created_at timestamptz not null, raw_user_meta_data jsonb not null default '{}');
revoke all on all tables in schema gi_auth from public,anon,authenticated;
create function gi_auth.uid() returns text language sql stable as $$ select nullif(current_setting('gi.user_id',true),'') $$;
grant usage on schema gi_auth to authenticated;
grant execute on function gi_auth.uid() to authenticated;
'''

def build():
    parts=[HEADER]
    for name in ['supabase_vakil_schema.sql','supabase_work_hub.sql','supabase_trial_limits.sql','supabase_owner_admin.sql']:
        path=ROOT/name
        if not path.exists(): path=ROOT.parent/'excellence'/name
        text=path.read_text(encoding='utf-8')
        text=re.sub(r'^\s*(begin|commit);\s*$', '', text, flags=re.M|re.I)
        text=text.replace('auth.users','gi_auth.users').replace('auth.uid()','gi_auth.uid()')
        # Better Auth identities need not be UUIDs. Record IDs retain random UUID
        # values represented as text, with existing constraints and RLS intact.
        text=re.sub(r'\buuid\b','text',text)
        text=text.replace('default gen_random_uuid()','default (gen_random_uuid()::text)')
        parts.append(text)
    parts.append('''
-- Never expose application tables to the unauthenticated role.
revoke all on all tables in schema public from anon;
grant usage on schema public to anon,authenticated;
commit;
''')
    return '\n'.join(parts)

if __name__=='__main__':
    (ROOT/'neon_app_schema.sql').write_text(build(),encoding='utf-8')
