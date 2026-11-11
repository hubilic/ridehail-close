import pandas as pd
from ridehail import db

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

def insert_cities(path = "ridehail-close/data/reference/cities.csv") -> None:
        csv_cities = pd.read_csv(path, sep=",")
        city_rows = list(csv_cities.itertuples(index=False, name=None))
        db.run_in_transaction([db.many(cities_insert_query, city_rows)])


def insert_drivers(path = "ridehail-close/data/reference/drivers.csv") -> None:
        csv_drivers = pd.read_csv(path, sep= ",")
        drivers_rows = list(csv_drivers.itertuples(index=False, name=None))
        db.run_in_transaction([db.many(drivers_insert_query, drivers_rows)])