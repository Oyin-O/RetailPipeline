CREATE OR REPLACE TABLE dim_users AS
SELECT
    user_id,
    email,
    split_part(email, '@', 2) AS email_domain,
    country,
    signup_date,
    is_active,
    updated_at AS source_updated_at
FROM silver_users;
