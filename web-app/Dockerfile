
FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN pip install pipenv

RUN pipenv install --system --deploy

EXPOSE 5001

CMD ["python", "app.py"]
