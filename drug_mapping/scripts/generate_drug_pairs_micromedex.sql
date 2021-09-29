-- Kontsioti, Maskell, Dutta & Pirmohamed, A reference set of clinically relevant adverse drug-drug interactions (2021)
set search_path = drug_interaction_compendia;
drop table if exists micromedex_drug_pairs
;

create table micromedex_drug_pairs as
select distinct
    ordered_drug_list
from
    micromedex_with_mapped_drugnames
;

alter table micromedex_drug_pairs add column drug_1_concept_id integer
  , add column drug_2_concept_id                               integer
;

update
    micromedex_drug_pairs
set drug_1_concept_id = split_part(ordered_drug_list, '|', 1)::int
  , drug_2_concept_id = split_part(ordered_drug_list, '|', 2)::int
;