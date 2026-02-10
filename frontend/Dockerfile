FROM python:3.13.7

WORKDIR /usr/src/app

COPY .frontend/requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY ./frontend .

CMD ["./entrypoint.sh"]