-- Supabase / Postgres schema for the lead generator.
-- Run once in the Supabase SQL editor (or psql) before the first pipeline run.

create table if not exists leads (
    place_id          text primary key,
    name              text not null default '',
    category          text not null default '',
    address           text not null default '',
    area              text not null default '',
    phone             text not null default '',
    website           text not null default '',
    google_maps_url   text not null default '',
    rating            double precision,
    reviews_count     integer,

    -- best-effort enrichment
    email             text not null default '',
    owner_name        text not null default '',
    source_of_contact text not null default '',

    -- AI enrichment
    lead_score        integer,
    score_reason      text not null default '',
    outreach_draft    text not null default '',

    -- lifecycle
    status            text not null default 'new',
    first_seen        timestamptz not null default now(),
    last_seen         timestamptz not null default now()
);

create index if not exists leads_area_idx     on leads (area);
create index if not exists leads_category_idx on leads (category);
create index if not exists leads_score_idx    on leads (lead_score desc);
create index if not exists leads_status_idx   on leads (status);
