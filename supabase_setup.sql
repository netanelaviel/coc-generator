-- Run this in the Supabase SQL Editor

-- 1. Products table
create table if not exists coc_products (
  id          bigserial primary key,
  sku         text unique not null,
  model       text not null,
  description text,
  created_at  timestamptz default now()
);

-- 2. Users table
create table if not exists coc_users (
  id            bigserial primary key,
  username      text unique not null,
  password_hash text not null,
  role          text not null default 'agent',  -- 'agent' or 'admin'
  created_at    timestamptz default now()
);

-- 3. Logs table
create table if not exists coc_logs (
  id         bigserial primary key,
  username   text not null,
  sku        text not null,
  model      text not null,
  created_at timestamptz default now()
);

-- 4. Disable Row Level Security (app uses service key)
alter table coc_products disable row level security;
alter table coc_users    disable row level security;
alter table coc_logs     disable row level security;
