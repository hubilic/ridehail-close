import pandas as pd
from ridehail import db

cities_insert_query = (
    "INSERT INTO core.cities (city, voivodeship) VALUES (%s, %s)"
    " on conflict (city) do update set voivodeship = excluded.voivodeship where cities.voivodeship != excluded.voivodeship;"
)

def insert_cities(path = "ridehail-close/data/reference/cities.csv") -> None:
        csv_cities = pd.read_csv(path, sep=",")
        city_rows = list(csv_cities.itertuples(index=False, name=None))
        db.run_in_transaction([db.many(cities_insert_query, city_rows)])
