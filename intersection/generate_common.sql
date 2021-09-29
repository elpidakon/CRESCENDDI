-- Kontsioti, Maskell, Dutta & Pirmohamed, A reference set of clinically relevant adverse drug-drug interactions (2021)
-- Generate a table that contains the DDIs from the intersection of the three data sources and the associated English descriptions.
set search_path = drug_interaction_compendia;
drop table if exists bnf_micromedex_intersection
;

create table bnf_micromedex_intersection as
select
    bnf.*
from
    bnf_drug_pairs bnf
    join
        micromedex_drug_pairs mi
        on
            bnf.ordered_drug_list = mi.ordered_drug_list
;

drop table if exists bnf_micromedex_thesaurus_intersection
;

create table bnf_micromedex_thesaurus_intersection as
select
    bnf_mi.*
from
    bnf_micromedex_intersection bnf_mi
    join
        thesaurus_drug_pairs thes
        on
            bnf_mi.ordered_drug_list = thes.ordered_drug_list
;

--- Table for intersection among the three data tables (BNF, Thesaurus and Micromedex) ------------
drop table if exists common
;

create table common as
select distinct
    i.*
  ,
     --lower(bnf.drugname_1_original) as bnf_drugname_original_first, lower(bnf.drugname_2_original) as bnf_drugname_original_second,
     bnf.description_blinded as bnf_description
  , mi.description_blinded   as micromedex_description
  , bnf.severity             as bnf_severity
  , thes.severity            as ansm_severity
  , mi.severity              as micromedex_severity
  , bnf.evidence             as bnf_evidence
  , mi.evidence              as micromedex_evidence
  , lower(c1.concept_name)   as drug_1_concept_name
  , lower(c2.concept_name)   as drug_2_concept_name
from
    bnf_micromedex_thesaurus_intersection i
    join
        bnf_with_mapped_drugnames bnf
        on
            i.ordered_drug_list = bnf.ordered_drug_list
    join
        micromedex_with_mapped_drugnames mi
        on
            i.ordered_drug_list = mi.ordered_drug_list
    join
        thesaurus_with_mapped_drugnames thes
        on
            i.ordered_drug_list = thes.ordered_drug_list
    join
        cdmv5.concept c1
        on
            drug_1_concept_id = c1.concept_id
    join
        cdmv5.concept c2
        on
            drug_2_concept_id = c2.concept_id
;

update
    common
set bnf_description        = trim(bnf_description)
  , micromedex_description = trim(micromedex_description)
;

-- Second effort for drug name blinding for salt forms etc that appeared in the description as ingredients (i.e. the drug names didn't match the names
-- that appeared in the description).
update
    common
set bnf_description        = replace(replace(bnf_description, lower(drug_1_concept_name), 'X'), lower(drug_2_concept_name), 'X')
  , micromedex_description = replace(replace(micromedex_description, lower(drug_1_concept_name), 'X'), lower(drug_2_concept_name), 'X')
;

-- Remove duplicate rows that arose from incomplete drug name blinding (so now they can be removed successfully)
delete
from
    common
where
    ctid not in
    (
        select
            min(ctid)
        from
            common
        group by
            ordered_drug_list
          , bnf_description
          , micromedex_description
    )
;

--The output of this command can be exported in ordered to be used for mapping interaction effect descriptions to MedDRA concepts
-- REPLACE 'specify_path' WITH THE DIRECTORY NAME YOU WANT TO EXPORT THE CSV FILE (you need to give WRITE permissions to this directory)
-- BNF description
COPY
(
    select distinct
        bnf_description
    from
        common
    group by
        bnf_description
)
to 'specify_path/common_bnf_descriptions_blinded.csv' csv header;
-- Micromedex descriptions
COPY
(
    select distinct
        micromedex_description
    from
        common
    group by
        micromedex_description
)
to 'specify_path/common_micromedex_descriptions_blinded.csv' csv header;