from datetime import datetime
import decimal

def validate_trip(row, validate_cities):
    required_fields =['trip_id', 'driver_id', 'city', 'requested_at', 'updated_at', 'status']

    if row['status'] != 'cancelled':
        required_fields.extend(['completed_at', 'distance_km', 'fare_pln'])

    for field in required_fields:
        if row[field] == '':
            return f"Missing field: {field}"

    if row['status'] not in ['completed', 'cancelled', 'refunded']:
        return f"Invalid status: {row['status']}"

    if row['city'] not in validate_cities:
        return f"Invalid city: {row['city']}"

    for field in ('requested_at', 'updated_at', 'completed_at'):
        value = row[field]
        if value != '':
            try:
                datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z")
            except ValueError:
                return f"Invalid datetime format for {field}: {value}"

    for field in ('fare_pln', 'distance_km'):
        value = row[field]
        if value == '':
            continue
        try:
            decimal_value = decimal.Decimal(value)
            if not decimal_value.is_finite():
                return f"Nonfinite {field}: {value}"
            if decimal_value < 0:
                return f"Negative {field}: {value}"
        except decimal.InvalidOperation:
                return f"Invalid decimal format for {field}: {value}"
    return None





    


    

    






