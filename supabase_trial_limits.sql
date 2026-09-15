-- Server-only admission; no client may reset or forge usage.
begin;
create table if not exists public.trial_analysis_usage (
  user_id uuid not null references auth.users(id) on delete cascade,
  analysis_key text not null check (analysis_key ~ '^[a-f0-9]{64}$'),
  created_at timestamptz not null default now(),
  primary key(user_id, analysis_key)
);
alter table public.trial_analysis_usage enable row level security;
revoke all on public.trial_analysis_usage from public, anon, authenticated;
create or replace function public.admit_trial_analysis(p_user_id uuid, p_analysis_key text)
returns jsonb language plpgsql security definer set search_path = public as $$
declare joined timestamptz; used integer;
begin
  -- The user-row lock serializes admissions across devices and app sessions.
  select created_at into joined from auth.users where id=p_user_id for update;
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
revoke all on function public.admit_trial_analysis(uuid,text) from public, anon, authenticated;
grant execute on function public.admit_trial_analysis(uuid,text) to service_role;
commit;
