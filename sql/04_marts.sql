create or replace view mart.daily_city_revenue as
select
	(t.completed_at at time zone 'Europe/Warsaw')::date as business_date,
	t.city,
	count(*) as completed_trips,
	sum(t.fare_pln) as revenue_pln
	from core.trips t
where t.status = 'completed' group by business_date, t.city;

create or replace view mart.driver_payouts as
select
	(t.completed_at at time zone 'Europe/Warsaw')::date as business_date,
	t.driver_id,
	count(t.completed_at) as completed_trips,
	sum(t.fare_pln) as gross_pln,
	sum(round(
	t.fare_pln * (1-coalesce(d.commission_rate, 0.25)),
	2
	)) as payout_pln
from core.trips t left join core.drivers d on t.driver_id = d.driver_id
where t.status = 'completed'
group by business_date, t.driver_id;