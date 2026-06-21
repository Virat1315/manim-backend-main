web: uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1
worker: celery -A gen_topic.celery_app worker --loglevel=info
web: uvicorn main:app --host 0.0.0.0 --port $PORT
worker: celery -A gen_topic.celery_app worker --loglevel=info --concurrency=1
