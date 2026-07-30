with source as (
    select *
    from {{ ref('rep_master') }}
),
cleaned as (
    select 
        initcap(trim("Alias Name")) as alias_name,
        initcap(trim("Canonical Name")) as canonical_name,
        upper(trim("Rep ID")) as rep_id,
        initcap(trim("Region")) as region
    from source 
)
select * 
from cleaned