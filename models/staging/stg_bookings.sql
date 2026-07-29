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
)

select *
from cleaned 