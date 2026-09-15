-- Additive migration: run in Supabase SQL Editor. Existing industry tables are unchanged.
begin;
create table if not exists public.work_hub_records (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  industry text not null check (industry in ('BPO','Manufacturing','CaseManagement','Retail','Logistics','Healthcare')),
  kind text not null check (kind in ('client','work','task','document','draft','time')),
  title text not null check (length(trim(title)) between 1 and 300),
  status text not null,
  parent_id uuid,
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
  user_id uuid not null references auth.users(id) on delete cascade,
  industry text not null,
  record_id uuid not null references public.work_hub_records(id),
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
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists work_hub_audit_read on public.work_hub_events;
create policy work_hub_audit_read on public.work_hub_events for select to authenticated using (auth.uid() = user_id);
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
commit;
