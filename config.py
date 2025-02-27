env_vars = {
  # Get From my.telegram.org
  "API_HASH": "e9bfc473049cbaeff901ca6892d559c7",
  # Get From my.telegram.org
  "API_ID": "20373005",
  #Get For @BotFather
  "BOT_TOKEN": "7650228700:AAHJAzEuwmXeu02v8aCCgeeag9SoyrX1NEg",
  # Get For tembo.io
  "DATABASE_URL_PRIMARY": "",
  # Logs Channel Username Without @
  "CACHE_CHANNEL": "https://t.me/+VxPazQIIcGJmMWY1",
  # Force Subs Channel username without @
  "CHANNEL": "",
  # {chap_num}: Chapter Number
  # {chap_name} : Manga Name
  # Ex : Chapter {chap_num} {chap_name} @Manhwa_Arena
  "FNAME": "",
  # Put Thumb Link 
  "THUMB": ""
}

dbname = env_vars.get('DATABASE_URL_PRIMARY') or env_vars.get('DATABASE_URL') or 'sqlite:///test.db'

if dbname.startswith('postgres://'):
    dbname = dbname.replace('postgres://', 'postgresql://', 1)
    
