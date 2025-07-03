READ ME

Requirements:
scrapy
playwright

Setup
python3 -m venv venv
pip install scrapy
pip install playwright
playwright install
python3 -m playwright install
pip install pandas openpyxl

--------------------------

Start/Close venv
source venv/bin/activate
deactivate


Run crawler:
scrapy crawl [class.name] -O [outputName.json or outputName.csv]
example: scrapy crawl abcam -O abcam.json

Run pandas:
python3 csv_to_excel.py