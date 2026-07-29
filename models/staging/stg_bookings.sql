with source as (
    select * 
    from {{ ref('raw_bookings') }}
),
cleaned as (
    select
        trim("BookingID") as booking_id,
        coalesce(
            try_to_date(trim("Booking Date"), 'MM/DD/YYYY'),
            try_to_date(trim("Booking Date"), 'YYYY-MM-DD'),
            try_to_date(trim("Booking Date"))
        ) as booking_date,
        trim("Customer") as customer,
        initcap(trim("Region")) as region,
        trim("Product") as product,
        trim("Deal Type") as deal_type,
        trim("Sales Rep") as sales_rep,
        cast("Amount (Local)" as number(18, 2)) as amount_local,
        upper(trim("Currency")) as currency 
    from source 
),
with_rep_id as (
    select 
        c.*,
        r.rep_id
    from cleaned c 
    left join {{ ref('stg_rep_master') }} r 
    on c.sales_rep = r.alias_name 
),
deduped as (
    select 
        *,
        row_number() over (
            partition by booking_id
            order by booking_date desc 
        ) as row_number 
    from with_rep_id 
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
    currency
from deduped 
where row_number = 1