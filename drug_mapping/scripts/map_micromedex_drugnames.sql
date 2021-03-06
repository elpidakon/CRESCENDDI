-- Kontsioti, Maskell, Dutta & Pirmohamed, A reference set of clinically relevant adverse drug-drug interactions (2021)
set search_path = drug_interaction_compendia;
drop table if exists micromedex_with_mapped_drugnames
;

create table micromedex_with_mapped_drugnames as
select
    a.drugname_1_original
  , a.drugname_2_original
  , b.target_concept_id as drugname_1_concept_id
  , c.target_concept_id as drugname_2_concept_id
  , d.concept_name      as drugname_1_concept_name
  , e.concept_name      as drugname_2_concept_name
  , a.description
  , a.severity
  , a.evidence
from
    micromedex_data a
    inner join
        micromedex_drug_usagi_mapping b
        on
            lower(a.drugname_1_original) = lower(b.source_code_description)
    inner join
        micromedex_drug_usagi_mapping c
        on
            lower(a.drugname_2_original) = lower(c.source_code_description)
    inner join
        cdmv5.concept d
        on
            b.target_concept_id = d.concept_id
    inner join
        cdmv5.concept e
        on
            c.target_concept_id = e.concept_id
;

alter table micromedex_with_mapped_drugnames add column flag integer
  , add column ordered_drug_list                             varchar
  , add column description_blinded                           text
;

update
    micromedex_with_mapped_drugnames
set flag = 1
where
    drugname_1_concept_id < drugname_2_concept_id
;

update
    micromedex_with_mapped_drugnames
set flag = 2
where
    drugname_1_concept_id > drugname_2_concept_id
;

update
    micromedex_with_mapped_drugnames
set ordered_drug_list = concat(drugname_1_concept_id, '|', drugname_2_concept_id)
where
    drugname_1_concept_id      < drugname_2_concept_id
    and drugname_1_concept_id != 0
    and drugname_2_concept_id != 0
;

update
    micromedex_with_mapped_drugnames
set ordered_drug_list = concat(drugname_2_concept_id, '|', drugname_1_concept_id)
where
    drugname_1_concept_id      > drugname_2_concept_id
    and drugname_1_concept_id != 0
    and drugname_2_concept_id != 0
;

-- First attempt for drug name blinding in description; note that some drug names 
-- have not been successfully blinded because the original name
-- was for example the salt form of the drug and the description contained the ingredient name. 
-- That is why a second attempt for blinding will follow.
update
    micromedex_with_mapped_drugnames
set description_blinded = replace(replace(lower(description), lower(drugname_1_original), 'X'), lower(drugname_2_original), 'X')
;