#!/bin/bash
export DJANGO_SETTINGS_MODULE=setup.settings
export PYTHONUNBUFFERED=1
# source /root/.local/share/virtualenvs/brooks-insurance-*/bin/activate

echo "<<<<<<<< Collect Staticfiles>>>>>>>>>"
python3 manage.py collectstatic --noinput


# sleep 5
# echo "<<<<<<<< Database Setup and Migrations Starts >>>>>>>>>"
# # Run database migrations
python3 manage.py makemigrations &
python3 manage.py migrate  &

# sleep 5
# echo "<<<<<<< Initializing the Database >>>>>>>>>>"
# echo " "
# python manage.py loaddata initialization.yaml
# echo " "
echo "<<<<<<<<<<<<<<<<<<<< START Celery >>>>>>>>>>>>>>>>>>>>>>>>"

# # start Celery worker
celery -A setup worker --loglevel=info &

# # start celery beat
celery -A setup beat --loglevel=info &

sleep 5

# Start Gunicorn WSGI
#gunicorn --bind 0.0.0.0:8000 setup.wsgi --workers=2 &

# Start Daphne ASGI for WebSockets
#daphne -b 0.0.0.0 -p 8001 setup.asgi:application 

python3 manage.py runserver 0.0.0.0:8000