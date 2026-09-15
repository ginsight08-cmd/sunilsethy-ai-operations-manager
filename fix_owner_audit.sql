-- Apply separately from rolled-back tests so the repair stays committed.
begin;
do $fix$
declare definition text;
begin
  select pg_get_functiondef('public.owner_console(text,jsonb)'::regprocedure) into definition;
  definition := replace(definition,
    'select actor,target,action,details,created_at from public.app_owner_audit order by id desc limit 100',
    'select h.actor,h.target,h.action,h.details,h.created_at from public.app_owner_audit h order by h.id desc limit 100');
  execute definition;
end $fix$;
commit;
