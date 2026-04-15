-- Seed 8 MECE categories for children's English learning scenes
-- Safe to run multiple times (uses ON CONFLICT to upsert)

INSERT INTO scene_categories (id, category_code, name, description, status, sort_order, created_at, updated_at)
VALUES
    ('scene_category_home',       'home',       '家庭生活', 'Home & Family — 家中各房间、家庭活动、日常起居、家具家电',       'active', 1, NOW(), NOW()),
    ('scene_category_food',       'food',       '饮食',     'Food & Drink — 食物、饮品、餐具、用餐、水果蔬菜',             'active', 2, NOW(), NOW()),
    ('scene_category_nature',     'nature',     '自然户外', 'Nature & Outdoors — 户外自然环境、天气、植物、地理景观',       'active', 3, NOW(), NOW()),
    ('scene_category_animals',    'animals',    '动物世界', 'Animals — 各种动物及栖息地、宠物',                           'active', 4, NOW(), NOW()),
    ('scene_category_transport',  'transport',  '交通出行', 'Transportation — 交通工具、交通设施、道路场景',               'active', 5, NOW(), NOW()),
    ('scene_category_community',  'community',  '社区职业', 'Community & Jobs — 社区场所、公共服务、职业体验',             'active', 6, NOW(), NOW()),
    ('scene_category_school',     'school',     '校园学习', 'School & Learning — 学校场所、学习用品、课堂活动',             'active', 7, NOW(), NOW()),
    ('scene_category_sports',     'sports',     '运动娱乐', 'Sports & Fun — 体育运动、游戏、娱乐、才艺',                   'active', 8, NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET
    category_code = EXCLUDED.category_code,
    name          = EXCLUDED.name,
    description   = EXCLUDED.description,
    status        = EXCLUDED.status,
    sort_order    = EXCLUDED.sort_order,
    updated_at    = NOW();
