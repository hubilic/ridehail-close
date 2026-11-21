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

create table if not exists core.trips (
    trip_id text primary key,
    driver_id text not null,
    city text not null,
    requested_at timestamptz not null,
    completed_at timestamptz,
    updated_at timestamptz not null,
    distance_km decimal,
    fare_pln numeric (10,2),
    status text not null
);

