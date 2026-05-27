-- Add show_weather_forecast field to event table
-- Allows hosts to toggle weather forecast visibility for their events

ALTER TABLE event
ADD COLUMN IF NOT EXISTS show_weather_forecast BOOLEAN DEFAULT false;
