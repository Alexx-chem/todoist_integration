FROM python:3.9

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src src
COPY main.py .
COPY config.py .

CMD [ "python", "-u", "main.py" ]
