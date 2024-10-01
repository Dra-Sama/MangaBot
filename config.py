env_vars = {
  # Get From my.telegram.org
  "API_HASH": "",
  # Get From my.telegram.org
  "API_ID": "",
  #Get For @BotFather
  "BOT_TOKEN": "",
  # Get For tembo.io
  "DATABASE_URL_PRIMARY": "",
  # Logs Channel Username Without @
  "CACHE_CHANNEL": "",
  # Force Subs Channel username without @
  "CHANNEL": "",
  # For Hosting at Render/Koyeb True. False For Other
  "RENDER": "",
  # {chap_num}: Chapter Number
  # {chap_name} : Manga Name
  "FNAME": "",
  # Thumb Url That U Want to Add at File
  "THUMB": ""
}
dbname = env_vars.get('DATABASE_URL_PRIMARY') or env_vars.get('DATABASE_URL') or 'sqlite:///test.db'

if dbname.startswith('postgres://'):
    dbname = dbname.replace('postgres://', 'postgresql://', 1)
    
