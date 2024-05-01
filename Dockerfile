FROM python as build
ENV PYTHONUNBUFFERED 1

WORKDIR /app/

RUN python -m venv /opt/venv
# Enable venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt /app/
COPY application.py /app/
COPY templates /app/

RUN pip install -Ur requirements.txt

EXPOSE 5000
ENV FLASK_APP=application.py
#USER nobody
CMD ["flask", "run", "--host", "0.0.0.0"]
