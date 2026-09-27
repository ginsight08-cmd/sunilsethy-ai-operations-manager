-- Install once in each NEW Neon database, as its project owner.
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

-- Run once in Supabase Dashboard > SQL Editor.
create extension if not exists pgcrypto;

create table if not exists public.vakil_clients (
  id text primary key default (gen_random_uuid()::text),
  user_id text not null references gi_auth.users(id) on delete cascade,
  client_name text not null,
  client_type text not null default 'Individual',
  phone text not null default '',
  email text not null default '',
  address text not null default '',
  identity_reference text not null default '',
  notes text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.vakil_cases (
  id text primary key default (gen_random_uuid()::text),
  user_id text not null references gi_auth.users(id) on delete cascade,
  client_id text not null references public.vakil_clients(id) on delete restrict,
  client_name text not null,
  case_number text not null,
  case_title text not null default '',
  court_name text not null default '',
  case_type text not null default '',
  filing_number text not null default '',
  opposing_party text not null default '',
  status text not null default 'Consultation',
  priority text not null default 'Normal',
  advocate_name text not null default '',
  filing_date date,
  next_hearing_date date,
  description text not null default '',
  notes text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, case_number)
);

create table if not exists public.vakil_notification_log (
  id text primary key default (gen_random_uuid()::text),
  user_id text not null references gi_auth.users(id) on delete cascade,
  case_id text not null references public.vakil_cases(id) on delete cascade,
  client_id text references public.vakil_clients(id) on delete set null,
  channels text[] not null default '{}',
  recipient_email text not null default '',
  recipient_phone text not null default '',
  message text not null,
  delivery_status text not null,
  provider_response text not null default '',
  created_at timestamptz not null default now()
);

create index if not exists vakil_clients_user_id_idx on public.vakil_clients(user_id);
create index if not exists vakil_cases_user_id_idx on public.vakil_cases(user_id);
create index if not exists vakil_cases_hearing_idx on public.vakil_cases(user_id, next_hearing_date);
create index if not exists vakil_notification_user_idx on public.vakil_notification_log(user_id, created_at desc);

alter table public.vakil_clients enable row level security;
alter table public.vakil_cases enable row level security;
alter table public.vakil_notification_log enable row level security;

drop policy if exists "Users manage own vakil clients" on public.vakil_clients;
create policy "Users manage own vakil clients" on public.vakil_clients
for all using (gi_auth.uid() = user_id) with check (gi_auth.uid() = user_id);

drop policy if exists "Users manage own vakil cases" on public.vakil_cases;
create policy "Users manage own vakil cases" on public.vakil_cases
for all using (gi_auth.uid() = user_id) with check (gi_auth.uid() = user_id);

drop policy if exists "Users manage own vakil notifications" on public.vakil_notification_log;
create policy "Users manage own vakil notifications" on public.vakil_notification_log
for all using (gi_auth.uid() = user_id) with check (gi_auth.uid() = user_id);

grant select, insert, update, delete on public.vakil_clients to authenticated;
grant select, insert, update, delete on public.vakil_cases to authenticated;
grant select, insert, update, delete on public.vakil_notification_log to authenticated;

-- Additive migration: run in Supabase SQL Editor. Existing industry tables are unchanged.

create table if not exists public.work_hub_records (
  id text primary key default (gen_random_uuid()::text),
  user_id text not null references gi_auth.users(id) on delete cascade,
  industry text not null check (industry in ('BPO','Manufacturing','CaseManagement','Retail','Logistics','Healthcare')),
  kind text not null check (kind in ('client','work','task','document','draft','time')),
  title text not null check (length(trim(title)) between 1 and 300),
  status text not null,
  parent_id text,
  owner_name text not null default '',
  due_date date,
  details jsonb not null default '{}' check (jsonb_typeof(details) = 'object' and octet_length(details::text) <= 65536),
  version integer not null default 1,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(user_id, id),
  foreign key(user_id, parent_id) references public.work_hub_records(user_id, id) on delete restrict,
  check (
    (kind='client' and status in ('Lead','Qualified','Active','Archived') and parent_id is null) or
    (kind='work' and status in ('Intake','In progress','On hold','Completed') and parent_id is not null) or
    (kind='task' and status in ('Open','In progress','Done') and parent_id is not null) or
    (kind='document' and status='Reference' and parent_id is not null) or
    (kind='draft' and status in ('Draft','Pending review','Approved','Rejected') and parent_id is not null) or
    (kind='time' and status='Recorded' and parent_id is not null)
  )
);
create index if not exists work_hub_scope_idx on public.work_hub_records(user_id, industry, updated_at desc);
create table if not exists public.work_hub_events (
  id bigint generated always as identity primary key,
  user_id text not null references gi_auth.users(id) on delete cascade,
  industry text not null,
  record_id text not null references public.work_hub_records(id),
  event text not null,
  version integer not null,
  title text not null,
  status text not null,
  details jsonb not null,
  created_at timestamptz not null default now()
);
create index if not exists work_hub_events_scope_idx on public.work_hub_events(user_id, industry, created_at desc);
alter table public.work_hub_records enable row level security;
alter table public.work_hub_events enable row level security;
drop policy if exists work_hub_owner on public.work_hub_records;
create policy work_hub_owner on public.work_hub_records for all to authenticated
  using (gi_auth.uid() = user_id) with check (gi_auth.uid() = user_id);
drop policy if exists work_hub_audit_read on public.work_hub_events;
create policy work_hub_audit_read on public.work_hub_events for select to authenticated using (gi_auth.uid() = user_id);
revoke all on public.work_hub_records, public.work_hub_events from anon, authenticated;
grant select, insert, update on public.work_hub_records to authenticated;
grant select on public.work_hub_events to authenticated;

create or replace function public.work_hub_validate() returns trigger
language plpgsql set search_path = public as $$
declare parent_kind text; parent_industry text; changed boolean;
begin
  if tg_op='UPDATE' then
    if new.id <> old.id or new.user_id <> old.user_id or new.kind <> old.kind or new.industry <> old.industry or new.created_at <> old.created_at then
      raise exception 'Record identity cannot be changed';
    end if;
    new.version := old.version + 1;
  else
    new.version := 1;
    new.created_at := now();
    if new.kind='draft' and new.status <> 'Draft' then raise exception 'New content must start as a draft'; end if;
  end if;
  new.updated_at := now();
  if new.parent_id is not null then
    select kind, industry into parent_kind, parent_industry from public.work_hub_records
      where id=new.parent_id and user_id=new.user_id;
    if parent_industry is distinct from new.industry or
       parent_kind is distinct from (case when new.kind='work' then 'client' else 'work' end) then
      raise exception 'Invalid related record';
    end if;
  end if;
  if new.kind='draft' then
    if coalesce(length(trim(new.details->>'body')),0)=0 then raise exception 'Draft body is required'; end if;
    if tg_op='UPDATE' then
      changed := new.details is distinct from old.details or new.title is distinct from old.title or new.parent_id is distinct from old.parent_id;
      if changed and new.status <> 'Draft' then raise exception 'Changed content requires a new review'; end if;
      if not changed and not (
        (old.status='Draft' and new.status in ('Draft','Pending review')) or
        (old.status='Pending review' and new.status in ('Draft','Approved','Rejected')) or
        (old.status in ('Approved','Rejected') and new.status='Draft')
      ) then raise exception 'Invalid review transition'; end if;
    end if;
  end if;
  if new.kind='time' then
    if jsonb_typeof(new.details->'minutes') is distinct from 'number' or
       jsonb_typeof(new.details->'hourly_rate') is distinct from 'number' or
       jsonb_typeof(new.details->'currency') is distinct from 'string' or
       (new.details->>'minutes')::numeric not between 1 and 1440 or
       (new.details->>'hourly_rate')::numeric not between 0 and 1000000 or
       new.details->>'currency' not in ('INR','USD','EUR','GBP') then
      raise exception 'Invalid time entry';
    end if;
  end if;
  return new;
end $$;
drop trigger if exists work_hub_validate on public.work_hub_records;
create trigger work_hub_validate before insert or update on public.work_hub_records
for each row execute function public.work_hub_validate();

create or replace function public.work_hub_audit() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  insert into public.work_hub_events(user_id, industry, record_id, event, version, title, status, details)
  values(new.user_id, new.industry, new.id, tg_op, new.version, new.title, new.status, to_jsonb(new));
  return new;
end $$;
revoke all on function public.work_hub_audit() from public;
drop trigger if exists work_hub_audit on public.work_hub_records;
create trigger work_hub_audit after insert or update on public.work_hub_records
for each row execute function public.work_hub_audit();

-- Server-only admission; no client may reset or forge usage.

create table if not exists public.trial_analysis_usage (
  user_id text not null references gi_auth.users(id) on delete cascade,
  analysis_key text not null check (analysis_key ~ '^[a-f0-9]{64}$'),
  created_at timestamptz not null default now(),
  primary key(user_id, analysis_key)
);
alter table public.trial_analysis_usage enable row level security;
revoke all on public.trial_analysis_usage from public, anon, authenticated;
create or replace function public.admit_trial_analysis(p_user_id text, p_analysis_key text)
returns jsonb language plpgsql security definer set search_path = public as $$
declare joined timestamptz; used integer;
begin
  -- The user-row lock serializes admissions across devices and app sessions.
  select created_at into joined from gi_auth.users where id=p_user_id for update;
  if joined is null or now() >= joined + interval '3 days' then
    return jsonb_build_object('allowed',false,'reason','expired');
  end if;
  select count(*) into used from public.trial_analysis_usage where user_id=p_user_id;
  if exists(select 1 from public.trial_analysis_usage where user_id=p_user_id and analysis_key=p_analysis_key) then
    return jsonb_build_object('allowed',true,'remaining',greatest(0,5-used));
  end if;
  if used >= 5 then return jsonb_build_object('allowed',false,'reason','limit','remaining',0); end if;
  insert into public.trial_analysis_usage(user_id,analysis_key) values(p_user_id,p_analysis_key);
  return jsonb_build_object('allowed',true,'remaining',4-used);
end $$;
revoke all on function public.admit_trial_analysis(text,text) from public, anon, authenticated;
grant execute on function public.admit_trial_analysis(text,text) to service_role;


create table public.app_owners(user_id text primary key references gi_auth.users(id));
create table public.app_trial_settings(id boolean primary key default true check(id), trial_days integer not null check(trial_days between 1 and 90), analysis_limit integer not null check(analysis_limit between 1 and 100));
insert into public.app_trial_settings values(true,3,5);
create table public.app_account_access(user_id text primary key references gi_auth.users(id) on delete cascade, trial_expires_at timestamptz not null, analysis_limit integer not null check(analysis_limit between 1 and 10000), blocked boolean not null default false);
insert into public.app_account_access(user_id,trial_expires_at,analysis_limit) select id,created_at+interval '3 days',5 from gi_auth.users;
create table public.app_owner_audit(id bigint generated always as identity primary key, actor text not null, target text, action text not null, details jsonb not null, created_at timestamptz not null default now());
alter table public.app_owners enable row level security;
alter table public.app_trial_settings enable row level security;
alter table public.app_account_access enable row level security;
alter table public.app_owner_audit enable row level security;
revoke all on public.app_owners,public.app_trial_settings,public.app_account_access,public.app_owner_audit from public,anon,authenticated;

create function public.initialize_app_access() returns trigger language plpgsql security definer set search_path=public as $$
begin
 insert into public.app_account_access(user_id,trial_expires_at,analysis_limit)
 select new.id,new.created_at+make_interval(days=>trial_days),analysis_limit from public.app_trial_settings where id;
 return new;
end $$;
revoke all on function public.initialize_app_access() from public;
create trigger initialize_app_access after insert on gi_auth.users for each row execute function public.initialize_app_access();

create function public.my_app_access() returns jsonb language plpgsql security definer set search_path=public as $$
declare a public.app_account_access; n integer;
begin
 if gi_auth.uid() is null then raise exception 'Sign in required'; end if;
 select * into strict a from public.app_account_access where user_id=gi_auth.uid();
 select count(*) into n from public.trial_analysis_usage where user_id=gi_auth.uid();
 return jsonb_build_object('blocked',a.blocked,'trial_expires_at',a.trial_expires_at,'analysis_limit',a.analysis_limit,'used',n,
 'is_owner',exists(select 1 from public.app_owners where user_id=gi_auth.uid()));
end $$;
revoke all on function public.my_app_access() from public;
grant execute on function public.my_app_access() to authenticated;

create function public.public_trial_offer() returns jsonb language sql security definer set search_path=public as $$
 select jsonb_build_object('trial_days',trial_days,'analysis_limit',analysis_limit) from public.app_trial_settings where id;
$$;
revoke all on function public.public_trial_offer() from public;
grant execute on function public.public_trial_offer() to anon,authenticated;

create function public.owner_console(p_action text,p_payload jsonb default '{}') returns jsonb language plpgsql security definer set search_path=public as $$
declare actor text:=gi_auth.uid(); target text; before_row jsonb; after_row jsonb; d integer; n integer; users_json jsonb;
begin
 if actor is null or not exists(select 1 from public.app_owners where user_id=actor) then raise exception 'Owner access required' using errcode='42501'; end if;
 if p_action='defaults' then
  d:=(p_payload->>'trial_days')::integer; n:=(p_payload->>'analysis_limit')::integer;
  if d is null or n is null or d not between 1 and 90 or n not between 1 and 100 then raise exception 'Invalid defaults'; end if;
  select to_jsonb(s) into before_row from public.app_trial_settings s where id for update;
  update public.app_trial_settings set trial_days=d,analysis_limit=n where id;
  insert into public.app_owner_audit(actor,action,details) values(actor,p_action,jsonb_build_object('before',before_row,'after',p_payload));
 elsif p_action='access' then
  target:=(p_payload->>'user_id')::text;
  if exists(select 1 from public.app_owners where user_id=target) then raise exception 'Owner access cannot be edited here'; end if;
  d:=(p_payload->>'extra_days')::integer; n:=(p_payload->>'extra_analyses')::integer;
  if d is null or n is null or d not between 0 and 90 or n not between 0 and 100 or jsonb_typeof(p_payload->'blocked') is distinct from 'boolean' or length(trim(coalesce(p_payload->>'reason',''))) not between 1 and 500 then raise exception 'Invalid access change'; end if;
  select to_jsonb(a) into strict before_row from public.app_account_access a where user_id=target for update;
  update public.app_account_access set blocked=(p_payload->>'blocked')::boolean,
   trial_expires_at=case when d>0 then greatest(trial_expires_at,now())+make_interval(days=>d) else trial_expires_at end,
   analysis_limit=analysis_limit+n where user_id=target returning to_jsonb(app_account_access.*) into after_row;
  insert into public.app_owner_audit(actor,target,action,details) values(actor,target,p_action,jsonb_build_object('before',before_row,'after',after_row,'reason',p_payload->>'reason'));
 elsif p_action not in ('view','search') then raise exception 'Unknown action'; end if;
 select coalesce(jsonb_agg(x),'[]') into users_json from (
  select u.id,u.email,u.created_at,a.trial_expires_at,a.analysis_limit,a.blocked,
   (select count(*) from public.trial_analysis_usage t where t.user_id=u.id) as analyses_used
  from gi_auth.users u join public.app_account_access a on a.user_id=u.id
  where p_action<>'search' or lower(u.email)=lower(trim(p_payload->>'email')) order by u.created_at desc limit 200
 ) x;
 return jsonb_build_object('users',users_json,'total_users',(select count(*) from gi_auth.users),'settings',(select to_jsonb(s) from public.app_trial_settings s where id),
 'audit',(select coalesce(jsonb_agg(x),'[]') from (select h.actor,h.target,h.action,h.details,h.created_at from public.app_owner_audit h order by h.id desc limit 100) x));
end $$;
revoke all on function public.owner_console(text,jsonb) from public;
grant execute on function public.owner_console(text,jsonb) to authenticated;

create or replace function public.admit_trial_analysis(p_user_id text,p_analysis_key text) returns jsonb language plpgsql security definer set search_path=public as $$
declare a public.app_account_access; used integer;
begin
 select * into a from public.app_account_access where user_id=p_user_id for update;
 if not found or a.blocked or now()>=a.trial_expires_at then return jsonb_build_object('allowed',false,'reason','expired'); end if;
 select count(*) into used from public.trial_analysis_usage where user_id=p_user_id;
 if exists(select 1 from public.trial_analysis_usage where user_id=p_user_id and analysis_key=p_analysis_key) then return jsonb_build_object('allowed',true,'remaining',greatest(0,a.analysis_limit-used)); end if;
 if used>=a.analysis_limit then return jsonb_build_object('allowed',false,'reason','limit','remaining',0); end if;
 insert into public.trial_analysis_usage(user_id,analysis_key) values(p_user_id,p_analysis_key);
 return jsonb_build_object('allowed',true,'remaining',a.analysis_limit-used-1);
end $$;
revoke all on function public.admit_trial_analysis(text,text) from public,anon,authenticated;
grant execute on function public.admit_trial_analysis(text,text) to service_role;
-- Owner enrollment is a separate, reviewed database action after identity verification.


-- Never expose application tables to the unauthenticated role.
revoke all on all tables in schema public from anon;
grant usage on schema public to anon,authenticated;
commit;
