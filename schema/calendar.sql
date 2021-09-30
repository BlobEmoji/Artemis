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
  prompt_idx INT NOT NULL,

  status submission_status NOT NULL,

  message_id BIGINT NOT NULL,
  queue_message_id BIGINT NOT NULL,

  gallery_message_id BIGINT
);
