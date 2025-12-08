# inklusionhub-api
Inklusion Hub API

### Create and activate a virtual environment
```bash
python -m venv env
source env/bin/activate   # Linux
env\Scripts\activate      # Windows
```

### Installing Django and Django REST Framework
```bash
pip install django djangorestframework
```
### create an application
```bash
python manage.py startapp api
```
### Add your app and DRF in settingd.py file
````python
INSTALLED_APPS = [
  'rest_framework',
  'yourapp',
  ]
````

### To run server
````bash
python manage.py runserver
````
