import pandas as pd
from ridehail import db

city_revenue_report_query = """
    select
	    dcr.business_date,
	    dcr.city,
	    dcr.completed_trips,
	    dcr.revenue_pln
    from mart.daily_city_revenue dcr
    order by business_date, city
"""

driver_payouts_report_query = """
    select
	    dp.business_date,
	    dp.driver_id,
	    dp.completed_trips,
	    dp.gross_pln,
	    dp.payout_pln
    from mart.driver_payouts dp 
    order by business_date, driver_id
"""

driver_leaderboard_report_query = """
    select
	    dl.business_date,
	    dl.city,
	    dl.driver_id,
	    dl.payout_pln,
	    dl.rank_in_city
    from mart.driver_leaderboard dl 
    order by business_date, city, rank_in_city, driver_id
"""

def write_reports(reports_dir) -> None:
    city_rows = db.fetch_all(city_revenue_report_query)
    driver_rows = db.fetch_all(driver_payouts_report_query)
    leaderboard_rows = db.fetch_all(driver_leaderboard_report_query)
    df_city_revenue = pd.DataFrame(city_rows, columns=["business_date", "city", "completed_trips", "revenue_pln"])
    df_driver_payouts = pd.DataFrame(driver_rows, columns=["business_date", "driver_id", "completed_trips", "gross_pln", "payout_pln"])
    df_driver_leaderboard = pd.DataFrame(leaderboard_rows, columns=["business_date", "city", "driver_id", "payout_pln", "rank_in_city"])
    df_city_revenue.to_csv(reports_dir / "daily_city_revenue.csv", index=False)
    df_driver_payouts.to_csv(reports_dir / "driver_payouts.csv", index=False)
    df_driver_leaderboard.to_csv(reports_dir / "driver_leaderboard.csv", index=False)


