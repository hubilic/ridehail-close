import pandas as pd
from ridehail import db
from ridehail.validate import validate_trip
from pathlib import Path
import hashlib

cities_insert_query = """ 
    INSERT INTO core.cities (city, voivodeship) VALUES (%s, %s)
    on conflict (city) do update set voivodeship = excluded.voivodeship where cities.voivodeship != excluded.voivodeship
"""

drivers_insert_query = """
        INSERT INTO core.drivers (driver_id,name,home_city,commission_rate,joined_at) VALUES (%s, %s, %s, %s, %s)
        on conflict (driver_id) do update
        set name = excluded.name, 
        home_city = excluded.home_city,
        commission_rate = excluded.commission_rate,
        joined_at = excluded.joined_at
        where drivers.name != excluded.name
        or drivers.home_city != excluded.home_city  
        or drivers.commission_rate != excluded.commission_rate
        or drivers.joined_at != excluded.joined_at"""

rejected_insert_query = """
        INSERT INTO raw.rejected (source_file, line_no, reason, raw_row, file_sha256) VALUES (%s, %s, %s, %s, %s)
        """
trips_insert_query = """
        INSERT INTO raw.trips (source_file, line_no, trip_id, driver_id, city, requested_at, completed_at, updated_at, distance_km, fare_pln, status, file_sha256) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

loaded_files_insert_query = """
        INSERT INTO raw.loaded_files (file_name, sha256) VALUES (%s, %s)
        """

loaded_file_select_query = """
        SELECT sha256 from raw.loaded_files where sha256 = %s
"""


def insert_cities(path = "ridehail-close/data/reference/cities.csv") -> None:
        csv_cities = pd.read_csv(path, sep=",")
        city_rows = list(csv_cities.itertuples(index=False, name=None))
        db.run_in_transaction([db.many(cities_insert_query, city_rows)])
        return set(csv_cities["city"])


def insert_drivers(path = "ridehail-close/data/reference/drivers.csv") -> None:
        csv_drivers = pd.read_csv(path, sep= ",")
        drivers_rows = list(csv_drivers.itertuples(index=False, name=None))
        db.run_in_transaction([db.many(drivers_insert_query, drivers_rows)])


def load_trip_file(path, validate_cities) -> None:
        file_bytes = Path(path).read_bytes()
        file_sha256 = hashlib.sha256(file_bytes).hexdigest()
        source_file = Path(path).name
        loaded_file = db.fetch_one(loaded_file_select_query, (file_sha256,))
        if loaded_file is not None:
              print (f"{source_file} skipped (already loaded)")
              return              
        csv_trips = pd.read_csv(path, sep= ",", dtype=str, keep_default_na=False)
        rows = csv_trips.to_dict(orient='records')
        rejected_rows = []
        accepted_rows = []
        
        for line_no, row in enumerate(rows, start=2):
            reason = validate_trip(row, validate_cities)
            if reason:
                raw_row = str(row)
                rejected_rows.append((source_file, line_no, reason, raw_row, file_sha256))
            else:
                  accepted_rows.append((source_file, line_no, row['trip_id'], row['driver_id'], row['city'], row['requested_at'], row['completed_at'] or None, row['updated_at'], row['distance_km'] or None, row['fare_pln'] or None, row['status'], file_sha256))

        db.run_in_transaction([
                db.many(trips_insert_query, accepted_rows),
                db.many(rejected_insert_query, rejected_rows),
                db.once(loaded_files_insert_query, (source_file, file_sha256)),
        ])

        print(f"{source_file} lines={len(rows)} loaded={len(accepted_rows)} rejected={len(rejected_rows)}")
