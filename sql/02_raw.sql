create table if not exists raw.loaded_files (
	file_name text not null,
	sha256 text primary key,
	loaded_at timestamptz not null default now()
);

create table if not exists raw.trips (
    source_file text not null,
    line_no int not null,
    trip_id text not null,
    driver_id text not null,
    city text not null,
    requested_at timestamptz not null,
    completed_at timestamptz,
    updated_at timestamptz not null,
    distance_km decimal,
    fare_pln numeric (10,2),
    status text not null,
    check (status in ('cancelled') or (completed_at is not null and distance_km is not null and fare_pln is not null)),
    check (distance_km >= 0 and fare_pln >= 0),
    file_sha256 text not null,
    primary key (file_sha256, line_no)
);

create table if not exists raw.rejected (
    source_file text not null,
    line_no int not null,
    reason text not null,
    raw_row text not null,
    file_sha256 text not null,
    primary key (file_sha256, line_no)
);