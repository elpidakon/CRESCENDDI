-- Kontsioti, Maskell, Dutta & Pirmohamed, A reference set of clinically relevant adverse drug-drug interactions (2021)
set search_path = drug_interaction_compendia;
drop table if exists common_with_mapped_eventnames
;

create table common_with_mapped_eventnames as
select distinct
    a.ordered_drug_list
  , a.drug_1_concept_name
  , a.drug_2_concept_name
  , b.target_concept_id as bnf_event_concept_id
  , c.target_concept_id as micromedex_event_concept_id
  , a.bnf_description
  , a.micromedex_effect
from
    common a
    inner join
        bnf_event_usagi_mapping b
        on
            lower(a.bnf_description) = lower(b.source_code_description)
    inner join
        micromedex_event_usagi_mapping c
        on
            lower(a.micromedex_effect) = lower(c.source_code_description)
;

-- Note: Some text descriptions from the bnf_event_usagi_mapping and  
-- micromedex_event_usagi_mapping tables are mapped to multiple OHDSI concepts;
-- this is the reason why the common_with_mapped_drugnames table has more rows compared to the original.