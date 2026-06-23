
create table if not exists public.employees (
    id bigint generated always as identity primary key,
    emp_id text not null unique,
    employee_name text not null,
    email_id text not null unique,
    password_hash text not null,
    is_admin boolean not null default false,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.shared_files (
    id bigint generated always as identity primary key,
    sender_emp_id text not null references public.employees(emp_id) on delete restrict,
    sender_name text not null,
    original_filename text not null,
    storage_path text not null unique,
    file_size_bytes bigint not null default 0,
    mime_type text,
    file_hash text,
    note text,
    created_at timestamptz not null default now()
);

create table if not exists public.file_recipients (
    id bigint generated always as identity primary key,
    file_id bigint not null references public.shared_files(id) on delete cascade,
    recipient_emp_id text not null references public.employees(emp_id) on delete cascade,
    recipient_deleted boolean not null default false,
    downloaded_at timestamptz,
    created_at timestamptz not null default now(),
    unique(file_id, recipient_emp_id)
);

create table if not exists public.file_activity_log (
    id bigint generated always as identity primary key,
    emp_id text,
    action_type text not null,
    details text,
    created_at timestamptz not null default now()
);

create or replace function public.get_inbox_for_emp(p_emp_id text)
returns table (
    file_recipient_id bigint,
    file_id bigint,
    sender_emp_id text,
    sender_name text,
    original_filename text,
    storage_path text,
    file_size_bytes bigint,
    mime_type text,
    note text,
    created_at timestamptz
)
language sql
security definer
as $$
    select
        fr.id as file_recipient_id,
        sf.id as file_id,
        sf.sender_emp_id,
        sf.sender_name,
        sf.original_filename,
        sf.storage_path,
        sf.file_size_bytes,
        sf.mime_type,
        sf.note,
        sf.created_at
    from public.file_recipients fr
    join public.shared_files sf on sf.id = fr.file_id
    where fr.recipient_emp_id = p_emp_id
      and fr.recipient_deleted = false
    order by sf.created_at desc;
$$;
