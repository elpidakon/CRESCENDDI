-- Kontsioti, Maskell, Dutta & Pirmohamed, A reference set of clinically relevant adverse drug-drug interactions (2021)
set search_path = drug_interaction_compendia;
drop table if exists thesaurus_with_mapped_drugnames
;

create table thesaurus_with_mapped_drugnames as
select
    a.drugname_1_original
  , a.drugname_2_original
  , b.target_concept_id as drugname_1_concept_id
  , c.target_concept_id as drugname_2_concept_id
  , a.severity
from
    thesaurus_data a
    inner join
        thesaurus_drug_usagi_mapping b
        on
            lower(a.drugname_1_original) = lower(b.source_code_description)
    inner join
        thesaurus_drug_usagi_mapping c
        on
            lower(a.drugname_2_original) = lower(c.source_code_description)
;

-- Note: Some names from the thesaurus_drug_usagi_mapping table are 
-- mapped to multiple OHDSI concepts;
-- this is the reason why the thesaurus_with_mapped_drugnames table 
-- has more rows compared to the original.
alter table thesaurus_with_mapped_drugnames add column flag integer
  , add column ordered_drug_list                            varchar
;

update
    thesaurus_with_mapped_drugnames
set flag = 1
where
    drugname_1_concept_id < drugname_2_concept_id
;

update
    thesaurus_with_mapped_drugnames
set flag = 2
where
    drugname_1_concept_id > drugname_2_concept_id
;

update
    thesaurus_with_mapped_drugnames
set ordered_drug_list = concat(drugname_1_concept_id, '|', drugname_2_concept_id)
where
    drugname_1_concept_id      < drugname_2_concept_id
    and drugname_1_concept_id != 0
    and drugname_2_concept_id != 0
;

update
    thesaurus_with_mapped_drugnames
set ordered_drug_list = concat(drugname_2_concept_id, '|', drugname_1_concept_id)
where
    drugname_1_concept_id      > drugname_2_concept_id
    and drugname_1_concept_id != 0
    and drugname_2_concept_id != 0
;