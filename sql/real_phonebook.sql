  CREATE SCHEMA IF NOT EXISTS bot_test;

  CREATE OR REPLACE VIEW bot_test.phone_directory_search AS
  SELECT
      c.id AS id_phone_directory,
      split_part(trim(c.full_name), ' ', 1) AS last_name,
      split_part(trim(c.full_name), ' ', 2) AS first_name,
      NULLIF(split_part(trim(c.full_name), ' ', 3), '') AS patronymic,
      NULLIF(c.work_phone, '') AS phone,
      NULLIF(c.ext_phone, '') AS phone_ext,
      NULLIF(c.mobile_phone, '') AS mobile_phone,
      NULL::text AS email,
      NULL::integer AS department_id,
      c.department AS department_name,
      c.position AS post,
      TRUE AS is_active,
      c.created_at,
      ''::text AS person_aliases,
      ''::text AS department_aliases
  FROM public.cit_staff c;