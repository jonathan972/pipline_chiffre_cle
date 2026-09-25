CREATE TABLE IF NOT EXISTS fact_population_officielle (
    annee_population smallint NOT NULL,
    niveau_geo text NOT NULL,
    code_geo text NOT NULL,
    territoire text NOT NULL,
    population_municipale integer NOT NULL,
    date_publication date,
    date_entree_vigueur date,
    source_url text,
    source_type text NOT NULL,
    PRIMARY KEY (annee_population, niveau_geo, code_geo)
);

CREATE TABLE IF NOT EXISTS fact_population_resolue (
    annee_indicateur smallint NOT NULL,
    niveau_geo text NOT NULL,
    code_geo text NOT NULL,
    territoire text NOT NULL,
    population_utilisee integer,
    millesime_population smallint,
    statut_resolution text NOT NULL,
    source_url text,
    PRIMARY KEY (annee_indicateur, niveau_geo, code_geo)
);
