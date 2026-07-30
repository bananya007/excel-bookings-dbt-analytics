with source as (
    select *
    from {{ ref('raw_rep_targets')}}
),
cleaned as (
    select 
        trim("Rep ID") as rep_id,
        trim("Sales Rep") as sales_rep,
        cast("Target Year" as integer) as target_year,
        cast("Annual Quota (USD)" as number(18, 2)) as annual_quota_usd
    from source 
)
select * 
from cleaned