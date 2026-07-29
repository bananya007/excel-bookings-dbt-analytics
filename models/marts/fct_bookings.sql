with bookings as (
    select * 
    from {{ ref('stg_bookings') }}
),
rates as (
    select *
    from {{ ref('stg_rates') }}
),
matched_rates as (
    select 
        b.*,
        r.rate_to_usd,
        r.effective_date as rate_effective_date,
        r.rate_source,
        row_number() over (
            partition by b.booking_id
            order by r.effective_date desc nulls last 
        ) as rate_rank 
    from bookings b 
    left join rates r 
        on b.currency = r.currency 
        and r.effective_date <= b.booking_date 
)
select 
    booking_id,
    booking_date,
    customer,
    region,
    product,
    deal_type,
    sales_rep,
    rep_id,
    amount_local,
    currency,
    rate_to_usd,
    rate_effective_date,
    rate_source,
    cast(amount_local * rate_to_usd as number(18, 2)) as amount_usd,
    case 
        when rate_to_usd is null then 'MISSING_RATE'
        else 'CONVERTED' 
    end as conversion_status 
from matched_rates
where rate_rank = 1