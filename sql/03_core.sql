create table if not exists core.cities (
    city text primary key,
    voivodeship text not null
);

create table if not exists core.drivers (
    driver_id text primary key,
    name text not null,
    home_city text not null,
    commission_rate numeric (2,2) not null,
    joined_at date not null
);

