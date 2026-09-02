-- Run once in Supabase Dashboard > SQL Editor.
create extension if not exists pgcrypto;

create table if not exists public.vakil_clients (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
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
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  client_id uuid not null references public.vakil_clients(id) on delete restrict,
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
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  case_id uuid not null references public.vakil_cases(id) on delete cascade,
  client_id uuid references public.vakil_clients(id) on delete set null,
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
for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "Users manage own vakil cases" on public.vakil_cases;
create policy "Users manage own vakil cases" on public.vakil_cases
for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "Users manage own vakil notifications" on public.vakil_notification_log;
create policy "Users manage own vakil notifications" on public.vakil_notification_log
for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

grant select, insert, update, delete on public.vakil_clients to authenticated;
grant select, insert, update, delete on public.vakil_cases to authenticated;
grant select, insert, update, delete on public.vakil_notification_log to authenticated;
