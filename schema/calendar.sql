CREATE TYPE submission_status AS ENUM (
    'pending',
    'approved',
    'denied',
    'dismissed'
);


CREATE TABLE IF NOT EXISTS submissions (
  id SERIAL PRIMARY KEY,

  user_id BIGINT NOT NULL,

  image_url TEXT NOT NULL,
  prompt_id INT NOT NULL,

  status submission_status NOT NULL,

  message_id BIGINT NOT NULL,
  queue_message_id BIGINT NOT NULL
);


CREATE TABLE IF NOT EXISTS gallery (
    submission_id INT NOT NULL REFERENCES submissions (id) ON DELETE CASCADE,
    message_id BIGINT NOT NULL
)
