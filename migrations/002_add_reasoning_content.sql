-- Add reasoning_content column to messages table for deepseek-reasoner support
ALTER TABLE public.messages ADD COLUMN reasoning_content TEXT DEFAULT NULL;
