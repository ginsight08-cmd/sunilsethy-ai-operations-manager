begin;
create table public.app_owners(user_id uuid primary key references auth.users(id));
create table public.app_trial_settings(id boolean primary key default true check(id), trial_days integer not null check(trial_days between 1 and 90), analysis_limit integer not null check(analysis_limit between 1 and 100));
insert into public.app_trial_settings values(true,3,5);
create table public.app_account_access(user_id uuid primary key references auth.users(id) on delete cascade, trial_expires_at timestamptz not null, analysis_limit integer not null check(analysis_limit between 1 and 10000), blocked boolean not null default false);
insert into public.app_account_access(user_id,trial_expires_at,analysis_limit) select id,created_at+interval '3 days',5 from auth.users;
create table public.app_owner_audit(id bigint generated always as identity primary key, actor uuid not null, target uuid, action text not null, details jsonb not null, created_at timestamptz not null default now());
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
create trigger initialize_app_access after insert on auth.users for each row execute function public.initialize_app_access();

create function public.my_app_access() returns jsonb language plpgsql security definer set search_path=public as $$
declare a public.app_account_access; n integer;
begin
 if auth.uid() is null then raise exception 'Sign in required'; end if;
 select * into strict a from public.app_account_access where user_id=auth.uid();
 select count(*) into n from public.trial_analysis_usage where user_id=auth.uid();
 return jsonb_build_object('blocked',a.blocked,'trial_expires_at',a.trial_expires_at,'analysis_limit',a.analysis_limit,'used',n,
 'is_owner',exists(select 1 from public.app_owners where user_id=auth.uid()));
end $$;
revoke all on function public.my_app_access() from public;
grant execute on function public.my_app_access() to authenticated;

create function public.public_trial_offer() returns jsonb language sql security definer set search_path=public as $$
 select jsonb_build_object('trial_days',trial_days,'analysis_limit',analysis_limit) from public.app_trial_settings where id;
$$;
revoke all on function public.public_trial_offer() from public;
grant execute on function public.public_trial_offer() to anon,authenticated;

create function public.owner_console(p_action text,p_payload jsonb default '{}') returns jsonb language plpgsql security definer set search_path=public as $$
declare actor uuid:=auth.uid(); target uuid; before_row jsonb; after_row jsonb; d integer; n integer; users_json jsonb;
begin
 if actor is null or not exists(select 1 from public.app_owners where user_id=actor) then raise exception 'Owner access required' using errcode='42501'; end if;
 if p_action='defaults' then
  d:=(p_payload->>'trial_days')::integer; n:=(p_payload->>'analysis_limit')::integer;
  if d is null or n is null or d not between 1 and 90 or n not between 1 and 100 then raise exception 'Invalid defaults'; end if;
  select to_jsonb(s) into before_row from public.app_trial_settings s where id for update;
  update public.app_trial_settings set trial_days=d,analysis_limit=n where id;
  insert into public.app_owner_audit(actor,action,details) values(actor,p_action,jsonb_build_object('before',before_row,'after',p_payload));
 elsif p_action='access' then
  target:=(p_payload->>'user_id')::uuid;
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
  from auth.users u join public.app_account_access a on a.user_id=u.id
  where p_action<>'search' or lower(u.email)=lower(trim(p_payload->>'email')) order by u.created_at desc limit 200
 ) x;
 return jsonb_build_object('users',users_json,'total_users',(select count(*) from auth.users),'settings',(select to_jsonb(s) from public.app_trial_settings s where id),
 'audit',(select coalesce(jsonb_agg(x),'[]') from (select h.actor,h.target,h.action,h.details,h.created_at from public.app_owner_audit h order by h.id desc limit 100) x));
end $$;
revoke all on function public.owner_console(text,jsonb) from public;
grant execute on function public.owner_console(text,jsonb) to authenticated;

create or replace function public.admit_trial_analysis(p_user_id uuid,p_analysis_key text) returns jsonb language plpgsql security definer set search_path=public as $$
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
revoke all on function public.admit_trial_analysis(uuid,text) from public,anon,authenticated;
grant execute on function public.admit_trial_analysis(uuid,text) to service_role;
-- Owner enrollment is a separate, reviewed database action after identity verification.
commit;
