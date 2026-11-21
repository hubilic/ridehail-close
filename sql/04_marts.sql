create or replace view mart.daily_city_revenue as
select
	(t.completed_at at time zone 'Europe/Warsaw')::date as business_date,
	t.city,
	count(*) as completed_trips,
	sum(t.fare_pln) as revenue_pln
	from core.trips t
where t.status = 'completed' group by business_date, t.city;