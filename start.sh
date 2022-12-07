cd /app
rm -rf mangabot
git clone https://github.com/Dra-Sama/mangabot
cd mangabot
pip install --quiet -r requirements.txt
python main.py
echo "Started..."
