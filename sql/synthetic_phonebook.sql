CREATE SCHEMA IF NOT EXISTS bot_test;

CREATE TABLE IF NOT EXISTS bot_test.departments (
    department_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    department_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS bot_test.department_aliases (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    department_id INTEGER NOT NULL REFERENCES bot_test.departments(department_id) ON DELETE CASCADE,
    alias TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bot_test.phone_directory (
    id_phone_directory INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    last_name TEXT NOT NULL,
    first_name TEXT NOT NULL,
    patronymic TEXT,
    phone TEXT,
    phone_ext TEXT,
    mobile_phone TEXT,
    email TEXT,
    department_id INTEGER REFERENCES bot_test.departments(department_id),
    post TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bot_test.person_aliases (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_phone_directory INTEGER NOT NULL REFERENCES bot_test.phone_directory(id_phone_directory) ON DELETE CASCADE,
    alias TEXT NOT NULL
);

TRUNCATE TABLE bot_test.person_aliases RESTART IDENTITY;
TRUNCATE TABLE bot_test.phone_directory RESTART IDENTITY CASCADE;
TRUNCATE TABLE bot_test.department_aliases RESTART IDENTITY;
TRUNCATE TABLE bot_test.departments RESTART IDENTITY CASCADE;

INSERT INTO bot_test.departments (department_name) VALUES
    ('ИТ инфраструктура'),
    ('Финансы и закупки'),
    ('HR и внутренние коммуникации'),
    ('Аналитика данных'),
    ('Полярная логистика и подъем пингвинов'),
    ('Поддержка клиентов'),
    ('Продажи'),
    ('Юридический отдел');

INSERT INTO bot_test.department_aliases (department_id, alias) VALUES
    (1, 'ит'),
    (1, 'айти'),
    (1, 'инфра'),
    (2, 'финансы'),
    (2, 'закупки'),
    (3, 'кадры'),
    (3, 'hr'),
    (4, 'аналитики'),
    (4, 'data'),
    (5, 'подниматели пингвинов'),
    (5, 'пингвины'),
    (5, 'полярники'),
    (6, 'саппорт'),
    (6, 'поддержка'),
    (7, 'селз'),
    (7, 'продажники'),
    (8, 'юристы');

INSERT INTO bot_test.phone_directory (
    last_name,
    first_name,
    patronymic,
    phone,
    phone_ext,
    mobile_phone,
    email,
    department_id,
    post,
    is_active
) VALUES
    ('Иванов', 'Алексей', 'Петрович', '+7 (391) 200-10-01', '101', '+7 913 000-10-01', 'a.ivanov@demo.local', 1, 'Системный администратор', TRUE),
    ('Смирнов', 'Алексей', 'Игоревич', '+7 (391) 200-10-02', '102', '+7 913 000-10-02', 'a.smirnov@demo.local', 5, 'Старший инженер экспедиции', TRUE),
    ('Петров', 'Александр', 'Сергеевич', '+7 (391) 200-10-03', '103', '+7 913 000-10-03', 'a.petrov@demo.local', 4, 'Ведущий аналитик', TRUE),
    ('Сидоров', 'Дмитрий', 'Алексеевич', '+7 (391) 200-10-04', '104', '+7 913 000-10-04', 'd.sidorov@demo.local', 1, 'DevOps инженер', TRUE),
    ('Козлова', 'Мария', 'Андреевна', '+7 (391) 200-10-05', '105', '+7 913 000-10-05', 'm.kozlova@demo.local', 2, 'Финансовый менеджер', TRUE),
    ('Орлова', 'Екатерина', 'Викторовна', '+7 (391) 200-10-06', '106', '+7 913 000-10-06', 'e.orlova@demo.local', 3, 'HR бизнес-партнер', TRUE),
    ('Федоров', 'Сергей', 'Николаевич', '+7 (391) 200-10-07', '107', '+7 913 000-10-07', 's.fedorov@demo.local', 6, 'Руководитель поддержки', TRUE),
    ('Лебедева', 'Анна', 'Павловна', '+7 (391) 200-10-08', '108', '+7 913 000-10-08', 'a.lebedeva@demo.local', 7, 'Менеджер по продажам', TRUE),
    ('Морозов', 'Илья', 'Романович', '+7 (391) 200-10-09', '109', '+7 913 000-10-09', 'i.morozov@demo.local', 5, 'Координатор полярной логистики', TRUE),
    ('Новикова', 'Ольга', 'Ильинична', '+7 (391) 200-10-10', '110', '+7 913 000-10-10', 'o.novikova@demo.local', 8, 'Юрисконсульт', TRUE),
    ('Волков', 'Роман', 'Владимирович', '+7 (391) 200-10-11', '111', '+7 913 000-10-11', 'r.volkov@demo.local', 1, 'Руководитель ИТ инфраструктуры', TRUE),
    ('Громова', 'Алина', 'Сергеевна', '+7 (391) 200-10-12', '112', '+7 913 000-10-12', 'a.gromova@demo.local', 4, 'BI аналитик', TRUE),
    ('Егоров', 'Павел', 'Олегович', '+7 (391) 200-10-13', '113', '+7 913 000-10-13', 'p.egorov@demo.local', 2, 'Специалист по закупкам', TRUE),
    ('Тарасова', 'Наталья', 'Ивановна', '+7 (391) 200-10-14', '114', '+7 913 000-10-14', 'n.tarasova@demo.local', 3, 'Рекрутер', TRUE),
    ('Белов', 'Андрей', 'Максимович', '+7 (391) 200-10-15', '115', '+7 913 000-10-15', 'a.belov@demo.local', 6, 'Инженер поддержки', TRUE),
    ('Крылов', 'Леонид', 'Артемович', '+7 (391) 200-10-16', '116', '+7 913 000-10-16', 'l.krylov@demo.local', 5, 'Начальник смены подъема пингвинов', TRUE),
    ('Афанасьева', 'Светлана', 'Юрьевна', '+7 (391) 200-10-17', '117', '+7 913 000-10-17', 's.afanaseva@demo.local', 7, 'Руководитель отдела продаж', TRUE),
    ('Захаров', 'Кирилл', 'Денисович', '+7 (391) 200-10-18', '118', '+7 913 000-10-18', 'k.zaharov@demo.local', 4, 'Data engineer', TRUE),
    ('Макаров', 'Артем', 'Станиславович', '+7 (391) 200-10-19', '119', '+7 913 000-10-19', 'a.makarov@demo.local', 1, 'Сетевой инженер', FALSE),
    ('Попова', 'Вероника', 'Дмитриевна', '+7 (391) 200-10-20', '120', '+7 913 000-10-20', 'v.popova@demo.local', 8, 'Помощник юриста', TRUE),
    ('Иванов', 'Петр', 'Андреевич', '+7 (391) 200-10-21', '121', '+7 913 000-10-21', 'p.ivanov@demo.local', 1, 'Проектный менеджер', TRUE),
    ('Иванова', 'Елена', 'Сергеевна', '+7 (391) 200-10-22', '122', '+7 913 000-10-22', 'e.ivanova@demo.local', 7, 'Менеджер по работе с клиентами', TRUE),
    ('Алексеев', 'Алексей', 'Михайлович', '+7 (391) 200-10-23', '123', '+7 913 000-10-23', 'a.alekseev@demo.local', 5, 'Специалист по подъему пингвинов', TRUE),
    ('Смирнова', 'Марина', 'Олеговна', '+7 (391) 200-10-24', '124', '+7 913 000-10-24', 'm.smirnova@demo.local', 6, 'Менеджер поддержки', TRUE),
    ('Гусев', 'Алексей', 'Викторович', '+7 (391) 200-10-25', '125', '+7 913 000-10-25', 'a.gusev@demo.local', 2, 'Менеджер по закупкам', TRUE),
    ('Васильев', 'Денис', 'Андреевич', '+7 (391) 200-10-26', '126', '+7 913 000-10-26', 'd.vasiliev@demo.local', 1, 'Системный администратор', TRUE),
    ('Васильева', 'Дарья', 'Игоревна', '+7 (391) 200-10-27', '127', '+7 913 000-10-27', 'd.vasileva@demo.local', 3, 'HR менеджер', TRUE),
    ('Никитин', 'Олег', 'Павлович', '+7 (391) 200-10-28', '128', '+7 913 000-10-28', 'o.nikitin@demo.local', 4, 'Руководитель аналитики', TRUE),
    ('Никитина', 'Ольга', 'Павловна', '+7 (391) 200-10-29', '129', '+7 913 000-10-29', 'o.nikitina@demo.local', 4, 'Аналитик данных', TRUE),
    ('Чернов', 'Арсений', 'Олегович', '+7 (391) 200-10-30', '130', '+7 913 000-10-30', 'a.chernov@demo.local', 5, 'Подниматель пингвинов', TRUE),
    ('Чернова', 'Арина', 'Игоревна', '+7 (391) 200-10-31', '131', '+7 913 000-10-31', 'a.chernova@demo.local', 5, 'Менеджер экспедиции', TRUE),
    ('Соколова', 'Юлия', 'Алексеевна', '+7 (391) 200-10-32', '132', '+7 913 000-10-32', 'y.sokolova@demo.local', 8, 'Юрист по договорам', TRUE),
    ('Соколов', 'Юрий', 'Семенович', '+7 (391) 200-10-33', '133', '+7 913 000-10-33', 'y.sokolov@demo.local', 7, 'Аккаунт-менеджер', TRUE),
    ('Павлов', 'Алексей', 'Григорьевич', '+7 (391) 200-10-34', '134', '+7 913 000-10-34', 'a.pavlov@demo.local', 6, 'Инженер поддержки', TRUE),
    ('Павлова', 'Алена', 'Игоревна', '+7 (391) 200-10-35', '135', '+7 913 000-10-35', 'a.pavlova@demo.local', 2, 'Финансовый контролер', TRUE),
    ('Романов', 'Лев', 'Максимович', '+7 (391) 200-10-36', '136', '+7 913 000-10-36', 'l.romanov@demo.local', 1, 'Руководитель платформы', TRUE);

INSERT INTO bot_test.person_aliases (id_phone_directory, alias) VALUES
    (1, 'леша'),
    (1, 'лёха'),
    (2, 'леша'),
    (2, 'лёха'),
    (3, 'саша'),
    (4, 'дима'),
    (4, 'дмитрий devops'),
    (7, 'серега'),
    (8, 'аня'),
    (9, 'иля'),
    (11, 'рома'),
    (13, 'паша'),
    (16, 'леня'),
    (19, 'тема'),
    (19, 'артем'),
    (21, 'петя'),
    (22, 'лена'),
    (23, 'леша'),
    (23, 'лёха'),
    (24, 'марина саппорт'),
    (25, 'леша'),
    (25, 'лёха'),
    (26, 'ден'),
    (27, 'даша'),
    (28, 'олег аналитика'),
    (29, 'оля'),
    (30, 'арс'),
    (31, 'арина'),
    (32, 'юля'),
    (33, 'юра'),
    (34, 'леша'),
    (35, 'алена'),
    (36, 'лев');

INSERT INTO bot_test.phone_directory (
    last_name,
    first_name,
    patronymic,
    phone,
    phone_ext,
    mobile_phone,
    email,
    department_id,
    post,
    is_active
)
SELECT
    'Тестов' || gs::text,
    CASE gs % 10
        WHEN 0 THEN 'Алексей'
        WHEN 1 THEN 'Мария'
        WHEN 2 THEN 'Дмитрий'
        WHEN 3 THEN 'Ольга'
        WHEN 4 THEN 'Роман'
        WHEN 5 THEN 'Анна'
        WHEN 6 THEN 'Павел'
        WHEN 7 THEN 'Дарья'
        WHEN 8 THEN 'Илья'
        ELSE 'Елена'
    END,
    CASE gs % 6
        WHEN 0 THEN 'Андреевич'
        WHEN 1 THEN 'Игоревна'
        WHEN 2 THEN 'Павлович'
        WHEN 3 THEN 'Сергеевна'
        WHEN 4 THEN 'Олегович'
        ELSE 'Дмитриевна'
    END,
    '+7 (391) 210-' || LPAD((gs + 40)::text, 2, '0') || '-01',
    (200 + gs)::text,
    '+7 913 100-' || LPAD((gs + 40)::text, 2, '0') || '-01',
    'bulk' || gs::text || '@demo.local',
    ((gs - 1) % 8) + 1,
    CASE gs % 9
        WHEN 0 THEN 'Менеджер проекта'
        WHEN 1 THEN 'Системный администратор'
        WHEN 2 THEN 'Аналитик данных'
        WHEN 3 THEN 'Инженер поддержки'
        WHEN 4 THEN 'Специалист по закупкам'
        WHEN 5 THEN 'HR менеджер'
        WHEN 6 THEN 'Юрист'
        WHEN 7 THEN 'Подниматель пингвинов'
        ELSE 'Руководитель группы'
    END,
    TRUE
FROM generate_series(1, 72) AS gs;

CREATE OR REPLACE VIEW bot_test.phone_directory_search AS
SELECT
    p.id_phone_directory,
    p.last_name,
    p.first_name,
    p.patronymic,
    p.phone,
    p.phone_ext,
    p.mobile_phone,
    p.email,
    p.department_id,
    d.department_name,
    p.post,
    p.is_active,
    p.created_at,
    COALESCE(STRING_AGG(DISTINCT pa.alias, ', '), '') AS person_aliases,
    COALESCE(STRING_AGG(DISTINCT da.alias, ', '), '') AS department_aliases
FROM bot_test.phone_directory p
LEFT JOIN bot_test.departments d ON d.department_id = p.department_id
LEFT JOIN bot_test.person_aliases pa ON pa.id_phone_directory = p.id_phone_directory
LEFT JOIN bot_test.department_aliases da ON da.department_id = d.department_id
GROUP BY
    p.id_phone_directory,
    p.last_name,
    p.first_name,
    p.patronymic,
    p.phone,
    p.phone_ext,
    p.mobile_phone,
    p.email,
    p.department_id,
    d.department_name,
    p.post,
    p.is_active,
    p.created_at;
