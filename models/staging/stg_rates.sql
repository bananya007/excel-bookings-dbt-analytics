with source as (
    select *
    from {{ ref('raw_rates') }}
),
cleaned as (
    select
        upper(trim("Currency")) as currency,
        cast("Rate to USD" as number(18, 6)) as rate_to_usd,
        try_to_date("Effective Date") as effective_date,
        trim("Source") as rate_source
    from source 
)
select *
from cleaned