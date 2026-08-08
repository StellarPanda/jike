INSERT INTO users (email, name, plan, created_at)
VALUES
    ('ava@example.com', 'Ava Chen', 'pro', NOW() - INTERVAL '18 days'),
    ('leo@example.com', 'Leo Wang', 'free', NOW() - INTERVAL '12 days'),
    ('mia@example.com', 'Mia Zhang', 'team', NOW() - INTERVAL '6 days'),
    ('noah@example.com', 'Noah Liu', 'pro', NOW() - INTERVAL '2 days')
ON CONFLICT (email) DO NOTHING;

INSERT INTO orders (user_id, amount, status, created_at)
VALUES
    (1, 199.00, 'paid', NOW() - INTERVAL '14 days'),
    (1, 49.00, 'paid', NOW() - INTERVAL '4 days'),
    (2, 19.90, 'refunded', NOW() - INTERVAL '9 days'),
    (3, 499.00, 'paid', NOW() - INTERVAL '5 days'),
    (4, 99.00, 'pending', NOW() - INTERVAL '1 day')
ON CONFLICT DO NOTHING;
