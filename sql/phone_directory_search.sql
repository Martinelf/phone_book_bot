DROP VIEW IF EXISTS bot_test.phone_directory_search;

CREATE VIEW bot_test.phone_directory_search AS
SELECT
    c.id AS id_phone_directory,
    split_part(TRIM(BOTH FROM c.full_name), ' ', 1) AS last_name,
    split_part(TRIM(BOTH FROM c.full_name), ' ', 2) AS first_name,
    NULLIF(split_part(TRIM(BOTH FROM c.full_name), ' ', 3), '') AS patronymic,
    NULLIF(c.work_phone, '') AS phone,
    NULLIF(c.ext_phone, '') AS phone_ext,
    NULLIF(c.mobile_phone, '') AS mobile_phone,
    NULL::text AS email,
    NULL::integer AS department_id,
    c.department AS department_name,
    c."position" AS post,
    TRUE AS is_active,
    c.created_at
FROM cit_staff c
WHERE upper(split_part(TRIM(BOTH FROM coalesce(c.full_name, '')), ' ', 1)) <> 'ВАКАНСИЯ';
