DROP TABLE IF EXISTS submissions;

CREATE TABLE submissions (
    user_id BIGINT,
    day_num INT,
    approved BOOLEAN DEFAULT false,
    user_post_id BIGINT,
    in_queue BOOLEAN DEFAULT true,
    queue_post_id BIGINT,
    gallery_post_id BIGINT,
    image_link TEXT,
    approver_id BIGINT,
    identifier_id BIGINT
);
