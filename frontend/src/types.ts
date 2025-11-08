export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface Item {
  id: string;
  user_id: string;
  type: string;
  title?: string;
  url?: string;
  raw_content?: string;
  tags: string[];
  s3_key?: string;
  created_at: string;
}

export interface CreateUserRequest {
  email: string;
}