with bookings as (
    select * 
    from {{ ref('fct_bookings') }}
),
categorized as (
    select 
        *,
        case 
            when upper(deal_type) in ('NEW','NEW BUSINESS') then 'NEW'
            when upper(deal_type) in ('RENEWAL', 'RECURRING') then 'RECURRING'
            else 'OTHER'
        end as deal_category 
    from bookings 
),
regional as (
    select 
        region,
        cast(sum(case 
            when deal_category = 'NEW' then coalesce(amount_usd, 0)
            else 0
        end) as number(18, 2)) as new_bookings_usd,
        cast(sum(case 
            when deal_category = 'RECURRING' then coalesce(amount_usd, 0)
            else 0
        end) as number(18, 2)) as recurring_bookings_usd,
        cast(sum(case
            when deal_category = 'OTHER' then coalesce(amount_usd, 0)
            else 0
        end) as number(18, 2)) as other_bookings_usd,
        cast(coalesce(sum(amount_usd), 0) as number(18, 2)) as total_bookings_usd,
        count(*) as booking_count,
        sum(case
            when conversion_status = 'MISSING_RATE' then 1
            else 0
        end) as missing_rate_booking_count 
    from categorized
    group by region
),
grand_total as (
    select 
        sum(total_bookings_usd) as grand_total_usd 
    from regional 
)
select 
    r.region,
    r.new_bookings_usd,
    r.recurring_bookings_usd,
    r.other_bookings_usd,
    r.total_bookings_usd,
    r.booking_count,
    r.missing_rate_booking_count,
    case 
        when g.grand_total_usd = 0 then 0
        else r.total_bookings_usd / g.grand_total_usd 
    end as pct_of_grand_total
from regional r 
cross join grand_total g
